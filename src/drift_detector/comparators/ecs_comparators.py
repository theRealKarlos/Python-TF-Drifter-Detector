"""
ECS Resource Comparators Module.

This module contains functions for comparing ECS-related AWS resources.
"""

from typing import Any, Dict, List

from ..types import DriftDetail


def compare_ecs_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any], resource_type: str
) -> List[DriftDetail]:
    """
    Compare ECS resource attributes between Terraform state and live AWS.

    Args:
        state_attrs: Attributes from Terraform state resource
        live_attrs: Attributes from live AWS resource
        resource_type: Type of ECS resource

    Returns:
        List of drift details for any mismatched attributes
    """
    if resource_type.startswith("aws_ecs_cluster"):
        return _compare_ecs_cluster_attributes(state_attrs, live_attrs)
    elif resource_type.startswith("aws_ecs_service"):
        return _compare_ecs_service_attributes(state_attrs, live_attrs)
    else:
        return []


def _compare_ecs_cluster_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any]
) -> List[DriftDetail]:
    """
    Compare ECS cluster attributes between Terraform state and live AWS.
    Returns a list of drift details for any mismatched attributes.
    """
    drift_details = []
    state_cluster_name = state_attrs.get("name")
    live_cluster_name = live_attrs.get("clusterName")
    if state_cluster_name != live_cluster_name:
        drift_details.append(
            {
                "attribute": "cluster_name",
                "state_value": str(state_cluster_name),
                "live_value": str(live_cluster_name),
            }
        )
    return drift_details


def _compare_ecs_service_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any]
) -> List[DriftDetail]:
    """
    Compare ECS service attributes between Terraform state and live AWS.
    Returns a list of drift details for any mismatched attributes.
    """
    drift_details = []
    state_service_name = state_attrs.get("name")
    live_service_name = live_attrs.get("serviceName")
    if state_service_name != live_service_name:
        drift_details.append(
            {
                "attribute": "service_name",
                "state_value": str(state_service_name),
                "live_value": str(live_service_name),
            }
        )
    return drift_details
