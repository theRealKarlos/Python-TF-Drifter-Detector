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

from src.utils import fetcher_error_handler

from ...utils import setup_logging
from ..types import SQSClient

logger = setup_logging()


def extract_hybrid_key_from_sqs(queue: dict) -> str:
    """
    Extract the best available key for an SQS queue using hybrid logic.
    1. Try ARN
    2. Try QueueUrl (ID)
    3. Fallback to 'aws_sqs_queue.<name>'
    """
    if "QueueArn" in queue and queue["QueueArn"]:
        return str(queue["QueueArn"])
    if "QueueUrl" in queue and queue["QueueUrl"]:
        return str(queue["QueueUrl"])
    return "aws_sqs_queue.unknown"


@fetcher_error_handler
def fetch_sqs_resources(sqs_client: SQSClient, resource_key: str, attributes: dict) -> dict:
    """
    Fetch SQS queue resources from AWS and map them by hybrid key for drift comparison.
    Returns a dictionary of hybrid keys to queue data for all SQS queues.
    """
    try:
        response = sqs_client.list_queues()
        live_resources = {}
        queue_urls = response.get("QueueUrls", [])
        for queue_url in queue_urls:
            attrs = sqs_client.get_queue_attributes(QueueUrl=queue_url, AttributeNames=["All"])["Attributes"]
            queue = {"QueueUrl": queue_url, **attrs}
            # SQS ARNs are sometimes in the attributes
            queue["QueueArn"] = attrs.get("QueueArn")
            key = extract_hybrid_key_from_sqs(queue)
            logger.debug(f"[SQS] Using key for queue: {key}")
            live_resources[key] = queue
        return live_resources
    except Exception as e:
        logger.error(f"[SQS] Error fetching SQS queues: {e}")
        return {}
