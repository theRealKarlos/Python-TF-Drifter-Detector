"""
SQS Resource Fetchers Module.

This module contains functions for fetching SQS-related AWS resources.

Key points:
- Strict matching: Only queues with an exact name match are considered. No fallback is
  allowed, to avoid false positives.
- Name normalisation: The Terraform state may provide the queue name as either the actual
  name or the full URL. We always normalise to the queue name for comparison.
- Debug output: Prints are included to aid debugging and show matching logic in action.
"""

from typing import Dict
from ..types import (
    SQSClient,
    ResourceAttributes,
    LiveResourceData,
)
from ...utils import setup_logging

logger = setup_logging()


def fetch_sqs_resources(
    sqs_client: SQSClient,
    resource_key: str,
    attributes: ResourceAttributes,
    resource_type: str = "",
) -> Dict[str, LiveResourceData]:
    """
    Fetch SQS resources from AWS based on resource type.

    Args:
        sqs_client: Boto3 SQS client
        resource_key: Resource key for mapping
        attributes: Resource attributes from Terraform state
        resource_type: Type of SQS resource (optional, for routing)

    Returns:
        Dictionary mapping resource keys to live AWS resource data
    """
    return _fetch_sqs_queues(sqs_client, resource_key, attributes)


def _fetch_sqs_queues(
    sqs_client: SQSClient, resource_key: str, attributes: ResourceAttributes
) -> Dict[str, LiveResourceData]:
    """
    Fetch SQS queues from AWS and map them by resource key for drift comparison.
    Only queues with an exact name match are considered. This strictness avoids
    false positives. The queue name from state may be a URL or a name; we always
    normalise to the name. Returns a dictionary of resource keys to queue data.
    """
    try:
        response = sqs_client.list_queues()
        live_resources = {}
        queue_name = attributes.get("name") or attributes.get("id")
        # Normalise: if queue_name is a URL, extract the last part
        if (
            queue_name
            and isinstance(queue_name, str)
            and queue_name.startswith("https://")
        ):
            queue_name = queue_name.split("/")[-1]

        logger.debug(f"[SQS] State queue_name: {queue_name}")
        logger.debug(f"[SQS] AWS QueueUrls: {response.get('QueueUrls', [])}")

        for queue_url in response.get("QueueUrls", []):
            # Extract queue name from URL
            queue_name_from_url = queue_url.split("/")[-1]
            logger.debug(f"[SQS] Checking AWS queue: {queue_name_from_url}")

            if queue_name and queue_name_from_url == queue_name:
                logger.debug(f"[SQS] Matched queue: {queue_name_from_url}")
                # Get detailed queue attributes
                queue_attributes = sqs_client.get_queue_attributes(
                    QueueUrl=queue_url, AttributeNames=["All"]
                )
                live_resources[resource_key] = queue_attributes["Attributes"]
                return live_resources

        logger.debug("[SQS] No matching queue found for state queue_name.")
        # If no exact match, return empty dict (no fallback)
        return live_resources
    except Exception as e:
        logger.error(f"[SQS] Error fetching SQS queues: {e}")
        return {}
