"""
AWS Resource Fetchers Module.

This module contains functions for fetching live AWS resources from various AWS services.
Each resource type has its own fetcher function that handles the specific API calls
and data transformation required for that resource type.
"""

from typing import Any, Dict

import boto3


def get_live_aws_resources(state_data: Dict) -> Dict[str, Any]:
    """
    Fetches live AWS resources based on what's found in the Terraform state.

    This function iterates through all resources in the Terraform state and
    fetches corresponding live AWS resources for comparison. It supports
    multiple AWS services and handles API errors gracefully.

    Args:
        state_data: Parsed Terraform state data containing resource definitions

    Returns:
        Dictionary mapping resource keys to live AWS resource data
    """
    live_resources = {}

    # Initialize AWS service clients for all supported services
    # Each client is used to fetch live resources from the respective AWS service
    ec2_client = boto3.client("ec2")
    s3_client = boto3.client("s3")
    rds_client = boto3.client("rds")
    dynamodb_client = boto3.client("dynamodb")
    lambda_client = boto3.client("lambda")
    iam_client = boto3.client("iam")
    events_client = boto3.client("events")
    ecs_client = boto3.client("ecs")
    apigateway_client = boto3.client("apigateway")
    cloudwatch_client = boto3.client("cloudwatch")

    # Iterate through each resource defined in the Terraform state
    for resource in state_data.get("resources", []):
        resource_type = resource.get("type", "")
        resource_name = resource.get("name", "")

        # Route to appropriate fetcher based on resource type
        if resource_type.startswith("aws_instance"):
            live_resources.update(_fetch_ec2_instances(ec2_client, resource_name))
        elif resource_type.startswith("aws_s3_bucket"):
            live_resources.update(_fetch_s3_buckets(s3_client, resource_name))
        elif resource_type.startswith("aws_db_instance"):
            live_resources.update(_fetch_rds_instances(rds_client, resource_name))
        elif resource_type.startswith("aws_dynamodb_table"):
            live_resources.update(
                _fetch_dynamodb_tables(dynamodb_client, resource_name)
            )
        elif resource_type.startswith("aws_lambda_function"):
            live_resources.update(_fetch_lambda_functions(lambda_client, resource_name))
        elif resource_type.startswith("aws_iam_role"):
            live_resources.update(_fetch_iam_roles(iam_client, resource_name))
        elif resource_type.startswith("aws_iam_policy"):
            live_resources.update(_fetch_iam_policies(iam_client, resource_name))
        elif resource_type.startswith("aws_cloudwatch_event_bus"):
            live_resources.update(
                _fetch_eventbridge_buses(events_client, resource_name)
            )
        elif resource_type.startswith("aws_cloudwatch_event_rule"):
            live_resources.update(
                _fetch_eventbridge_rules(events_client, resource_name)
            )
        elif resource_type.startswith("aws_ecs_cluster"):
            live_resources.update(_fetch_ecs_clusters(ecs_client, resource_name))
        elif resource_type.startswith("aws_ecs_service"):
            live_resources.update(_fetch_ecs_services(ecs_client, resource_name))
        elif resource_type.startswith("aws_vpc"):
            live_resources.update(_fetch_vpcs(ec2_client, resource_name))
        elif resource_type.startswith("aws_api_gateway_rest_api"):
            live_resources.update(
                _fetch_api_gateway_apis(apigateway_client, resource_name)
            )
        elif resource_type.startswith("aws_cloudwatch_dashboard"):
            live_resources.update(
                _fetch_cloudwatch_dashboards(cloudwatch_client, resource_name)
            )
        elif resource_type.startswith("aws_cloudwatch_metric_alarm"):
            live_resources.update(
                _fetch_cloudwatch_alarms(cloudwatch_client, resource_name)
            )

    return live_resources


def _fetch_ec2_instances(ec2_client: Any, resource_name: str) -> Dict[str, Any]:
    """Fetch EC2 instances from AWS."""
    try:
        response = ec2_client.describe_instances()
        live_resources = {}
        for reservation in response["Reservations"]:
            for instance in reservation["Instances"]:
                live_resources[f"aws_instance.{resource_name}"] = instance
        return live_resources
    except Exception as e:
        print(f"Error fetching EC2 instances: {e}")
        return {}


def _fetch_s3_buckets(s3_client: Any, resource_name: str) -> Dict[str, Any]:
    """Fetch S3 buckets from AWS."""
    try:
        response = s3_client.list_buckets()
        live_resources = {}
        for bucket in response["Buckets"]:
            live_resources[f"aws_s3_bucket.{resource_name}"] = bucket
        return live_resources
    except Exception as e:
        print(f"Error fetching S3 buckets: {e}")
        return {}


def _fetch_rds_instances(rds_client: Any, resource_name: str) -> Dict[str, Any]:
    """Fetch RDS database instances from AWS."""
    try:
        response = rds_client.describe_db_instances()
        live_resources = {}
        for db_instance in response["DBInstances"]:
            live_resources[f"aws_db_instance.{resource_name}"] = db_instance
        return live_resources
    except Exception as e:
        print(f"Error fetching RDS instances: {e}")
        return {}


def _fetch_dynamodb_tables(dynamodb_client: Any, resource_name: str) -> Dict[str, Any]:
    """Fetch DynamoDB tables from AWS."""
    try:
        response = dynamodb_client.list_tables()
        live_resources = {}
        for table_name in response["TableNames"]:
            table_info = dynamodb_client.describe_table(TableName=table_name)
            live_resources[f"aws_dynamodb_table.{resource_name}"] = table_info["Table"]
        return live_resources
    except Exception as e:
        print(f"Error fetching DynamoDB tables: {e}")
        return {}


