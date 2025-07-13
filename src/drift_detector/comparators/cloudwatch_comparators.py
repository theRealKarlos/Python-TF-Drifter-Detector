"""
CloudWatch Resource Comparators Module.

This module contains functions for comparing CloudWatch-related AWS resources.
"""

from typing import Any, Dict, List


def compare_cloudwatch_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any], resource_type: str
) -> List[Dict[str, Any]]:
    """
    Compare CloudWatch resource attributes between Terraform state and live AWS.

    Args:
        state_attrs: Attributes from Terraform state resource
        live_attrs: Attributes from live AWS resource
        resource_type: Type of CloudWatch resource

    Returns:
        List of drift details for any mismatched attributes
    """
    if resource_type.startswith("aws_cloudwatch_dashboard"):
        return _compare_cloudwatch_dashboard_attributes(state_attrs, live_attrs)
    elif resource_type.startswith("aws_cloudwatch_metric_alarm"):
        return _compare_cloudwatch_alarm_attributes(state_attrs, live_attrs)
    else:
        return []


def _compare_cloudwatch_dashboard_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Compare CloudWatch dashboard attributes between Terraform state and live AWS.
    Returns a list of drift details for any mismatched attributes.
    """
    drift_details = []
    state_dashboard_name = state_attrs.get("dashboard_name")
    live_dashboard_name = live_attrs.get("DashboardName")
    if state_dashboard_name != live_dashboard_name:
        drift_details.append(
            {
                "attribute": "dashboard_name",
                "state_value": str(state_dashboard_name),
                "live_value": str(live_dashboard_name),
            }
        )
    return drift_details


def _compare_cloudwatch_alarm_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Compare CloudWatch alarm attributes between Terraform state and live AWS.
    Returns a list of drift details for any mismatched attributes.
    """
    drift_details = []
    state_alarm_name = state_attrs.get("alarm_name")
    live_alarm_name = live_attrs.get("AlarmName")
    if state_alarm_name != live_alarm_name:
        drift_details.append(
            {
                "attribute": "alarm_name",
                "state_value": str(state_alarm_name),
                "live_value": str(live_alarm_name),
            }
        )
    return drift_details
