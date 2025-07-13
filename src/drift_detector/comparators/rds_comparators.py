"""
RDS Resource Comparators Module.

This module contains functions for comparing RDS-related AWS resources.
"""

from typing import Any, Dict, List


def compare_rds_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Compare RDS resource attributes between Terraform state and live AWS.

    Args:
        state_attrs: Attributes from Terraform state resource
        live_attrs: Attributes from live AWS resource

    Returns:
        List of drift details for any mismatched attributes
    """
    drift_details = []
    state_db_identifier = state_attrs.get("db_instance_identifier")
    live_db_identifier = live_attrs.get("DBInstanceIdentifier")
    if state_db_identifier != live_db_identifier:
        drift_details.append(
            {
                "attribute": "db_instance_identifier",
                "state_value": str(state_db_identifier),
                "live_value": str(live_db_identifier),
            }
        )
    return drift_details
