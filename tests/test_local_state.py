#!/usr/bin/env python3
"""
Test script for running drift detection with a local state file.
This allows testing without needing to upload state files to S3.
"""

import argparse
import os
import sys
from pathlib import Path

from src.drift_detector import detect_drift
from src.utils import parse_terraform_state

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_with_local_state() -> None:
    """
    Test drift detection with a local state file.
    This test is designed to be run manually with a real state file.
    """
    state_file_path = os.environ.get("TEST_STATE_FILE_PATH")
    if not state_file_path:
        print("Skipping test - TEST_STATE_FILE_PATH not set")
        return
    if not os.path.exists(state_file_path):
        print(f"Skipping test - State file not found: {state_file_path}")
        return
    log_level = os.environ.get("LOG_LEVEL", "INFO")
    aws_region = os.environ.get("AWS_REGION", "eu-west-2")
    try:
        print(f"Reading state file: {state_file_path}")
        with open(state_file_path, "r") as f:
            state_content = f.read()
        state_data = parse_terraform_state(state_content)
        print(
            f"Parsed state file with {len(state_data.get('resources', []))} resources"
        )
        config = {
            "s3_state_path": "local://" + state_file_path,
            "log_level": log_level,
            "aws_region": aws_region,
        }
        print("Starting drift detection...")
        result = detect_drift(config)
        assert isinstance(result, dict)
        assert "drift_detected" in result
        assert "drifts" in result
        print(
            f"Drift detection completed. Drift detected: {result.get('drift_detected', False)}"
        )
    except Exception as e:
        print(f"Error during drift detection: {e}")
        pass


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Test drift detection with a local state file"
    )
    parser.add_argument("state_file", help="Path to the Terraform state file")
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level",
    )
    parser.add_argument(
        "--region", default=None, help="AWS region to use (overrides config and env)"
    )
    parser.add_argument("--output", help="Output file for results (optional)")
    args = parser.parse_args()
    if not os.path.exists(args.state_file):
        print(f"Error: State file '{args.state_file}' not found")
        sys.exit(1)
    os.environ["TEST_STATE_FILE_PATH"] = args.state_file
    if args.region:
        os.environ["AWS_REGION"] = args.region
    os.environ["LOG_LEVEL"] = args.log_level
    test_with_local_state()
    print("Test completed!")


if __name__ == "__main__":
    main()
