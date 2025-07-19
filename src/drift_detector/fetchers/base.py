"""
Base AWS Resource Fetchers Module.

This module contains the main orchestration logic for fetching live AWS resources
and initialises AWS service clients for all supported services.
"""

from typing import Any, Dict

import boto3

from ..types import (
    APIGatewayClient,
    CloudWatchClient,
    DynamoDBClient,
    EC2Client,
    ECSClient,
    EventsClient,
    IAMClient,
    LambdaClient,
    RDSClient,
    S3Client,
    SQSClient,
    STSClient,
)


def extract_arn_from_attributes(attributes: Dict[str, Any], resource_type: str) -> str:
    """
    Extract ARN from resource attributes.

    This function looks for ARN fields in the resource attributes and returns
    the first valid ARN found. It checks multiple possible ARN field names
    to handle different resource types and naming conventions.

    Args:
        attributes: Resource attributes from Terraform state
        resource_type: Type of AWS resource

    Returns:
        ARN string if found

    Raises:
        ValueError: If no valid ARN is found for the resource type
    """
    # Special handling for resources that don't have ARNs
    if resource_type.startswith("aws_route_table"):
        # Route tables don't have ARNs in the same way as other resources
        # This will be handled by the specific fetcher using ID-based matching
        raise ValueError(
            f"Resource type '{resource_type}' does not support ARN-based matching. " f"Use ID-based matching instead."
        )

    # Check for common ARN field names
    arn_fields = ["arn", "Arn", "ARN"]
    for field in arn_fields:
        if field in attributes:
            arn_value = attributes[field]
            if arn_value and isinstance(arn_value, str) and arn_value.startswith("arn:aws:"):
                return str(arn_value)

    # Check for service-specific ARN fields
    if resource_type.startswith("aws_lambda_function"):
        function_arn = attributes.get("invoke_arn") or attributes.get("function_arn")
        if function_arn and isinstance(function_arn, str) and function_arn.startswith("arn:aws:"):
            return str(function_arn)

    # Check for 'id' field that might be an ARN
    if "id" in attributes:
        id_value = attributes["id"]
        if id_value and isinstance(id_value, str) and id_value.startswith("arn:aws:"):
            return str(id_value)

    # If we still haven't found an ARN, look for any field ending with '_arn'
    for field_name, field_value in attributes.items():
        if (
            field_name.endswith("_arn")
            and field_value
            and isinstance(field_value, str)
            and field_value.startswith("arn:aws:")
        ):
            return str(field_value)

    # Final fallback: look for any field containing 'arn' in the name
    for field_name, field_value in attributes.items():
        if (
            "arn" in field_name.lower()
            and field_value
            and isinstance(field_value, str)
            and field_value.startswith("arn:aws:")
        ):
            return str(field_value)

    # If no ARN is found, this indicates a problem with the state file
    # or an unsupported resource type
    available_fields = list(attributes.keys())
    raise ValueError(
        f"No valid ARN found for resource type '{resource_type}'. "
        f"Available fields: {available_fields}. "
        f"This may indicate an unsupported resource type or a corrupted state file."
    )


def get_resource_identifier(attributes: Dict[str, Any], resource_type: str, resource_name: str) -> Dict[str, Any]:
    """
    Get the ARN-based identifier for a resource.

    This function uses ARN-based identification exclusively, as ARNs are
    always present for AWS managed resources that support them.

    Args:
        attributes: Resource attributes from Terraform state
        resource_type: Type of AWS resource
        resource_name: Name of the resource in Terraform

    Returns:
        Dictionary containing ARN-based identifier information
    """
    arn = extract_arn_from_attributes(attributes, resource_type)

    return {
        "primary_identifier": "arn",
        "arn": arn,
        "resource_type": resource_type,
        "resource_name": resource_name,
        # Keep some additional identifiers for debugging purposes
        "debug_info": {
            "name": attributes.get("name"),
            "id": attributes.get("id"),
            "function_name": attributes.get("function_name"),
            "role_name": attributes.get("role_name"),
            "policy_name": attributes.get("policy_name"),
            "queue_name": attributes.get("name"),  # For SQS queues
        },
    }


