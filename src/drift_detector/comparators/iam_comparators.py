"""
IAM Resource Comparators Module.

This module contains functions for comparing IAM-related AWS resources.
"""

import json
from typing import Any, Dict, List

from ..types import DriftDetail


def compare_iam_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any], resource_type: str
) -> List[DriftDetail]:
    """
    Compare IAM resource attributes between Terraform state and live AWS.

    Args:
        state_attrs: Attributes from Terraform state resource
        live_attrs: Attributes from live AWS resource
        resource_type: Type of IAM resource

    Returns:
        List of drift details for any mismatched attributes
    """
    if resource_type.startswith("aws_iam_role_policy"):
        return _compare_iam_role_policy_attributes(state_attrs, live_attrs)
    elif resource_type.startswith("aws_iam_role"):
        return _compare_iam_role_attributes(state_attrs, live_attrs)
    elif resource_type.startswith("aws_iam_policy"):
        return _compare_iam_policy_attributes(state_attrs, live_attrs)
    elif resource_type.startswith("aws_iam_openid_connect_provider"):
        return _compare_iam_openid_connect_provider_attributes(state_attrs, live_attrs)
    else:
        return []


def _compare_iam_role_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any]
) -> List[DriftDetail]:
    """
    Compare IAM role attributes between Terraform state and live AWS.
    Returns a list of drift details for any mismatched attributes.
    """
    drift_details = []
    state_role_name = state_attrs.get("name")
    live_role_name = live_attrs.get("RoleName")
    if state_role_name != live_role_name:
        drift_details.append(
            {
                "attribute": "role_name",
                "state_value": str(state_role_name),
                "live_value": str(live_role_name),
            }
        )
    return drift_details


def _compare_iam_policy_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any]
) -> List[DriftDetail]:
    """
    Compare IAM policy attributes between Terraform state and live AWS.
    Returns a list of drift details for any mismatched attributes.
    """
    drift_details = []
    state_policy_name = state_attrs.get("name")
    live_policy_name = live_attrs.get("PolicyName")
    if state_policy_name != live_policy_name:
        drift_details.append(
            {
                "attribute": "policy_name",
                "state_value": str(state_policy_name),
                "live_value": str(live_policy_name),
            }
        )
    return drift_details


def _compare_iam_role_policy_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any]
) -> List[DriftDetail]:
    """
    Compare IAM role policy attributes between Terraform state and live AWS.
    This comparator normalises policy document format differences (e.g. JSON string vs dict),
    so only real content drift is reported. This prevents false positives when the state file
    stores the policy as a JSON string and AWS returns it as a dict.

    Args:
        state_attrs: Attributes from Terraform state resource (may have policy as JSON string)
        live_attrs: Attributes from live AWS resource (policy as dict)

    Returns:
        List of drift details for any mismatched attributes
    """
    drift_details = []
    # Compare role name
    state_role = state_attrs.get("role")
    live_role = live_attrs.get("role_name")
    if state_role != live_role:
        drift_details.append(
            {
                "attribute": "role_name",
                "state_value": str(state_role),
                "live_value": str(live_role),
            }
        )
    # Compare policy name
    state_policy = state_attrs.get("name")
    live_policy = live_attrs.get("policy_name")
    if state_policy != live_policy:
        drift_details.append(
            {
                "attribute": "policy_name",
                "state_value": str(state_policy),
                "live_value": str(live_policy),
            }
        )
    # Compare policy document (normalised comparison)
    state_policy_doc = state_attrs.get("policy")
    live_policy_doc = live_attrs.get("policy")
    if state_policy_doc and live_policy_doc:
        try:
            # Parse state policy if it's a string (Terraform state stores as JSON string)
            if isinstance(state_policy_doc, str):
                state_policy_parsed = json.loads(state_policy_doc)
            else:
                state_policy_parsed = state_policy_doc
            # Compare the parsed content (dict vs dict)
            if state_policy_parsed != live_policy_doc:
                drift_details.append(
                    {
                        "attribute": "policy_document",
                        "state_value": str(state_policy_doc),
                        "live_value": str(live_policy_doc),
                    }
                )
        except (json.JSONDecodeError, TypeError):
            # If parsing fails, fall back to string comparison
            if state_policy_doc != live_policy_doc:
                drift_details.append(
                    {
                        "attribute": "policy_document",
                        "state_value": str(state_policy_doc),
                        "live_value": str(live_policy_doc),
                    }
                )
    elif state_policy_doc != live_policy_doc:
        # Handle case where one is None/empty and the other isn't
        drift_details.append(
            {
                "attribute": "policy_document",
                "state_value": str(state_policy_doc),
                "live_value": str(live_policy_doc),
            }
        )
    return drift_details


def _compare_iam_openid_connect_provider_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any]
) -> List[DriftDetail]:
    """
    Compare IAM OpenID Connect provider attributes between Terraform state and live AWS.
    Returns a list of drift details for any mismatched attributes.
    """
    drift_details = []
    state_provider_arn = state_attrs.get("arn")
    live_provider_arn = live_attrs.get("arn")
    if state_provider_arn != live_provider_arn:
        drift_details.append(
            {
                "attribute": "provider_arn",
                "state_value": str(state_provider_arn),
                "live_value": str(live_provider_arn),
            }
        )
    return drift_details
