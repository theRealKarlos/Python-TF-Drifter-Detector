"""
CloudWatch Resource Comparators Module.

This module contains functions for comparing CloudWatch-related AWS resources.
"""

from typing import Any, Dict, List

from ..types import DriftDetail


def compare_cloudwatch_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any], resource_type: str
) -> List[DriftDetail]:
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


def _compare_cloudwatch_dashboard_attributes(state_attrs: Dict[str, Any], live_attrs: Dict[str, Any]) -> List[DriftDetail]:
    """
    Compare CloudWatch dashboard attributes between Terraform state and live AWS.
    Only compare DashboardArn and DashboardBody, as AWS does not return dashboard_name in the live resource.
    Returns a list of drift details for any mismatched attributes.
    """
    drift_details = []
    # Compare DashboardArn if present in both
    state_arn = state_attrs.get("dashboard_arn") or state_attrs.get("DashboardArn")
    live_arn = live_attrs.get("DashboardArn")
    if state_arn and live_arn and state_arn != live_arn:
        drift_details.append(
            {
                "attribute": "DashboardArn",
                "state_value": str(state_arn),
                "live_value": str(live_arn),
            }
        )
    # Compare DashboardBody if present in both
    state_body = state_attrs.get("dashboard_body") or state_attrs.get("DashboardBody")
    live_body = live_attrs.get("DashboardBody")
    if state_body and live_body and state_body != live_body:
        drift_details.append(
            {
                "attribute": "DashboardBody",
                "state_value": str(state_body),
                "live_value": str(live_body),
            }
        )
    # Do NOT compare dashboard_name, as AWS does not return it in the live resource
    return drift_details


def _compare_cloudwatch_alarm_attributes(state_attrs: Dict[str, Any], live_attrs: Dict[str, Any]) -> List[DriftDetail]:
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
