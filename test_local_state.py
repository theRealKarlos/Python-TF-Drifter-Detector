#!/usr/bin/env python3
"""
Test script to run the drift detector with a local state file.
"""

import json
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.drift_detector import detect_drift
from src.utils import setup_logging


def main():
    """Test the drift detector with local state file."""
    
    # Set up logging
    logger = setup_logging("DEBUG")
    logger.info("Starting local drift detection test")
    
    # Load the state file with real AWS resources
    state_file_path = "tests/real_state.json"
    
    try:
        with open(state_file_path, 'r') as f:
            state_data = json.load(f)
        
        logger.info(f"Loaded state file: {state_file_path}")
        
        # Prepare configuration
        config = {
            "s3_state_path": "local://tests/real_state.json",  # Use local file path format
            "aws_region": "eu-west-2",
            "log_level": "DEBUG",
            "max_retries": 3,
            "timeout_seconds": 30,
        }
        
        # Run drift detection
        logger.info("Running drift detection...")
        drift_report = detect_drift(config)
        
        # Print results
        print("\n" + "="*60)
        print("DRIFT DETECTION TEST RESULTS")
        print("="*60)
        
        drift_detected = drift_report.get("drift_detected", False)
        drifts = drift_report.get("drifts", [])
        summary = drift_report.get("summary", {})
        
        print(f"Drift Detected: {'YES' if drift_detected else 'NO'}")
        print(f"Total Drifts: {len(drifts)}")
        
        if summary:
            print(f"\nSummary:")
            for key, value in summary.items():
                if key != "matching_resources":
                    print(f"  {key}: {value}")
        
        # Print matching resources
        matching_resources = summary.get("matching_resources", [])
        if matching_resources:
            print(f"\n=== Matching Resources ({len(matching_resources)}) ===")
            for res in sorted(matching_resources, key=lambda x: (x["resource_type"], x["resource_name"])):
                aws_live_name = res.get("aws_live_name", "")
                if aws_live_name:
                    print(f"✅ {res['resource_type']} {res['resource_name']} - {aws_live_name}")
                else:
                    print(f"✅ {res['resource_type']} {res['resource_name']}")
        else:
            print("\n❌ No matching resources found!")
        
        # Print drifts
        if drifts:
            print(f"\n=== Drifts ({len(drifts)}) ===")
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
        
        print("\n" + "="*60)
        
        # Return appropriate exit code
        if drift_detected:
            logger.warning("Drift detected! Exiting with code 1")
            sys.exit(1)
        else:
            logger.info("No drift detected. Exiting with code 0")
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"Error running drift detection: {str(e)}")
        print(f"ERROR: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main() 