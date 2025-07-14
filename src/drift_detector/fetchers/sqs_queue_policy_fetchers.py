"""
Fetcher for AWS SQS Queue Policy resources.
Fetches only the policy document for a given SQS queue policy.
"""
from typing import Any, Dict
import boto3
from botocore.exceptions import ClientError
import traceback
from src.utils import fetcher_error_handler
import sys

class SQSQueuePolicyFetcher:
    """
    Fetches the policy document for an AWS SQS queue policy resource.
    """
    resource_type = "aws_sqs_queue_policy"

    # @fetcher_error_handler
    def fetch_live_resource(self, resource_id: str, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetches the live policy document for the given SQS queue policy resource.
        Returns a dictionary with the 'policy' key. If the policy does not exist, returns an empty string.
        Includes detailed debug output for all steps and error cases.
        """
        print(f"FORCE DEBUG: [fetcher] called for resource_id={resource_id!r}, attributes={attributes!r}")
        sys.stdout.flush()
        region = attributes.get('region')
        print(f"FORCE DEBUG: [fetcher] region for boto3 client: {region!r}")
        sys.stdout.flush()
        queue_url = attributes.get('queue_url') or attributes.get('id')
        print(f"FORCE DEBUG: [fetcher] using queue_url={queue_url!r}")
        sys.stdout.flush()
        if not queue_url:
            print(f"FORCE DEBUG: [fetcher] No queue_url found in attributes for resource_id={resource_id!r}")
            sys.stdout.flush()
            # Return an empty string for missing policy, as per AWS behaviour
            return {'policy': ''}
        try:
            print("FORCE DEBUG: [fetcher] about to create boto3 client")
            sys.stdout.flush()
            sqs = boto3.client('sqs', region_name=region)
            print("FORCE DEBUG: [fetcher] boto3 client created")
            sys.stdout.flush()
        except Exception as e:
            print(f"FORCE DEBUG: [fetcher] Exception during boto3 client creation: {e}")
            traceback.print_exc()
            sys.stdout.flush()
            # Return an empty string for missing policy on error
            return {'policy': ''}
        print(f"FORCE DEBUG: [fetcher] calling get_queue_attributes for queue_url={queue_url!r}")
        sys.stdout.flush()
        try:
            response = sqs.get_queue_attributes(QueueUrl=queue_url, AttributeNames=['Policy'])
            print(f"FORCE DEBUG: [fetcher] AWS response for {queue_url!r}: {response!r}")
            sys.stdout.flush()
            # AWS returns 'Policy' only if it exists; otherwise, it is absent
            policy = response.get('Attributes', {}).get('Policy', '')
            print(f"FORCE DEBUG: [fetcher] extracted policy: {policy!r}")
            sys.stdout.flush()
            return {'policy': policy}
        except Exception as e:
            print(f"FORCE DEBUG: [fetcher] Exception during get_queue_attributes: {e}")
            traceback.print_exc()
            sys.stdout.flush()
            # Return an empty string for missing policy on error
            return {'policy': ''} 