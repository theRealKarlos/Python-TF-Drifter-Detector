"""
EC2 Instance Resource Comparators Module.

This module contains functions for comparing EC2 instance-related AWS resources.
"""

from typing import Any, Dict, List

from ..types import DriftDetail


def compare_ec2_instance_attributes(state_attrs: Dict[str, Any], live_attrs: Dict[str, Any]) -> List[DriftDetail]:
    """
    Compare EC2 instance attributes between Terraform state and live AWS.
    Returns a list of drift details for any mismatched attributes.
    """
    drift_details: List[DriftDetail] = []
    # Compare instance type for EC2 instances
    state_instance_type = state_attrs.get("instance_type")
    live_instance_type = live_attrs.get("InstanceType")
    if state_instance_type != live_instance_type:
        drift_details.append(
            {
                "attribute": "instance_type",
                "state_value": str(state_instance_type),
                "live_value": str(live_instance_type),
            }
        )
    return drift_details
