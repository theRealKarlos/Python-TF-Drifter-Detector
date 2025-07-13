"""
S3 Resource Comparators Module.

This module contains functions for comparing S3-related AWS resources.
"""

from typing import Any, Dict, List


def compare_s3_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Compare S3 resource attributes between Terraform state and live AWS.

    Args:
        state_attrs: Attributes from Terraform state resource
        live_attrs: Attributes from live AWS resource

    Returns:
        List of drift details for any mismatched attributes
    """
    drift_details = []
    state_bucket_name = state_attrs.get("bucket")
    live_bucket_name = live_attrs.get("Name")
    if state_bucket_name != live_bucket_name:
        drift_details.append(
            {
                "attribute": "bucket_name",
                "state_value": str(state_bucket_name),
                "live_value": str(live_bucket_name),
            }
        )
    return drift_details
