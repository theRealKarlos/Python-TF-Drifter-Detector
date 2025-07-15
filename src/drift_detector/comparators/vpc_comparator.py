"""
VPC Resource Comparators Module.

This module contains functions for comparing VPC-related AWS resources.
"""

from typing import Any, Dict, List

from ..types import DriftDetail


def compare_vpc_attributes(state_attrs: Dict[str, Any], live_attrs: Dict[str, Any]) -> List[DriftDetail]:
    """
    Compare VPC attributes between Terraform state and live AWS.
    Returns a list of drift details for any mismatched attributes.
    """
    drift_details: List[DriftDetail] = []
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
