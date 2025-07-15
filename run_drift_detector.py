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
    summary = drift_report.get("summary", {})
    timestamp = drift_report.get("timestamp", "Unknown")

    # 1. Print total count of all resources in the state file
    total_resources = summary.get("total_resources", "Unknown")
    resource_block_count = summary.get("resource_block_count", "Unknown")
    total_instance_count = summary.get("total_instance_count", "Unknown")
    print(f"\nResource block count (top-level resources): {resource_block_count}")
    print(f"Total resource instances (including meta): {total_instance_count}")
    print(f"Total unique resource keys (excluding meta): {total_resources}")

    # 2. Print meta resources
    meta_resources = summary.get("meta_resources", [])
    print(f"\n=== Meta Resources ({len(meta_resources)}) ===")
    if meta_resources:
        for res in meta_resources:
            print(f"⚙️  {res['resource_type']} {res['resource_name']}: {res['value']}")
        print("\nNote: Meta resources are present in the state file but are not subject to drift detection (e.g., aws_region, aws_caller_identity).")
    else:
        print("No meta resources detected.")

    # 3. Print matched resources
    matching_resources = summary.get("matching_resources", [])
    print(f"\n=== Matching Resources ({len(matching_resources)}) ===")
    if matching_resources:
        for res in sorted(matching_resources, key=lambda x: (x["resource_type"], x.get("display_name") or x["resource_name"])):
            display = res.get("display_name") or res["resource_name"]
            print(f"✅ {res['resource_type']} {display}")
    else:
        print("No matching resources detected.")

    # 4. Print drifted resources
    drifts = drift_report.get("drifts", [])
    print(f"\n=== Drifted Resources ({len(drifts)}) ===")
    if drifts:
        for i, drift in enumerate(drifts, 1):
            print(f"{i}. Resource: {drift.get('resource_key', 'Unknown')}")
            print(f"   Type: {drift.get('drift_type', 'Unknown')}")
            print(f"   Description: {drift.get('description', 'No description')}")
            differences = drift.get('differences', [])
            if differences:
                print(f"   Differences:")
                for diff in differences:
                    print(f"     - {diff.get('attribute', 'Unknown')}: State='{diff.get('state_value', 'N/A')}' Live='{diff.get('live_value', 'N/A')}'")
    else:
        print("No drifted resources detected.")

    # 5. Print unaccounted resources (resources in state file not in matched, drift, or meta lists)
    unaccounted_resources = summary.get("unmatched_undetected_resources", [])
    print(f"\n=== Unaccounted Resources ({len(unaccounted_resources)}) ===")
    if unaccounted_resources:
        for res in unaccounted_resources:
            print(f"❓ {res['resource_type']} {res['resource_name']}: {res['key']}")
        print("\nNote: Unaccounted resources are present in the state file but not classified as matched, drifted, or meta. This may indicate a bug or a resource type not yet supported by the drift detector.")
    else:
        print("No unaccounted resources detected.")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    main() 