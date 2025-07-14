#!/usr/bin/env python3
"""
Command-line interface for running the Terraform Drift Detector locally.

This script allows you to run the drift detector with a real S3 path from your local machine.
It requires AWS credentials to be configured (via AWS CLI, environment variables, or IAM roles).

Usage:
    python run_drift_detector.py --s3-path s3://your-bucket/path/to/terraform.tfstate
    python run_drift_detector.py --s3-path s3://your-bucket/path/to/terraform.tfstate --region us-east-1
    python run_drift_detector.py --s3-path s3://your-bucket/path/to/terraform.tfstate --log-level DEBUG
"""

import argparse
import json
import os
import sys
from typing import Dict, Any

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.drift_detector import detect_drift
from src.utils import setup_logging


def main() -> None:
    """Main entry point for the command-line drift detector."""
    parser = argparse.ArgumentParser(
        description="Run Terraform Drift Detector with a real S3 path",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_drift_detector.py --s3-path s3://my-terraform-bucket/terraform.tfstate
  python run_drift_detector.py --s3-path s3://my-bucket/state.tfstate --region us-west-2 --log-level DEBUG
        """
    )
    
    parser.add_argument(
        "--s3-path",
        required=True,
        help="S3 path to the Terraform state file (e.g., s3://bucket/path/to/terraform.tfstate)"
    )
    
    parser.add_argument(
        "--region",
        default="eu-west-2",
        help="AWS region for API calls (default: eu-west-2)"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum number of retries for AWS API calls (default: 3)"
    )
    
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=30,
        help="Timeout for AWS API calls in seconds (default: 30)"
    )
    
    parser.add_argument(
        "--output-format",
        choices=["json", "pretty"],
        default="pretty",
        help="Output format for the drift report (default: pretty)"
    )
    
    args = parser.parse_args()
    
    # Validate S3 path format
    if not args.s3_path.startswith("s3://"):
        print("ERROR: S3 path must start with 's3://'")
        sys.exit(1)
    
    # Set up logging
    logger = setup_logging(args.log_level)
    logger.info("Starting Terraform drift detection from command line")
    
    # Prepare configuration
    config: Dict[str, Any] = {
        "s3_state_path": args.s3_path,
        "aws_region": args.region,
        "log_level": args.log_level,
        "max_retries": args.max_retries,
        "timeout_seconds": args.timeout_seconds,
    }
    
    try:
        # Run drift detection
        logger.info(f"Running drift detection for S3 path: {args.s3_path}")
        logger.info(f"Using AWS region: {args.region}")
        
        drift_report = detect_drift(config)
        
        # Output results
        if args.output_format == "json":
            print(json.dumps(drift_report, indent=2))
        else:
            print_drift_report(drift_report)
            
        # Exit with appropriate code
        if drift_report.get("drift_detected", False):
            logger.warning("Drift detected! Exiting with code 1")
            sys.exit(1)
        else:
            logger.info("No drift detected. Exiting with code 0")
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"Error running drift detection: {str(e)}")
        print(f"ERROR: {str(e)}", file=sys.stderr)
        sys.exit(1)


def print_drift_report(drift_report: Dict[str, Any]) -> None:
    """Print a human-readable drift report, including matching resources."""
    print("\n" + "="*60)
    print("TERRAFORM DRIFT DETECTION REPORT")
    print("="*60)
    
    drift_detected = drift_report.get("drift_detected", False)
    drifts = drift_report.get("drifts", [])
    summary = drift_report.get("summary", {})
    timestamp = drift_report.get("timestamp", "Unknown")
    # Print matching resources in alphabetical order
    matching_resources = summary.get("matching_resources", [])
    
    print(f"Timestamp: {timestamp}")
    print(f"Drift Detected: {'YES' if drift_detected else 'NO'}")
    print(f"Total Drifts: {len(drifts)}")
    
    if summary:
        print(f"\nSummary:")
        for key, value in summary.items():
            if key != "matching_resources":
                print(f"  {key}: {value}")
    
    if drifts:
        print(f"\nDetailed Drift Information:")
        print("-" * 40)
        
        for i, drift in enumerate(drifts, 1):
            print(f"\n{i}. Resource: {drift.get('resource_key', 'Unknown')}")
            print(f"   Type: {drift.get('drift_type', 'Unknown')}")
            print(f"   Description: {drift.get('description', 'No description')}")
            
            differences = drift.get('differences', [])
            if differences:
                print(f"   Differences:")
                for diff in differences:
                    print(f"     - {diff.get('attribute', 'Unknown')}: "
                          f"State='{diff.get('state_value', 'N/A')}' "
                          f"Live='{diff.get('live_value', 'N/A')}'")
    else:
        print("\n✅ No drift detected - your infrastructure is in sync!")
    
    # Print matching resources with a green tick
    if matching_resources:
        print("\n=== Matching Resources ===")
        # Sort by resource_type then resource_name
        for res in sorted(matching_resources, key=lambda x: (x["resource_type"], x["resource_name"])):
            # If aws_live_name is present, include it in the output
            aws_live_name = res.get("aws_live_name")
            if aws_live_name:
                print(f"\u2705 {res['resource_type']} {res['resource_name']} - {aws_live_name}")
            else:
                print(f"\u2705 {res['resource_type']} {res['resource_name']}")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    main() 