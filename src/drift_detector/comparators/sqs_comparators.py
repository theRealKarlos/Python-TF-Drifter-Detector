"""
SQS Resource Comparators Module.

This module contains functions for comparing SQS-related AWS resources.

Key points:
- Strict attribute matching: Only report drift if the state and live values are actually
  different.
- String conversion: State and live values may differ in type (e.g., integer vs string),
  so we convert both to strings before comparison to avoid false positives.
- British English spelling is used throughout comments and documentation.
"""

from typing import Any, Dict, List


def compare_sqs_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any], resource_type: str = ""
) -> List[Dict[str, Any]]:
    """
    Compare SQS resource attributes between Terraform state and live AWS.

    Args:
        state_attrs: Attributes from Terraform state resource
        live_attrs: Attributes from live AWS resource
        resource_type: Type of SQS resource (optional, for routing)

    Returns:
        List of drift details for any mismatched attributes
    """
    return _compare_sqs_queue_attributes(state_attrs, live_attrs)


def _compare_sqs_queue_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Compare SQS queue attributes between Terraform state and live AWS.
    Only report drift if the values are actually different (after string conversion).
    Returns a list of drift details for any mismatched attributes.
    """
    drift_details = []

    # Compare queue name
    state_name = state_attrs.get("name")
    live_name = (
        live_attrs.get("QueueArn", "").split(":")[-1]
        if live_attrs.get("QueueArn")
        else ""
    )
    # Convert both to string for strict comparison
    if str(state_name) != str(live_name):
        drift_details.append(
            {
                "attribute": "name",
                "state_value": str(state_name),
                "live_value": str(live_name),
            }
        )

    # Compare visibility timeout
    state_visibility_timeout = state_attrs.get("visibility_timeout_seconds")
    live_visibility_timeout = live_attrs.get("VisibilityTimeout")
    if str(state_visibility_timeout) != str(live_visibility_timeout):
        drift_details.append(
            {
                "attribute": "visibility_timeout_seconds",
                "state_value": str(state_visibility_timeout),
                "live_value": str(live_visibility_timeout),
            }
        )

    # Compare message retention period
    state_retention = state_attrs.get("message_retention_seconds")
    live_retention = live_attrs.get("MessageRetentionPeriod")
    if str(state_retention) != str(live_retention):
        drift_details.append(
            {
                "attribute": "message_retention_seconds",
                "state_value": str(state_retention),
                "live_value": str(live_retention),
            }
        )

    # Compare maximum message size
    state_max_size = state_attrs.get("max_message_size")
    live_max_size = live_attrs.get("MaximumMessageSize")
    if str(state_max_size) != str(live_max_size):
        drift_details.append(
            {
                "attribute": "max_message_size",
                "state_value": str(state_max_size),
                "live_value": str(live_max_size),
            }
        )

    # Compare delay seconds
    state_delay = state_attrs.get("delay_seconds")
    live_delay = live_attrs.get("DelaySeconds")
    if str(state_delay) != str(live_delay):
        drift_details.append(
            {
                "attribute": "delay_seconds",
                "state_value": str(state_delay),
                "live_value": str(live_delay),
            }
        )

    return drift_details