def extract_apigateway_key(attributes: dict, resource_type: str, resource_name: str, idx: int) -> str:
    """
    Extract the best key for API Gateway resources, preferring:
    1. ARN (if available)
    2. ID (if available)
    3. Composite key (for methods/integrations)
    4. Fallback to resource_type.name_idx
    """
    # Try ARN
    arn = attributes.get("arn")
    if arn:
        return str(arn)
    # Try ID
    resource_id = attributes.get("id")
    if resource_id:
        return str(resource_id)
    # Try composite key for methods/integrations
    if resource_type == "aws_api_gateway_method":
        rest_api_id = attributes.get("rest_api_id") or attributes.get("restApiId")
        resource_id = attributes.get("resource_id") or attributes.get("resourceId") or attributes.get("id")
        http_method = attributes.get("http_method") or attributes.get("httpMethod")
        if rest_api_id and resource_id and http_method:
            return f"agm-{rest_api_id}-{resource_id}-{http_method}"
    if resource_type == "aws_api_gateway_integration":
        rest_api_id = attributes.get("rest_api_id") or attributes.get("restApiId")
        resource_id = attributes.get("resource_id") or attributes.get("resourceId") or attributes.get("id")
        http_method = attributes.get("http_method") or attributes.get("httpMethod")
        if rest_api_id and resource_id and http_method:
            return f"apigw_integration:{rest_api_id}:{resource_id}:{http_method}"
    # Fallback
    return f"{resource_type}.{resource_name}_{idx}"


def extract_hybrid_key_from_apigateway(resource: dict, resource_type: str, resource_id: str = "") -> str:
    """
    Extract the best available key for an API Gateway resource using hybrid logic.
    1. Try ARN
    2. Try ID
    3. Fallback to resource_type.<id>
    """
    # For API Gateway resources, we'll use the ID as the primary key since ARNs are complex
    if resource_id:
        return str(resource_id)

    # Try to extract ID from the resource
    for id_key in (
        "id",
        "Id",
        "ID",
        "restApiId",
        "resourceId",
        "deploymentId",
        "stageName",
    ):
        if id_key in resource and resource[id_key]:
            value = resource[id_key]
            if isinstance(value, str):
                return value
            return str(value)

    return f"{resource_type}.unknown"