def _fetch_lambda_functions(lambda_client: Any, resource_name: str) -> Dict[str, Any]:
    """Fetch Lambda functions from AWS."""
    try:
        response = lambda_client.list_functions()
        live_resources = {}
        for function in response["Functions"]:
            live_resources[f"aws_lambda_function.{resource_name}"] = function
        return live_resources
    except Exception as e:
        print(f"Error fetching Lambda functions: {e}")
        return {}


def _fetch_iam_roles(iam_client: Any, resource_name: str) -> Dict[str, Any]:
    """Fetch IAM roles from AWS."""
    try:
        response = iam_client.list_roles()
        live_resources = {}
        for role in response["Roles"]:
            live_resources[f"aws_iam_role.{resource_name}"] = role
        return live_resources
    except Exception as e:
        print(f"Error fetching IAM roles: {e}")
        return {}


def _fetch_iam_policies(iam_client: Any, resource_name: str) -> Dict[str, Any]:
    """Fetch IAM policies from AWS."""
    try:
        response = iam_client.list_policies(Scope="Local")
        live_resources = {}
        for policy in response["Policies"]:
            live_resources[f"aws_iam_policy.{resource_name}"] = policy
        return live_resources
    except Exception as e:
        print(f"Error fetching IAM policies: {e}")
        return {}


def _fetch_eventbridge_buses(events_client: Any, resource_name: str) -> Dict[str, Any]:
    """Fetch EventBridge buses from AWS."""
    try:
        response = events_client.list_event_buses()
        live_resources = {}
        for bus in response["EventBuses"]:
            live_resources[f"aws_cloudwatch_event_bus.{resource_name}"] = bus
        return live_resources
    except Exception as e:
        print(f"Error fetching EventBridge buses: {e}")
        return {}


def _fetch_eventbridge_rules(events_client: Any, resource_name: str) -> Dict[str, Any]:
    """Fetch EventBridge rules from AWS."""
    try:
        response = events_client.list_rules()
        live_resources = {}
        for rule in response["Rules"]:
            live_resources[f"aws_cloudwatch_event_rule.{resource_name}"] = rule
        return live_resources
    except Exception as e:
        print(f"Error fetching EventBridge rules: {e}")
        return {}


def _fetch_ecs_clusters(ecs_client: Any, resource_name: str) -> Dict[str, Any]:
    """Fetch ECS clusters from AWS."""
    try:
        response = ecs_client.list_clusters()
        live_resources = {}
        for cluster_arn in response["clusterArns"]:
            cluster_info = ecs_client.describe_clusters(clusters=[cluster_arn])
            live_resources[f"aws_ecs_cluster.{resource_name}"] = cluster_info[
                "clusters"
            ][0]
        return live_resources
    except Exception as e:
        print(f"Error fetching ECS clusters: {e}")
        return {}


def _fetch_ecs_services(ecs_client: Any, resource_name: str) -> Dict[str, Any]:
    """Fetch ECS services from AWS."""
    try:
        response = ecs_client.list_services()
        live_resources = {}
        for service_arn in response["serviceArns"]:
            service_info = ecs_client.describe_services(services=[service_arn])
            live_resources[f"aws_ecs_service.{resource_name}"] = service_info[
                "services"
            ][0]
        return live_resources
    except Exception as e:
        print(f"Error fetching ECS services: {e}")
        return {}


def _fetch_vpcs(ec2_client: Any, resource_name: str) -> Dict[str, Any]:
    """Fetch VPCs from AWS."""
    try:
        response = ec2_client.describe_vpcs()
        live_resources = {}
        for vpc in response["Vpcs"]:
            live_resources[f"aws_vpc.{resource_name}"] = vpc
        return live_resources
    except Exception as e:
        print(f"Error fetching VPCs: {e}")
        return {}


def _fetch_api_gateway_apis(
    apigateway_client: Any, resource_name: str
) -> Dict[str, Any]:
    """Fetch API Gateway REST APIs from AWS."""
    try:
        response = apigateway_client.get_rest_apis()
        live_resources = {}
        for api in response["items"]:
            live_resources[f"aws_api_gateway_rest_api.{resource_name}"] = api
        return live_resources
    except Exception as e:
        print(f"Error fetching API Gateway REST APIs: {e}")
        return {}


def _fetch_cloudwatch_dashboards(
    cloudwatch_client: Any, resource_name: str
) -> Dict[str, Any]:
    """Fetch CloudWatch dashboards from AWS."""
    try:
        response = cloudwatch_client.list_dashboards()
        live_resources = {}
        for dashboard in response["DashboardEntries"]:
            live_resources[f"aws_cloudwatch_dashboard.{resource_name}"] = dashboard
        return live_resources
    except Exception as e:
        print(f"Error fetching CloudWatch dashboards: {e}")
        return {}


def _fetch_cloudwatch_alarms(
    cloudwatch_client: Any, resource_name: str
) -> Dict[str, Any]:
    """Fetch CloudWatch alarms from AWS."""
    try:
        response = cloudwatch_client.describe_alarms()
        live_resources = {}
        for alarm in response["MetricAlarms"]:
            live_resources[f"aws_cloudwatch_metric_alarm.{resource_name}"] = alarm
        return live_resources
    except Exception as e:
        print(f"Error fetching CloudWatch alarms: {e}")
        return {}
