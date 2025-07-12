#!/usr/bin/env python3
"""
Regression test for IAM role policy drift detection.

This test ensures that the drift detector does NOT report false drift when the policy document
in the Terraform state is a JSON string and the live AWS resource returns a dict. This is a common
format difference and should not be considered drift. This test guards against regressions in the
comparator logic for IAM role policies.
"""

import json
import sys
from pathlib import Path

# Add src to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.drift_detector.resource_comparators import _compare_iam_role_policy_attributes


def test_policy_comparison():
    """Test that policy document format differences are handled correctly."""
    
    # State attributes (JSON string format)
    state_attrs = {
        "role": "github-actions-role",
        "name": "github-actions-policy",
        "policy": '{"Version":"2012-10-17","Statement":[{"Action":["lambda:CreateFunction"],"Effect":"Allow","Resource":"*"}]}'
    }
    
    # Live attributes (dict format)
    live_attrs = {
        "role_name": "github-actions-role",
        "policy_name": "github-actions-policy",
        "policy": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": ["lambda:CreateFunction"],
                    "Effect": "Allow",
                    "Resource": "*"
                }
            ]
        }
    }
    
    # Compare attributes
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
        print(f"  - {detail['attribute']}: {detail['state_value']} -> {detail['live_value']}")
    
    # Should have no drift details if format is handled correctly
    assert len(drift_details) == 0, f"Expected no drift details, but found {len(drift_details)}"
    print("✅ SUCCESS: No drift detected - format differences handled correctly!")


if __name__ == "__main__":
    test_policy_comparison()
    print("Test completed successfully!") 