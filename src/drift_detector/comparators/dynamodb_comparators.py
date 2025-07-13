"""
DynamoDB Resource Comparators Module.

This module contains functions for comparing DynamoDB-related AWS resources.
"""

from typing import Any, Dict, List

from ..types import DriftDetail


def compare_dynamodb_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any]
) -> List[DriftDetail]:
    """
    Compare DynamoDB resource attributes between Terraform state and live AWS.

    Args:
        state_attrs: Attributes from Terraform state resource
        live_attrs: Attributes from live AWS resource

    Returns:
        List of drift details for any mismatched attributes
    """
    drift_details = []
    state_table_name = state_attrs.get("name")
    live_table_name = live_attrs.get("TableName")
    if state_table_name != live_table_name:
        drift_details.append(
            {
                "attribute": "table_name",
                "state_value": str(state_table_name),
                "live_value": str(live_table_name),
            }
        )
    return drift_details
