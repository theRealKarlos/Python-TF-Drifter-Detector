"""
EC2 Resource Comparators Module.

This module contains functions for comparing EC2-related AWS resources.
"""

from typing import Any, Dict, List

from ..types import DriftDetail


def compare_ec2_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any]
) -> List[DriftDetail]:
    """
    Compare EC2 resource attributes between Terraform state and live AWS.

    Args:
        state_attrs: Attributes from Terraform state resource
        live_attrs: Attributes from live AWS resource

    Returns:
        List of drift details for any mismatched attributes
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

    # Compare VPC ID for VPCs
    state_vpc_id = state_attrs.get("id")
    live_vpc_id = live_attrs.get("VpcId")
    if state_vpc_id != live_vpc_id:
        drift_details.append(
            {
                "attribute": "vpc_id",
                "state_value": str(state_vpc_id),
                "live_value": str(live_vpc_id),
            }
        )

    return drift_details