def get_live_aws_resources(state_data: Dict, region_name: str = "eu-west-2") -> Dict[str, Any]:
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
    ec2_client: EC2Client = boto3.client("ec2", region_name=region_name)
    s3_client: S3Client = boto3.client("s3", region_name=region_name)
    rds_client: RDSClient = boto3.client("rds", region_name=region_name)
    dynamodb_client: DynamoDBClient = boto3.client("dynamodb", region_name=region_name)
    lambda_client: LambdaClient = boto3.client("lambda", region_name=region_name)
    iam_client: IAMClient = boto3.client("iam", region_name=region_name)
    sts_client: STSClient = boto3.client("sts", region_name=region_name)
    events_client: EventsClient = boto3.client("events", region_name=region_name)
    ecs_client: ECSClient = boto3.client("ecs", region_name=region_name)
    apigateway_client: APIGatewayClient = boto3.client("apigateway", region_name=region_name)
    cloudwatch_client: CloudWatchClient = boto3.client("cloudwatch", region_name=region_name)
    cloudwatch_logs_client: CloudWatchClient = boto3.client("logs", region_name=region_name)
    sqs_client: SQSClient = boto3.client("sqs", region_name=region_name)

    # Import service-specific fetchers
    from .apigateway_fetchers import fetch_apigateway_resources
    from .cloudwatch_fetchers import fetch_cloudwatch_resources
    from .data_source_fetchers import fetch_data_source_resources
    from .dynamodb_fetchers import fetch_dynamodb_resources
    from .ec2_fetchers import fetch_ec2_resources
    from .ecs_fetchers import fetch_ecs_resources
    from .events_fetchers import fetch_events_resources
    from .iam_fetchers import fetch_iam_resources
    from .lambda_fetchers import fetch_lambda_resources
    from .rds_fetchers import fetch_rds_resources
    from .s3_fetchers import fetch_s3_resources
    from .sqs_fetchers import fetch_sqs_resources

    # Iterate through each resource defined in the Terraform state
    for resource in state_data.get("resources", []):
        resource_type = resource.get("type", "")
        resource_name = resource.get("name", "")

        # Get all resource instances
        instances = resource.get("instances", [])
        if not instances:
            continue

        # Process all instances, using ARN as the primary identifier
        for idx, instance in enumerate(instances):
            attributes = instance.get("attributes", {})

            # Special case for aws_route_table_association: use association ID as key
            if resource_type == "aws_route_table_association":
                association_id = attributes.get("id")
                if association_id:
                    unique_resource_key = association_id
                else:
                    unique_resource_key = f"{resource_type}.{resource_name}_{idx}"
            # Special keying for aws_iam_role_policy_attachment
            elif resource_type == "aws_iam_role_policy_attachment":
                role = attributes.get("role")
                policy_arn = attributes.get("policy_arn")
                if role and policy_arn:
                    unique_resource_key = f"{role}/{policy_arn}"
                else:
                    unique_resource_key = f"{resource_type}.{resource_name}_{idx}"
            # API Gateway: use explicit key extraction order
            elif (
                resource_type.startswith("aws_api_gateway_rest_api")
                or resource_type.startswith("aws_api_gateway_resource")
                or resource_type.startswith("aws_api_gateway_method")
                or resource_type.startswith("aws_api_gateway_integration")
                or resource_type.startswith("aws_api_gateway_deployment")
                or resource_type.startswith("aws_api_gateway_stage")
            ):
                unique_resource_key = extract_apigateway_key(attributes, resource_type, resource_name, idx)
            else:
                # Try to extract ARN for unique identification
                try:
                    arn = extract_arn_from_attributes(attributes, resource_type)
                    unique_resource_key = arn
                except ValueError:
                    unique_resource_key = f"{resource_type}.{resource_name}_{idx}"

            # Route to appropriate service-specific fetcher
            if resource_type.startswith("aws_instance"):
                live_resources.update(fetch_ec2_resources(ec2_client, unique_resource_key, attributes))
            elif resource_type.startswith("aws_s3_bucket"):
                live_resources.update(fetch_s3_resources(s3_client, unique_resource_key, attributes))
            elif resource_type.startswith("aws_db_instance"):
                live_resources.update(fetch_rds_resources(rds_client, unique_resource_key, attributes))
            elif resource_type.startswith("aws_dynamodb_table"):
                live_resources.update(fetch_dynamodb_resources(dynamodb_client, unique_resource_key, attributes))
            elif resource_type.startswith("aws_lambda_function"):
                live_resources.update(fetch_lambda_resources(lambda_client, unique_resource_key, attributes))
            elif (
                resource_type.startswith("aws_iam_role_policy")
                or resource_type.startswith("aws_iam_role")
                or resource_type.startswith("aws_iam_policy")
                or resource_type.startswith("aws_iam_openid_connect_provider")
                or resource_type.startswith("aws_iam_role_policy_attachment")
            ):
                live_resources.update(fetch_iam_resources(iam_client, unique_resource_key, attributes, resource_type))
            elif resource_type.startswith("aws_cloudwatch_event_rule"):
                event_bus_name = attributes.get("event_bus_name", "")
                if event_bus_name:
                    unique_resource_key = f"{unique_resource_key}_{event_bus_name}"
                live_resources.update(fetch_events_resources(events_client, unique_resource_key, attributes, resource_type))
            elif resource_type.startswith("aws_cloudwatch_event_target"):
                event_bus_name = attributes.get("event_bus_name", "")
                rule_name = attributes.get("rule", "")
                target_arn = attributes.get("arn", "")
                composite_key = f"event_target:{event_bus_name}:{rule_name}:{target_arn}"
                live_resources.update(fetch_events_resources(events_client, composite_key, attributes, resource_type))
            elif resource_type.startswith("aws_cloudwatch_event_bus"):
                live_resources.update(fetch_events_resources(events_client, unique_resource_key, attributes, resource_type))
            elif resource_type.startswith("aws_lambda_permission"):
                function_name = attributes.get("function_name", "")
                statement_id = attributes.get("statement_id", "")
                if function_name.startswith("arn:aws:lambda:"):
                    function_name = function_name.split(":")[-1]
                composite_key = f"lambda_permission:{function_name}:{statement_id}"
                live_resources.update(fetch_lambda_resources(lambda_client, composite_key, attributes, resource_type))
            elif (
                resource_type.startswith("aws_ecs_cluster")
                or resource_type.startswith("aws_ecs_service")
                or resource_type.startswith("aws_ecs_task_definition")
            ):
                live_resources.update(fetch_ecs_resources(ecs_client, unique_resource_key, attributes, resource_type))
            elif (
                resource_type.startswith("aws_vpc")
                or resource_type.startswith("aws_security_group")
                or resource_type.startswith("aws_subnet")
                or resource_type.startswith("aws_internet_gateway")
                or resource_type.startswith("aws_route_table")
                or resource_type.startswith("aws_route_table_association")
            ):
                if resource_type == "aws_route_table_association":
                    print(f"DEBUG: Calling fetch_ec2_resources for {resource_type} with key {unique_resource_key}")
                    print(f"DEBUG: fetch_ec2_resources object: {fetch_ec2_resources}")
                    print(f"DEBUG: fetch_ec2_resources module: {getattr(fetch_ec2_resources, '__module__', 'N/A')}")
                    print(
                        "DEBUG: fetch_ec2_resources file: "
                        + str(getattr(getattr(fetch_ec2_resources, "__code__", None), "co_filename", "N/A"))
                    )
                    result = fetch_ec2_resources(ec2_client, unique_resource_key, attributes, resource_type)
                    after_keys = set(result.keys())
                    print(f"DEBUG: fetch_ec2_resources returned keys for {resource_type}: {after_keys}")
                    live_resources.update(result)
                else:
                    live_resources.update(fetch_ec2_resources(ec2_client, unique_resource_key, attributes, resource_type))
            elif resource_type == "aws_api_gateway_resource":
                print(
                    f"DEBUG: Calling fetch_apigateway_resource for resource_key={unique_resource_key}, "
                    f"attributes={attributes}"
                )
                from .apigateway_fetchers import fetch_apigateway_resource

                result = fetch_apigateway_resource(apigateway_client, unique_resource_key, attributes)
                print(f"DEBUG: fetch_apigateway_resource returned keys: {list(result.keys())}")
                live_resources.update(result)
            elif (
                resource_type.startswith("aws_api_gateway_rest_api")
                or resource_type.startswith("aws_api_gateway_method")
                or resource_type.startswith("aws_api_gateway_integration")
                or resource_type.startswith("aws_api_gateway_deployment")
                or resource_type.startswith("aws_api_gateway_stage")
            ):
                # All other API Gateway resource types are routed here, with key preference: ARN > ID > composite > fallback
                live_resources.update(fetch_apigateway_resources(apigateway_client, unique_resource_key, attributes))
            elif (
                resource_type.startswith("aws_cloudwatch_dashboard")
                or resource_type.startswith("aws_cloudwatch_metric_alarm")
                or resource_type.startswith("aws_cloudwatch_log_group")
            ):
                live_resources.update(
                    fetch_cloudwatch_resources(
                        cloudwatch_client,
                        unique_resource_key,
                        attributes,
                        resource_type,
                        cloudwatch_logs_client,
                    )
                )
            elif resource_type.startswith("aws_region") or resource_type.startswith("aws_caller_identity"):
                live_resources.update(
                    fetch_data_source_resources(
                        sts_client,
                        region_name,
                        unique_resource_key,
                        attributes,
                        resource_type,
                    )
                )
            elif resource_type.startswith("aws_sqs_queue"):
                queue_name = attributes.get("name", "")
                if queue_name:
                    if queue_name.startswith("https://"):
                        queue_name = queue_name.split("/")[-1]
                    unique_resource_key = f"{unique_resource_key}_{queue_name}"
                live_resources.update(fetch_sqs_resources(sqs_client, unique_resource_key, attributes))

    return live_resources
