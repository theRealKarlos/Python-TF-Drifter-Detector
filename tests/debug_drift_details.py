#!/usr/bin/env python3
"""
Developer debug tool for inspecting raw drift output.

This script runs drift detection on a real or test state file and prints the raw drift details.
It is useful for debugging comparator logic, understanding what the drift detector is reporting,
and for regression testing during development.
"""

import sys
from pathlib import Path

from src.drift_detector import detect_drift

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def debug_drift_details() -> None:
    """Debug the actual drift details being returned."""
    config = {
        "s3_state_path": ("local://D:/Exercise Files/TypeScript-PulseQueue/infra/bootstrap/terraform.tfstate"),
        "log_level": "DEBUG",
        "aws_region": "eu-west-2",
    }
    result = detect_drift(config)
    print("=== DRIFT DETECTION RESULT ===")
    print(f"Drift detected: {result.get('drift_detected', False)}")
    print(f"Total drifts: {len(result.get('drifts', []))}")
    print()
    if result.get("drifts"):
        print("=== DRIFT DETAILS ===")
        for i, drift in enumerate(result["drifts"], 1):
            print(f"Drift {i}:")
            print(f"  Resource: {drift.get('resource_key', 'Unknown')}")
            print(f"  Type: {drift.get('drift_type', 'Unknown')}")
            print(f"  Description: {drift.get('description', 'No description')}")
            if "differences" in drift:
                print("  Differences:")
                for diff in drift["differences"]:
                    print(
                        f"    {diff.get('attribute', 'Unknown')}: "
                        f"{diff.get('state_value', 'Unknown')} -> "
                        f"{diff.get('live_value', 'Unknown')}"
                    )
            print()
    else:
        print("No drifts detected! ✅")


if __name__ == "__main__":
    debug_drift_details()
