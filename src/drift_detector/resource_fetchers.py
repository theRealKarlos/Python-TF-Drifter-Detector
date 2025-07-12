"""
AWS Resource Fetchers Module.

This module contains functions for fetching live AWS resources from various AWS services.
Each resource type has its own fetcher function that handles the specific API calls
and data transformation required for that resource type.
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
    events_client = boto3.client("events", region_name=region_name)
    ecs_client = boto3.client("ecs", region_name=region_name)
    apigateway_client = boto3.client("apigateway", region_name=region_name)
    cloudwatch_client = boto3.client("cloudwatch", region_name=region_name)

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

        # Route to appropriate fetcher based on resource type
        if resource_type.startswith("aws_instance"):
            live_resources.update(
                _fetch_ec2_instances(ec2_client, resource_key, attributes)
            )
        elif resource_type.startswith("aws_s3_bucket"):
            live_resources.update(
                _fetch_s3_buckets(s3_client, resource_key, attributes)
            )
        elif resource_type.startswith("aws_db_instance"):
            live_resources.update(
                _fetch_rds_instances(rds_client, resource_key, attributes)
            )
        elif resource_type.startswith("aws_dynamodb_table"):
            live_resources.update(
                _fetch_dynamodb_tables(dynamodb_client, resource_key, attributes)
            )
        elif resource_type.startswith("aws_lambda_function"):
            live_resources.update(
                _fetch_lambda_functions(lambda_client, resource_key, attributes)
            )
        elif resource_type.startswith("aws_iam_role_policy"):
            live_resources.update(
                _fetch_iam_role_policies(iam_client, resource_key, attributes)
            )
        elif resource_type.startswith("aws_iam_role"):
            live_resources.update(
                _fetch_iam_roles(iam_client, resource_key, attributes)
            )
        elif resource_type.startswith("aws_iam_policy"):
            live_resources.update(
                _fetch_iam_policies(iam_client, resource_key, attributes)
            )
        elif resource_type.startswith("aws_iam_openid_connect_provider"):
            live_resources.update(
                _fetch_iam_openid_connect_providers(
                    iam_client, resource_key, attributes
                )
            )
        elif resource_type.startswith("aws_cloudwatch_event_bus"):
            live_resources.update(
                _fetch_eventbridge_buses(events_client, resource_key, attributes)
            )
        elif resource_type.startswith("aws_cloudwatch_event_rule"):
            live_resources.update(
                _fetch_eventbridge_rules(events_client, resource_key, attributes)
            )
        elif resource_type.startswith("aws_ecs_cluster"):
            live_resources.update(
                _fetch_ecs_clusters(ecs_client, resource_key, attributes)
            )
        elif resource_type.startswith("aws_ecs_service"):
            live_resources.update(
                _fetch_ecs_services(ecs_client, resource_key, attributes)
            )
        elif resource_type.startswith("aws_vpc"):
            live_resources.update(_fetch_vpcs(ec2_client, resource_key, attributes))
        elif resource_type.startswith("aws_api_gateway_rest_api"):
            live_resources.update(
                _fetch_api_gateway_apis(apigateway_client, resource_key, attributes)
            )
        elif resource_type.startswith("aws_cloudwatch_dashboard"):
            live_resources.update(
                _fetch_cloudwatch_dashboards(
                    cloudwatch_client, resource_key, attributes
                )
            )
        elif resource_type.startswith("aws_cloudwatch_metric_alarm"):
            live_resources.update(
                _fetch_cloudwatch_alarms(cloudwatch_client, resource_key, attributes)
            )

    return live_resources


def _fetch_ec2_instances(
    ec2_client: Any, resource_key: str, attributes: Dict
) -> Dict[str, Any]:
    """
    Fetch EC2 instances from AWS and map them by resource key for drift comparison.
    Returns a dictionary of resource keys to instance data.
    """
    try:
        response = ec2_client.describe_instances()
        live_resources = {}
        for reservation in response["Reservations"]:
            for instance in reservation["Instances"]:
                # Match by instance ID if available in attributes
                if (
                    attributes.get("id")
                    and instance.get("InstanceId") == attributes["id"]
                ):
                    live_resources[resource_key] = instance
                    return live_resources
        # If no exact match, return first instance (fallback)
        if response["Reservations"]:
            live_resources[resource_key] = response["Reservations"][0]["Instances"][0]
        return live_resources
    except Exception as e:
        print(f"Error fetching EC2 instances: {e}")
        return {}


def _fetch_s3_buckets(
    s3_client: Any, resource_key: str, attributes: Dict
) -> Dict[str, Any]:
    """
    Fetch S3 buckets from AWS and map them by resource key for drift comparison.
    Returns a dictionary of resource keys to bucket data.
    """
    try:
        response = s3_client.list_buckets()
        live_resources = {}
        bucket_name = attributes.get("bucket") or attributes.get("id")

        for bucket in response["Buckets"]:
            if bucket_name and bucket["Name"] == bucket_name:
                live_resources[resource_key] = bucket
                return live_resources

        # If no exact match, return first bucket (fallback)
        if response["Buckets"]:
            live_resources[resource_key] = response["Buckets"][0]
        return live_resources
    except Exception as e:
        print(f"Error fetching S3 buckets: {e}")
        return {}


def _fetch_rds_instances(
    rds_client: Any, resource_key: str, attributes: Dict
) -> Dict[str, Any]:
    """
    Fetch RDS database instances from AWS and map them by resource key for drift comparison.
    Returns a dictionary of resource keys to database instance data.
    """
    try:
        response = rds_client.describe_db_instances()
        live_resources = {}
        db_identifier = attributes.get("db_instance_identifier") or attributes.get("id")

        for db_instance in response["DBInstances"]:
            if db_identifier and db_instance["DBInstanceIdentifier"] == db_identifier:
                live_resources[resource_key] = db_instance
                return live_resources

        # If no exact match, return first instance (fallback)
        if response["DBInstances"]:
            live_resources[resource_key] = response["DBInstances"][0]
        return live_resources
    except Exception as e:
        print(f"Error fetching RDS instances: {e}")
        return {}


def _fetch_dynamodb_tables(
    dynamodb_client: Any, resource_key: str, attributes: Dict
) -> Dict[str, Any]:
    """
    Fetch DynamoDB tables from AWS and map them by resource key for drift comparison.
    Returns a dictionary of resource keys to table data.
    """
    try:
        response = dynamodb_client.list_tables()
        live_resources = {}
        table_name = attributes.get("name") or attributes.get("id")

        for table_name_from_aws in response["TableNames"]:
            if table_name and table_name_from_aws == table_name:
                table_info = dynamodb_client.describe_table(
                    TableName=table_name_from_aws
                )
                live_resources[resource_key] = table_info["Table"]
                return live_resources

        # If no exact match, return first table (fallback)
        if response["TableNames"]:
            table_info = dynamodb_client.describe_table(
                TableName=response["TableNames"][0]
            )
            live_resources[resource_key] = table_info["Table"]
        return live_resources
    except Exception as e:
        print(f"Error fetching DynamoDB tables: {e}")
        return {}


def _fetch_lambda_functions(
    lambda_client: Any, resource_key: str, attributes: Dict
) -> Dict[str, Any]:
    """
    Fetch Lambda functions from AWS and map them by resource key for drift comparison.
    Returns a dictionary of resource keys to function data.
    """
    try:
        response = lambda_client.list_functions()
        live_resources = {}
        function_name = attributes.get("function_name") or attributes.get("id")

        for function in response["Functions"]:
            if function_name and function["FunctionName"] == function_name:
                live_resources[resource_key] = function
                return live_resources

        # If no exact match, return first function (fallback)
        if response["Functions"]:
            live_resources[resource_key] = response["Functions"][0]
        return live_resources
    except Exception as e:
        print(f"Error fetching Lambda functions: {e}")
        return {}


def _fetch_iam_roles(
    iam_client: Any, resource_key: str, attributes: Dict
) -> Dict[str, Any]:
    """
    Fetch IAM roles from AWS and map them by resource key for drift comparison.
    Returns a dictionary of resource keys to role data.
    """
    try:
        response = iam_client.list_roles()
        live_resources = {}
        role_name = attributes.get("name") or attributes.get("id")

        for role in response["Roles"]:
            if role_name and role["RoleName"] == role_name:
                live_resources[resource_key] = role
                return live_resources

        # If no exact match, return first role (fallback)
        if response["Roles"]:
            live_resources[resource_key] = response["Roles"][0]
        return live_resources
    except Exception as e:
        print(f"Error fetching IAM roles: {e}")
        return {}


def _fetch_iam_policies(
    iam_client: Any, resource_key: str, attributes: Dict
) -> Dict[str, Any]:
    """
    Fetch IAM policies from AWS and map them by resource key for drift comparison.
    Returns a dictionary of resource keys to policy data.
    """
    try:
        response = iam_client.list_policies(Scope="Local")
        live_resources = {}
        policy_name = attributes.get("name") or attributes.get("id")

        for policy in response["Policies"]:
            if policy_name and policy["PolicyName"] == policy_name:
                live_resources[resource_key] = policy
                return live_resources

        # If no exact match, return first policy (fallback)
        if response["Policies"]:
            live_resources[resource_key] = response["Policies"][0]
        return live_resources
    except Exception as e:
        print(f"Error fetching IAM policies: {e}")
        return {}


def _fetch_iam_role_policies(
    iam_client: Any, resource_key: str, attributes: Dict
) -> Dict[str, Any]:
    """
    Fetch IAM role policies from AWS and map them by resource key for drift comparison.
    Returns a dictionary of resource keys to role policy data.
    """
    print(
        f"DEBUG: Entered _fetch_iam_role_policies with "
        f"resource_key={resource_key}, attributes={attributes}"
    )
    try:
        role_name = attributes.get("role") or attributes.get("name")
        policy_name = attributes.get("name")

        print(
            f"DEBUG: IAM role policy fetcher - looking for role: {role_name}, policy: {policy_name}"
        )

        if not role_name or not policy_name:
            print(f"DEBUG: No role or policy name found in attributes: {attributes}")
            return {}

        # Get the role first
        try:
            role_response = iam_client.get_role(RoleName=role_name)
            role = role_response["Role"]
            print(f"DEBUG: Found role: {role['RoleName']}")
        except iam_client.exceptions.NoSuchEntityException:
            print(f"DEBUG: Role {role_name} not found")
            return {}

        # Get inline policies for the role
        try:
            policies_response = iam_client.list_role_policies(RoleName=role_name)
            print(
                f"DEBUG: Available policies for role {role_name}: "
                f"{policies_response['PolicyNames']}"
            )
            if policy_name in policies_response["PolicyNames"]:
                policy_response = iam_client.get_role_policy(
                    RoleName=role_name, PolicyName=policy_name
                )
                # Return a structure with the policy document and role name for comparison
                result = {
                    resource_key: {
                        "role_name": role_name,
                        "policy_name": policy_name,
                        "policy": policy_response["PolicyDocument"],
                    }
                }
                print(f"DEBUG: IAM role policy fetcher returning: {result}")
                return result
            else:
                print(f"DEBUG: Policy {policy_name} not found for role {role_name}")
                print("DEBUG: IAM role policy fetcher returning empty dict")
                return {}
        except Exception as e:
            print(f"Error fetching IAM role policies: {e}")
            return {}
    except Exception as e:
        print(f"Error fetching IAM role policies: {e}")
        return {}


def _fetch_iam_openid_connect_providers(
    iam_client: Any, resource_key: str, attributes: Dict
) -> Dict[str, Any]:
    """
    Fetch IAM OpenID Connect providers from AWS and map them by resource key for drift comparison.
    Returns a dictionary of resource keys to provider data.
    """
    try:
        response = iam_client.list_open_id_connect_providers()
        live_resources = {}
        provider_arn = attributes.get("arn") or attributes.get("id")

        # The response structure is 'OpenIDConnectProviderList' with 'Arn' fields
        provider_list = response.get("OpenIDConnectProviderList", [])

        print(
            f"DEBUG: OIDC provider ARNs from AWS: {[p.get('Arn') for p in provider_list]}"
        )
        print(f"DEBUG: Looking for provider ARN: {provider_arn}")

        for provider in provider_list:
            provider_arn_from_aws = provider.get("Arn")
            if provider_arn and provider_arn_from_aws == provider_arn:
                try:
                    provider_response = iam_client.get_open_id_connect_provider(
                        OpenIDConnectProviderArn=provider_arn_from_aws
                    )
                    live_resources[resource_key] = {
                        "arn": provider_arn_from_aws,
                        **provider_response,
                    }
                    return live_resources
                except Exception as e:
                    print(f"Error getting OIDC provider details: {e}")
                    continue

        # If no exact match, return first provider (fallback)
        if provider_list:
            try:
                first_provider_arn = provider_list[0].get("Arn")
                provider_response = iam_client.get_open_id_connect_provider(
                    OpenIDConnectProviderArn=first_provider_arn
                )
                live_resources[resource_key] = {
                    "arn": first_provider_arn,
                    **provider_response,
                }
            except Exception as e:
                print(f"Error getting first OIDC provider details: {e}")
        return live_resources
    except Exception as e:
        print(f"Error fetching IAM OpenID Connect providers: {e}")
        return {}


def _fetch_eventbridge_buses(
    events_client: Any, resource_key: str, attributes: Dict
) -> Dict[str, Any]:
    """
    Fetch EventBridge buses from AWS and map them by resource key for drift comparison.
    Returns a dictionary of resource keys to bus data.
    """
    try:
        response = events_client.list_event_buses()
        live_resources = {}
        bus_name = attributes.get("name") or attributes.get("id")

        for bus in response["EventBuses"]:
            if bus_name and bus["Name"] == bus_name:
                live_resources[resource_key] = bus
                return live_resources

        # If no exact match, return first bus (fallback)
        if response["EventBuses"]:
            live_resources[resource_key] = response["EventBuses"][0]
        return live_resources
    except Exception as e:
        print(f"Error fetching EventBridge buses: {e}")
        return {}


def _fetch_eventbridge_rules(
    events_client: Any, resource_key: str, attributes: Dict
) -> Dict[str, Any]:
    """
    Fetch EventBridge rules from AWS and map them by resource key for drift comparison.
    Returns a dictionary of resource keys to rule data.
    """
    try:
        response = events_client.list_rules()
        live_resources = {}
        rule_name = attributes.get("name") or attributes.get("id")

        for rule in response["Rules"]:
            if rule_name and rule["Name"] == rule_name:
                live_resources[resource_key] = rule
                return live_resources

        # If no exact match, return first rule (fallback)
        if response["Rules"]:
            live_resources[resource_key] = response["Rules"][0]
        return live_resources
    except Exception as e:
        print(f"Error fetching EventBridge rules: {e}")
        return {}


def _fetch_ecs_clusters(
    ecs_client: Any, resource_key: str, attributes: Dict
) -> Dict[str, Any]:
    """
    Fetch ECS clusters from AWS and map them by resource key for drift comparison.
    Returns a dictionary of resource keys to cluster data.
    """
    try:
        response = ecs_client.list_clusters()
        live_resources = {}
        cluster_name = attributes.get("name") or attributes.get("id")

        for cluster_arn in response["clusterArns"]:
            cluster_info = ecs_client.describe_clusters(clusters=[cluster_arn])
            if (
                cluster_name
                and cluster_info["clusters"][0]["clusterName"] == cluster_name
            ):
                live_resources[resource_key] = cluster_info["clusters"][0]
                return live_resources

        # If no exact match, return first cluster (fallback)
        if response["clusterArns"]:
            cluster_info = ecs_client.describe_clusters(
                clusters=[response["clusterArns"][0]]
            )
            live_resources[resource_key] = cluster_info["clusters"][0]
        return live_resources
    except Exception as e:
        print(f"Error fetching ECS clusters: {e}")
        return {}


def _fetch_ecs_services(
    ecs_client: Any, resource_key: str, attributes: Dict
) -> Dict[str, Any]:
    """
    Fetch ECS services from AWS and map them by resource key for drift comparison.
    Returns a dictionary of resource keys to service data.
    """
    try:
        response = ecs_client.list_services()
        live_resources = {}
        service_name = attributes.get("name") or attributes.get("id")

        for service_arn in response["serviceArns"]:
            service_info = ecs_client.describe_services(services=[service_arn])
            if (
                service_name
                and service_info["services"][0]["serviceName"] == service_name
            ):
                live_resources[resource_key] = service_info["services"][0]
                return live_resources

        # If no exact match, return first service (fallback)
        if response["serviceArns"]:
            service_info = ecs_client.describe_services(
                services=[response["serviceArns"][0]]
            )
            live_resources[resource_key] = service_info["services"][0]
        return live_resources
    except Exception as e:
        print(f"Error fetching ECS services: {e}")
        return {}


def _fetch_vpcs(ec2_client: Any, resource_key: str, attributes: Dict) -> Dict[str, Any]:
    """
    Fetch VPCs from AWS and map them by resource key for drift comparison.
    Returns a dictionary of resource keys to VPC data.
    """
    try:
        response = ec2_client.describe_vpcs()
        live_resources = {}
        vpc_id = attributes.get("id")

        for vpc in response["Vpcs"]:
            if vpc_id and vpc["VpcId"] == vpc_id:
                live_resources[resource_key] = vpc
                return live_resources

        # If no exact match, return first VPC (fallback)
        if response["Vpcs"]:
            live_resources[resource_key] = response["Vpcs"][0]
        return live_resources
    except Exception as e:
        print(f"Error fetching VPCs: {e}")
        return {}


def _fetch_api_gateway_apis(
    apigateway_client: Any, resource_key: str, attributes: Dict
) -> Dict[str, Any]:
    """
    Fetch API Gateway REST APIs from AWS and map them by resource key for drift comparison.
    Returns a dictionary of resource keys to API Gateway data.
    """
    try:
        response = apigateway_client.get_rest_apis()
        live_resources = {}
        api_name = attributes.get("name") or attributes.get("id")

        for api in response["items"]:
            if api_name and api["name"] == api_name:
                live_resources[resource_key] = api
                return live_resources

        # If no exact match, return first API (fallback)
        if response["items"]:
            live_resources[resource_key] = response["items"][0]
        return live_resources
    except Exception as e:
        print(f"Error fetching API Gateway REST APIs: {e}")
        return {}


def _fetch_cloudwatch_dashboards(
    cloudwatch_client: Any, resource_key: str, attributes: Dict
) -> Dict[str, Any]:
    """
    Fetch CloudWatch dashboards from AWS and map them by resource key for drift comparison.
    Returns a dictionary of resource keys to dashboard data.
    """
    try:
        response = cloudwatch_client.list_dashboards()
        live_resources = {}
        dashboard_name = attributes.get("name") or attributes.get("id")

        for dashboard in response["DashboardEntries"]:
            if dashboard_name and dashboard["DashboardName"] == dashboard_name:
                live_resources[resource_key] = dashboard
                return live_resources

        # If no exact match, return first dashboard (fallback)
        if response["DashboardEntries"]:
            live_resources[resource_key] = response["DashboardEntries"][0]
        return live_resources
    except Exception as e:
        print(f"Error fetching CloudWatch dashboards: {e}")
        return {}


def _fetch_cloudwatch_alarms(
    cloudwatch_client: Any, resource_key: str, attributes: Dict
) -> Dict[str, Any]:
    """
    Fetch CloudWatch alarms from AWS and map them by resource key for drift comparison.
    Returns a dictionary of resource keys to alarm data.
    """
    try:
        response = cloudwatch_client.describe_alarms()
        live_resources = {}
        alarm_name = attributes.get("name") or attributes.get("id")

        for alarm in response["MetricAlarms"]:
            if alarm_name and alarm["AlarmName"] == alarm_name:
                live_resources[resource_key] = alarm
                return live_resources

        # If no exact match, return first alarm (fallback)
        if response["MetricAlarms"]:
            live_resources[resource_key] = response["MetricAlarms"][0]
        return live_resources
    except Exception as e:
        print(f"Error fetching CloudWatch alarms: {e}")
        return {}
