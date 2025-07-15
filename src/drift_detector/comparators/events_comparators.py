"""
EventBridge Resource Comparators Module.

This module contains functions for comparing EventBridge-related AWS resources.
"""

from typing import Any, Dict, List

from ..types import DriftDetail


def compare_events_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any], resource_type: str
) -> List[DriftDetail]:
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


def _normalise_optional(val: Any) -> Any:
    """
    Normalise optional string fields so that both '' and None are treated as None.
    This avoids false drift reports when Terraform and AWS represent unset fields differently.
    """
    return val if val not in (None, "") else None


def _normalise_target_optional(val: Any) -> Any:
    """
    Normalise optional EventBridge target fields so that None, '' and [] are treated as None.
    This avoids false drift reports when Terraform and AWS represent unset fields differently.
    """
    if val in (None, ""):
        return None
    if isinstance(val, list) and len(val) == 0:
        return None
    return val


def _compare_eventbridge_bus_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any]
) -> List[DriftDetail]:
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
) -> List[DriftDetail]:
    """
    Compare EventBridge rule attributes between Terraform state and live AWS.
    Returns a list of drift details for any mismatched attributes.
    """
    drift_details = []
    
    # Compare basic rule attributes
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
    
    # Compare event pattern if present
    state_event_pattern = state_attrs.get("event_pattern")
    live_event_pattern = live_attrs.get("EventPattern")
    if state_event_pattern != live_event_pattern:
        drift_details.append(
            {
                "attribute": "event_pattern",
                "state_value": str(state_event_pattern),
                "live_value": str(live_event_pattern),
            }
        )
    
    # Compare schedule expression if present (normalised)
    state_schedule = _normalise_optional(state_attrs.get("schedule_expression"))
    live_schedule = _normalise_optional(live_attrs.get("ScheduleExpression"))
    if state_schedule != live_schedule:
        drift_details.append(
            {
                "attribute": "schedule_expression",
                "state_value": str(state_attrs.get("schedule_expression")),
                "live_value": str(live_attrs.get("ScheduleExpression")),
            }
        )
    
    # Compare description if present (normalised)
    state_description = _normalise_optional(state_attrs.get("description"))
    live_description = _normalise_optional(live_attrs.get("Description"))
    if state_description != live_description:
        drift_details.append(
            {
                "attribute": "description",
                "state_value": str(state_attrs.get("description")),
                "live_value": str(live_attrs.get("Description")),
            }
        )
    
    # Compare role ARN if present (normalised)
    state_role_arn = _normalise_optional(state_attrs.get("role_arn"))
    live_role_arn = _normalise_optional(live_attrs.get("RoleArn"))
    if state_role_arn != live_role_arn:
        drift_details.append(
            {
                "attribute": "role_arn",
                "state_value": str(state_attrs.get("role_arn")),
                "live_value": str(live_attrs.get("RoleArn")),
            }
        )
    
    # Compare state if present
    state_state = state_attrs.get("state")
    live_state = live_attrs.get("State")
    if state_state != live_state:
        drift_details.append(
            {
                "attribute": "state",
                "state_value": str(state_state),
                "live_value": str(live_state),
            }
        )
    
    return drift_details


def _compare_eventbridge_target_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any]
) -> List[DriftDetail]:
    """
    Compare EventBridge target attributes between Terraform state and live AWS.
    Returns a list of drift details for any mismatched attributes.
    """
    import logging
    logger = logging.getLogger("drift_detector.comparators.events_comparators")
    logger.debug(f"[EventBridge] (EXTRA) Comparing EventBridge target attributes:\n  State: {state_attrs}\n  Live: {live_attrs}")
    print(f"[EventBridge] (EXTRA) Comparing EventBridge target attributes:\n  State: {state_attrs}\n  Live: {live_attrs}")
    drift_details = []
    # Only compare EventBridge target attributes
    for attr in ["target_id", "arn"]:
        state_val = state_attrs.get(attr)
        live_val = live_attrs.get(attr)
        logger.debug(f"[EventBridge] (EXTRA) Comparing attribute '{attr}': State='{state_val}' Live='{live_val}'")
        print(f"[EventBridge] (EXTRA) Comparing attribute '{attr}': State='{state_val}' Live='{live_val}'")
        if state_val != live_val:
            drift_details.append(
                {
                    "attribute": attr,
                    "state_value": str(state_val),
                    "live_value": str(live_val),
                }
            )
    for attr in ["input", "input_path", "input_transformer"]:
        state_val = _normalise_target_optional(state_attrs.get(attr))
        live_val = _normalise_target_optional(live_attrs.get(attr))
        logger.debug(f"[EventBridge] (EXTRA) Comparing attribute '{attr}': State='{state_val}' Live='{live_val}' (normalised)")
        print(f"[EventBridge] (EXTRA) Comparing attribute '{attr}': State='{state_val}' Live='{live_val}' (normalised)")
        if state_val != live_val:
            drift_details.append(
                {
                    "attribute": attr,
                    "state_value": str(state_attrs.get(attr)),
                    "live_value": str(live_attrs.get(attr)),
                }
            )
    return drift_details
