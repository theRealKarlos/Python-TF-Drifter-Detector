#!/usr/bin/env python3
"""
Developer debug tool for inspecting raw drift output.

This script runs drift detection on a real or test state file and prints the raw drift details.
It is useful for debugging comparator logic, understanding what the drift detector is reporting,
and for regression testing during development.
"""

import json
import sys
from pathlib import Path

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.drift_detector import detect_drift


def debug_drift_details():
    """Debug the actual drift details being returned."""
    
    # Create a simple config for testing
    config = {
        "s3_state_path": "local://D:/Exercise Files/TypeScript-PulseQueue/infra/bootstrap/terraform.tfstate",
        "log_level": "DEBUG",
        "aws_region": "eu-west-2"
    }
    
    # Run drift detection
    result = detect_drift(config)
    
    print("=== DRIFT DETECTION RESULT ===")
    print(f"Drift detected: {result.get('drift_detected', False)}")
    print(f"Number of drifts: {len(result.get('drifts', []))}")
    
    for i, drift in enumerate(result.get('drifts', []), 1):
        print(f"\nDrift {i}:")
        print(f"  Resource key: {drift.get('resource_key')}")
        print(f"  Drift type: {drift.get('drift_type')}")
        print(f"  Description: {drift.get('description')}")
        
        if 'differences' in drift:
            print("  Differences:")
            for diff in drift['differences']:
                print(f"    {diff.get('attribute')}: {diff.get('state_value')} -> {diff.get('live_value')}")
        else:
            print("  No differences field")
    
    # Also print the raw result for debugging
    print("\n=== RAW RESULT ===")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    debug_drift_details() 