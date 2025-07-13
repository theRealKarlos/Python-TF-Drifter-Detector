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
    sts_client = boto3.client("sts", region_name=region_name)
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
            # Create unique key for EventBridge rules using event bus name
            event_bus_name = attributes.get("event_bus_name", "")
            unique_resource_key = f"{resource_key}_{event_bus_name}" if event_bus_name else resource_key
            live_resources.update(
                _fetch_eventbridge_rules(events_client, unique_resource_key, attributes)
            )
        elif resource_type.startswith("aws_cloudwatch_event_target"):
            # Create unique key for EventBridge targets using event bus name
            event_bus_name = attributes.get("event_bus_name", "")
            unique_resource_key = f"{resource_key}_{event_bus_name}" if event_bus_name else resource_key
            live_resources.update(
                _fetch_eventbridge_targets(events_client, unique_resource_key, attributes)
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
        elif resource_type.startswith("aws_region"):
            live_resources.update(
                _fetch_aws_region_data(region_name, resource_key, attributes)
            )
        elif resource_type.startswith("aws_caller_identity"):
            live_resources.update(
                _fetch_aws_caller_identity_data(sts_client, resource_key, attributes)
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
        # If no exact match, return empty dict (no fallback)
        # This ensures we only report drift when there's a real mismatch
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

        # If no exact match, return empty dict (no fallback)
        # This ensures we only report drift when there's a real mismatch
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

        # If no exact match, return empty dict (no fallback)
        # This ensures we only report drift when there's a real mismatch
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

        # If no exact match, return empty dict (no fallback)
        # This ensures we only report drift when there's a real mismatch
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

        # If no exact match, return empty dict (no fallback)
        # This ensures we only report drift when there's a real mismatch
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

        # If no exact match, return empty dict (no fallback)
        # This ensures we only report drift when there's a real mismatch
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

        # If no exact match, return empty dict (no fallback)
        # This ensures we only report drift when there's a real mismatch
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

        # If no exact match, return empty dict (no fallback)
        # This ensures we only report drift when there's a real mismatch
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

        # If no exact match, return empty dict (no fallback)
        # This ensures we only report drift when there's a real mismatch
        return live_resources
    except Exception as e:
        print(f"Error fetching EventBridge buses: {e}")
        return {}


def _fetch_eventbridge_rules(
    events_client: Any, resource_key: str, attributes: Dict
) -> Dict[str, Any]:
    """
    Fetch EventBridge rules from AWS and map them by resource key for drift comparison.
    Only searches the specific event bus given in the Terraform state. If no event_bus_name is present,
    does not search or return any rules. This strictness avoids false positives from fallback logic.
    Returns a dictionary of resource keys to rule data.
    """
    try:
        event_bus_name = attributes.get("event_bus_name")
        if not event_bus_name:
            # No event bus specified in state, do not search (strict, avoids false positives)
            return {}
        response = events_client.list_rules(EventBusName=event_bus_name)
        live_resources = {}
        rule_name = attributes.get("name")

        for rule in response["Rules"]:
            if rule_name and rule["Name"] == rule_name:
                live_resources[resource_key] = rule
                return live_resources

        # No match found, return empty dict (no fallback)
        return live_resources
    except Exception as e:
        print(f"Error fetching EventBridge rules: {e}")
        return {}


def _fetch_eventbridge_targets(
    events_client: Any, resource_key: str, attributes: Dict
) -> Dict[str, Any]:
    """
    Fetch EventBridge targets from AWS and map them by resource key for drift comparison.
    Only searches the specific event bus and rule given in the Terraform state. If no event_bus_name
    or rule name is present, does not search or return any targets. This strictness avoids false positives.
    Returns a dictionary of resource keys to target data.
    """
    try:
        event_bus_name = attributes.get("event_bus_name")
        rule_name = attributes.get("rule")
        target_id = attributes.get("target_id")
        
        print(f"DEBUG: Fetching EventBridge target - event_bus: {event_bus_name}, rule: {rule_name}, target_id: {target_id}")
        
        if not event_bus_name or not rule_name:
            # No event bus or rule specified in state, do not search (strict, avoids false positives)
            print(f"DEBUG: Missing event_bus_name or rule_name, skipping")
            return {}
            
        response = events_client.list_targets_by_rule(
            Rule=rule_name,
            EventBusName=event_bus_name
        )
        live_resources = {}
        
        print(f"DEBUG: Found {len(response['Targets'])} targets in AWS")
        for target in response["Targets"]:
            print(f"DEBUG: Checking target {target['Id']} against {target_id}")
            if target_id and target["Id"] == target_id:
                print(f"DEBUG: Match found! Adding to live_resources")
                live_resources[resource_key] = target
                return live_resources

        print(f"DEBUG: No match found for target_id {target_id}")
        # No match found, return empty dict (no fallback)
        return live_resources
    except Exception as e:
        print(f"Error fetching EventBridge targets: {e}")
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

        # If no exact match, return empty dict (no fallback)
        # This ensures we only report drift when there's a real mismatch
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

        # If no exact match, return empty dict (no fallback)
        # This ensures we only report drift when there's a real mismatch
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

        # If no exact match, return empty dict (no fallback)
        # This ensures we only report drift when there's a real mismatch
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

        # If no exact match, return empty dict (no fallback)
        # This ensures we only report drift when there's a real mismatch
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

        # If no exact match, return empty dict (no fallback)
        # This ensures we only report drift when there's a real mismatch
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

        # If no exact match, return empty dict (no fallback)
        # This ensures we only report drift when there's a real mismatch
        return live_resources
    except Exception as e:
        print(f"Error fetching CloudWatch alarms: {e}")
        return {}


def _fetch_aws_region_data(
    region_name: str, resource_key: str, attributes: Dict
) -> Dict[str, Any]:
    """
    Fetch AWS region data for Terraform data source.

    This handles the aws_region data source which provides information about
    the current AWS region. Since this is a data source, we create a mock
    resource that represents the current region information.

    Returns a dictionary with region information that matches the Terraform data source.
    """
    try:
        # Create a mock resource that represents the current region
        # This matches what Terraform's aws_region data source provides
        region_data = {
            "name": region_name,
            "description": f"Current AWS region: {region_name}",
            "endpoint": f"https://{region_name}.amazonaws.com",
            "id": region_name,
        }
        return {resource_key: region_data}
    except Exception as e:
        print(f"Error creating AWS region data: {e}")
        return {}


def _fetch_aws_caller_identity_data(
    sts_client: Any, resource_key: str, attributes: Dict
) -> Dict[str, Any]:
    """
    Fetch AWS caller identity data for Terraform data source.

    This handles the aws_caller_identity data source which provides information about
    the current AWS account and user/role. Since this is a data source, we create a mock
    resource that represents the current caller identity information.

    Returns a dictionary with caller identity information that matches the Terraform data source.
    """
    try:
        # Get the current caller identity from AWS
        response = sts_client.get_caller_identity()
        # Create a mock resource that represents the current caller identity
        # This matches what Terraform's aws_caller_identity data source provides
        caller_identity_data = {
            "account_id": response["Account"],
            "arn": response["Arn"],
            "user_id": response["UserId"],
            "id": response["Account"],  # Terraform uses account ID as the ID
        }
        return {resource_key: caller_identity_data}
    except Exception as e:
        print(f"Error fetching AWS caller identity data: {e}")
        return {}
