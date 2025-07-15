"""
EC2 Resource Comparators Module (Router).

This module routes EC2-related resource types to their specific comparators.
"""

from typing import Any, Dict, List

from ..types import DriftDetail
from .ec2_instances_comparator import compare_ec2_instance_attributes
from .vpc_comparator import compare_vpc_attributes


def compare_ec2_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any], resource_type: str = ""
) -> List[DriftDetail]:
    """
    Route EC2-related resource types to their specific comparators.
    """
    if resource_type and resource_type.startswith("aws_vpc"):
        return compare_vpc_attributes(state_attrs, live_attrs)
    else:
        return compare_ec2_instance_attributes(state_attrs, live_attrs)
