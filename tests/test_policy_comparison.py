#!/usr/bin/env python3
"""
Regression test for IAM role policy drift detection.

This test ensures that the drift detector does NOT report false drift when the policy document
in the Terraform state is a JSON string and the live AWS resource returns a dict. This is a common
format difference and should not be considered drift. This test guards against regressions in the
comparator logic for IAM role policies.
"""

import sys
from pathlib import Path

from src.drift_detector.comparators.iam_comparators import (
    _compare_iam_role_policy_attributes,
)

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_policy_comparison() -> None:
    """Test that policy document format differences are handled correctly."""
    state_attrs = {
        "role": "github-actions-role",
        "name": "github-actions-policy",
        "policy": (
            '{"Version":"2012-10-17","Statement":[{"Action":["lambda:CreateFunction"],'
            '"Effect":"Allow","Resource":"*"}]}'
        ),
    }
    live_attrs = {
        "role_name": "github-actions-role",
        "policy_name": "github-actions-policy",
        "policy": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": ["lambda:CreateFunction"],
                    "Effect": "Allow",
                    "Resource": "*",
                }
            ],
        },
    }
    drift_details = _compare_iam_role_policy_attributes(state_attrs, live_attrs)
    print("Policy comparison test:")
    print(f"State role: {state_attrs['role']}")
    print(f"Live role: {live_attrs['role_name']}")
    print(f"State policy name: {state_attrs['name']}")
    print(f"Live policy name: {live_attrs['policy_name']}")
    print(f"State policy type: {type(state_attrs['policy'])}")
    print(f"Live policy type: {type(live_attrs['policy'])}")
    print(f"Drift details found: {len(drift_details)}")
    for detail in drift_details:
        print(
            f"  - {detail['attribute']}: {detail['state_value']} -> {detail['live_value']}"
        )
    assert (
        len(drift_details) == 0
    ), f"Expected no drift details, but found {len(drift_details)}"
    print("✅ SUCCESS: No drift detected - format differences handled correctly!")


if __name__ == "__main__":
    test_policy_comparison()
    print("Test completed successfully!")
