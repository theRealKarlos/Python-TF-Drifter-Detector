"""
Base AWS Resource Fetchers Module.

This module contains the main orchestration logic for fetching live AWS resources
and initializes AWS service clients for all supported services.
"""

from typing import Any, Dict

import boto3


def get_live_aws_resources(
    state_data: Dict, region_name: str = "eu-west-2"
) -> Dict[str, Any]:
    """
    Fetches live AWS resources based on what's found in the Terraform state.

    This function iterates through all resources in the Terraform state and
    fetches corresponding live AWS resources for comparison. It supports
    multiple AWS services and handles API errors gracefully.

    Args:
        state_data: Parsed Terraform state data containing resource definitions
        region_name: AWS region to use for boto3 clients (default: 'eu-west-2')

    Returns:
        Dictionary mapping resource keys to live AWS resource data
    """
    live_resources = {}

    # Initialize AWS service clients for all supported services
    # Each client is used to fetch live resources from the respective AWS service
    ec2_client = boto3.client("ec2", region_name=region_name)
    s3_client = boto3.client("s3", region_name=region_name)
    rds_client = boto3.client("rds", region_name=region_name)
    dynamodb_client = boto3.client("dynamodb", region_name=region_name)
    lambda_client = boto3.client("lambda", region_name=region_name)
    iam_client = boto3.client("iam", region_name=region_name)
    sts_client = boto3.client("sts", region_name=region_name)
    events_client = boto3.client("events", region_name=region_name)
    ecs_client = boto3.client("ecs", region_name=region_name)
    apigateway_client = boto3.client("apigateway", region_name=region_name)
    cloudwatch_client = boto3.client("cloudwatch", region_name=region_name)

    # Import service-specific fetchers
    from .ec2_fetchers import fetch_ec2_resources
    from .s3_fetchers import fetch_s3_resources
    from .rds_fetchers import fetch_rds_resources
    from .dynamodb_fetchers import fetch_dynamodb_resources
    from .lambda_fetchers import fetch_lambda_resources
    from .iam_fetchers import fetch_iam_resources
    from .events_fetchers import fetch_events_resources
    from .ecs_fetchers import fetch_ecs_resources
    from .apigateway_fetchers import fetch_apigateway_resources
    from .cloudwatch_fetchers import fetch_cloudwatch_resources
    from .data_source_fetchers import fetch_data_source_resources

    # Iterate through each resource defined in the Terraform state
    for resource in state_data.get("resources", []):
        resource_type = resource.get("type", "")
        resource_name = resource.get("name", "")
        resource_key = f"{resource_type}.{resource_name}"

        # Get the resource instance data for better matching
        instances = resource.get("instances", [])
        if not instances:
            continue

        instance = instances[0]
        attributes = instance.get("attributes", {})

        # Route to appropriate service-specific fetcher
        if resource_type.startswith("aws_instance"):
            live_resources.update(
                fetch_ec2_resources(ec2_client, resource_key, attributes)
            )
        elif resource_type.startswith("aws_s3_bucket"):
            live_resources.update(
                fetch_s3_resources(s3_client, resource_key, attributes)
            )
        elif resource_type.startswith("aws_db_instance"):
            live_resources.update(
                fetch_rds_resources(rds_client, resource_key, attributes)
            )
        elif resource_type.startswith("aws_dynamodb_table"):
            live_resources.update(
                fetch_dynamodb_resources(dynamodb_client, resource_key, attributes)
            )
        elif resource_type.startswith("aws_lambda_function"):
            live_resources.update(
                fetch_lambda_resources(lambda_client, resource_key, attributes)
            )
        elif resource_type.startswith("aws_iam_role_policy") or resource_type.startswith("aws_iam_role") or resource_type.startswith("aws_iam_policy") or resource_type.startswith("aws_iam_openid_connect_provider"):
            live_resources.update(
                fetch_iam_resources(iam_client, resource_key, attributes, resource_type)
            )
        elif resource_type.startswith("aws_cloudwatch_event_bus") or resource_type.startswith("aws_cloudwatch_event_rule") or resource_type.startswith("aws_cloudwatch_event_target"):
            live_resources.update(
                fetch_events_resources(events_client, resource_key, attributes, resource_type)
            )
        elif resource_type.startswith("aws_lambda_permission"):
            live_resources.update(
                fetch_lambda_resources(lambda_client, resource_key, attributes, resource_type)
            )
        elif resource_type.startswith("aws_ecs_cluster") or resource_type.startswith("aws_ecs_service"):
            live_resources.update(
                fetch_ecs_resources(ecs_client, resource_key, attributes, resource_type)
            )
        elif resource_type.startswith("aws_vpc"):
            live_resources.update(
                fetch_ec2_resources(ec2_client, resource_key, attributes, resource_type)
            )
        elif resource_type.startswith("aws_api_gateway_rest_api"):
            live_resources.update(
                fetch_apigateway_resources(apigateway_client, resource_key, attributes)
            )
        elif resource_type.startswith("aws_cloudwatch_dashboard") or resource_type.startswith("aws_cloudwatch_metric_alarm"):
            live_resources.update(
                fetch_cloudwatch_resources(cloudwatch_client, resource_key, attributes, resource_type)
            )
        elif resource_type.startswith("aws_region") or resource_type.startswith("aws_caller_identity"):
            live_resources.update(
                fetch_data_source_resources(sts_client, region_name, resource_key, attributes, resource_type)
            )

    return live_resources 