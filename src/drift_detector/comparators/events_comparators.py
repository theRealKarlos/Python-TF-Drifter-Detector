"""
EventBridge Resource Comparators Module.

This module contains functions for comparing EventBridge-related AWS resources.
"""

from typing import Any, Dict, List


def compare_events_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any], resource_type: str
) -> List[Dict[str, Any]]:
    """
    Compare EventBridge resource attributes between Terraform state and live AWS.
    
    Args:
        state_attrs: Attributes from Terraform state resource
        live_attrs: Attributes from live AWS resource
        resource_type: Type of EventBridge resource
        
    Returns:
        List of drift details for any mismatched attributes
    """
    if resource_type.startswith("aws_cloudwatch_event_bus"):
        return _compare_eventbridge_bus_attributes(state_attrs, live_attrs)
    elif resource_type.startswith("aws_cloudwatch_event_rule"):
        return _compare_eventbridge_rule_attributes(state_attrs, live_attrs)
    elif resource_type.startswith("aws_cloudwatch_event_target"):
        return _compare_eventbridge_target_attributes(state_attrs, live_attrs)
    else:
        return []


def _compare_eventbridge_bus_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Compare EventBridge bus attributes between Terraform state and live AWS.
    Returns a list of drift details for any mismatched attributes.
    """
    drift_details = []
    state_bus_name = state_attrs.get("name")
    live_bus_name = live_attrs.get("Name")
    if state_bus_name != live_bus_name:
        drift_details.append(
            {
                "attribute": "bus_name",
                "state_value": str(state_bus_name),
                "live_value": str(live_bus_name),
            }
        )
    return drift_details


def _compare_eventbridge_rule_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Compare EventBridge rule attributes between Terraform state and live AWS.
    Returns a list of drift details for any mismatched attributes.
    """
    drift_details = []
    state_rule_name = state_attrs.get("name")
    live_rule_name = live_attrs.get("Name")
    if state_rule_name != live_rule_name:
        drift_details.append(
            {
                "attribute": "rule_name",
                "state_value": str(state_rule_name),
                "live_value": str(live_rule_name),
            }
        )
    return drift_details


def _compare_eventbridge_target_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Compare EventBridge target attributes between Terraform state and live AWS.
    Returns a list of drift details for any mismatched attributes.
    """
    drift_details = []
    state_target_id = state_attrs.get("target_id")
    live_target_id = live_attrs.get("Id")
    if state_target_id != live_target_id:
        drift_details.append(
            {
                "attribute": "target_id",
                "state_value": str(state_target_id),
                "live_value": str(live_target_id),
            }
        )
    
    state_arn = state_attrs.get("arn")
    live_arn = live_attrs.get("Arn")
    if state_arn != live_arn:
        drift_details.append(
            {
                "attribute": "arn",
                "state_value": str(state_arn),
                "live_value": str(live_arn),
            }
        )
    return drift_details 