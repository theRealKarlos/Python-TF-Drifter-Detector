"""
Lambda Resource Comparators Module.

This module contains functions for comparing Lambda-related AWS resources.
"""

from typing import Any, Dict, List

from ..types import DriftDetail


def compare_lambda_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any], resource_type: str = ""
) -> List[DriftDetail]:
    """
    Compare Lambda resource attributes between Terraform state and live AWS.

    Args:
        state_attrs: Attributes from Terraform state resource
        live_attrs: Attributes from live AWS resource
        resource_type: Type of Lambda resource (optional, for routing)

    Returns:
        List of drift details for any mismatched attributes
    """
    if resource_type and resource_type.startswith("aws_lambda_permission"):
        return _compare_lambda_permission_attributes(state_attrs, live_attrs)
    else:
        return _compare_lambda_function_attributes(state_attrs, live_attrs)


def _compare_lambda_function_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any]
) -> List[DriftDetail]:
    """
    Compare Lambda function attributes between Terraform state and live AWS.
    Returns a list of drift details for any mismatched attributes.
    """
    print(f"DEBUG: Lambda function comparator called with state_attrs: {list(state_attrs.keys())}")
    print(f"DEBUG: Lambda function comparator called with live_attrs: {list(live_attrs.keys())}")
    
    drift_details = []
    state_function_name = state_attrs.get("function_name")
    live_function_name = live_attrs.get("FunctionName")
    if state_function_name != live_function_name:
        drift_details.append(
            {
                "attribute": "function_name",
                "state_value": str(state_function_name),
                "live_value": str(live_function_name),
            }
        )
    return drift_details


def _compare_lambda_permission_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any]
) -> List[DriftDetail]:
    """
    Compare Lambda permission attributes between Terraform state and live AWS.
    Returns a list of drift details for any mismatched attributes.
    """
    drift_details = []
    state_statement_id = state_attrs.get("statement_id")
    live_statement_id = live_attrs.get("Sid")
    if state_statement_id != live_statement_id:
        drift_details.append(
            {
                "attribute": "statement_id",
                "state_value": str(state_statement_id),
                "live_value": str(live_statement_id),
            }
        )

    state_action = state_attrs.get("action")
    live_action = live_attrs.get("Action")
    if state_action != live_action:
        drift_details.append(
            {
                "attribute": "action",
                "state_value": str(state_action),
                "live_value": str(live_action),
            }
        )

    state_principal = state_attrs.get("principal")
    live_principal = live_attrs.get("Principal")

    # Handle different principal formats
    # State might have "events.amazonaws.com" while AWS returns {"Service": "events.amazonaws.com"}
    if isinstance(live_principal, dict) and "Service" in live_principal:
        live_principal_service = live_principal["Service"]
    else:
        live_principal_service = live_principal

    if state_principal != live_principal_service:
        drift_details.append(
            {
                "attribute": "principal",
                "state_value": str(state_principal),
                "live_value": str(live_principal),
            }
        )
    return drift_details
