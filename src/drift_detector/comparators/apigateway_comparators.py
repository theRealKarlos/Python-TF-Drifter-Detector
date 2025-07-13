"""
API Gateway Resource Comparators Module.

This module contains functions for comparing API Gateway-related AWS resources.
"""

from typing import Any, Dict, List


def compare_apigateway_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Compare API Gateway resource attributes between Terraform state and live AWS.

    Args:
        state_attrs: Attributes from Terraform state resource
        live_attrs: Attributes from live AWS resource

    Returns:
        List of drift details for any mismatched attributes
    """
    drift_details = []
    state_api_name = state_attrs.get("name")
    live_api_name = live_attrs.get("name")
    if state_api_name != live_api_name:
        drift_details.append(
            {
                "attribute": "api_name",
                "state_value": str(state_api_name),
                "live_value": str(live_api_name),
            }
        )
    return drift_details
