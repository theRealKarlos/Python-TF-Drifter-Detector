"""
AWS Resource Comparators Module.

This module contains functions for comparing Terraform state resources with live AWS resources.
Each resource type has its own comparator function that handles the specific attribute
comparisons required for that resource type.
"""

import json
from datetime import datetime
from typing import Any, Dict, List


def compare_resources(
    state_data: Dict[str, Any], live_resources: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Compares Terraform state resources with live AWS resources to identify drift.

    This function performs two types of drift detection:
    1. Missing Resources: Resources that exist in state but not in live AWS
    2. Attribute Drift: Resources that exist in both but have different attributes

    Args:
        state_data: Parsed Terraform state data containing resource definitions
        live_resources: Dictionary of live AWS resources fetched from AWS APIs

    Returns:
        Dictionary containing drift information and timestamp
    """
    drifts: List[Dict[str, Any]] = []

    # Iterate through each resource in the Terraform state
    for resource in state_data.get("resources", []):
        resource_type = resource.get("type")
        resource_name = resource.get("name")
        resource_key = f"{resource_type}.{resource_name}"

        # Handle EventBridge rules specially - create unique key with event bus name
        if resource_type.startswith("aws_cloudwatch_event_rule"):
            state_attributes = resource.get("instances", [{}])[0].get("attributes", {})
            event_bus_name = state_attributes.get("event_bus_name", "")
            unique_resource_key = f"{resource_key}_{event_bus_name}" if event_bus_name else resource_key
        elif resource_type.startswith("aws_cloudwatch_event_target"):
            state_attributes = resource.get("instances", [{}])[0].get("attributes", {})
            event_bus_name = state_attributes.get("event_bus_name", "")
            unique_resource_key = f"{resource_key}_{event_bus_name}" if event_bus_name else resource_key
        else:
            unique_resource_key = resource_key

        # Debug output for IAM role policy
        if resource_key == "aws_iam_role_policy.github_actions":
            print(f"DEBUG: Checking IAM role policy drift for {resource_key}")
            print(f"DEBUG: Resource type: {resource_type}")
            print(
                f"DEBUG: State attributes: "
                f"{resource.get('instances', [{}])[0].get('attributes', {})}"
            )
            if unique_resource_key in live_resources:
                print(f"DEBUG: Live attributes: {live_resources[unique_resource_key]}")
            else:
                print("DEBUG: Resource not found in live_resources")

        # Check if resource exists in live AWS
        if unique_resource_key not in live_resources:
            drifts.append(
                {
                    "resource_key": resource_key,
                    "drift_type": "missing_resource",
                    "description": f"Resource {resource_key} exists in state but not in live AWS",
                }
            )
            continue

        # Compare attributes for existing resources
        state_attributes = resource.get("instances", [{}])[0].get("attributes", {})
        live_attributes = live_resources[unique_resource_key]

        # Compare key attributes (customize based on resource type)
        differences = compare_attributes(
            state_attributes, live_attributes, resource_type
        )

        if differences:
            drifts.append(
                {
                    "resource_key": resource_key,
                    "drift_type": "attribute_drift",
                    "description": f"Attribute drift detected for {resource_key}",
                    "differences": differences,
                }
            )

    return {
        "drifts": drifts,
        "total_drifts": len(drifts),
        "timestamp": datetime.now().isoformat(),
    }


def compare_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any], resource_type: str
) -> List[Dict[str, Any]]:
    """
    Compares specific attributes between Terraform state and live AWS resources.

    This function implements resource-specific attribute comparison logic.
    Each resource type has different key attributes that are important for drift detection.
    The comparison focuses on the most critical attributes for each resource type.

    IMPORTANT: More specific resource types (e.g. aws_iam_role_policy) must be checked
    before more general ones (e.g. aws_iam_role), otherwise the wrong comparator may be
    called. This is a common source of subtle bugs.

    Args:
        state_attrs: Attributes from Terraform state resource
        live_attrs: Attributes from live AWS resource
        resource_type: Type of AWS resource being compared

    Returns:
        List of drift details for attributes that don't match
    """
    drift_details = []

    # Route to appropriate comparator based on resource type
    # Order matters: more specific types must come before general ones!
    if resource_type.startswith("aws_instance"):
        drift_details.extend(_compare_ec2_attributes(state_attrs, live_attrs))
    elif resource_type.startswith("aws_s3_bucket"):
        drift_details.extend(_compare_s3_attributes(state_attrs, live_attrs))
    elif resource_type.startswith("aws_dynamodb_table"):
        drift_details.extend(_compare_dynamodb_attributes(state_attrs, live_attrs))
    elif resource_type.startswith("aws_lambda_function"):
        drift_details.extend(_compare_lambda_attributes(state_attrs, live_attrs))
    elif resource_type.startswith("aws_iam_role_policy"):
        # Must come before aws_iam_role!
        drift_details.extend(
            _compare_iam_role_policy_attributes(state_attrs, live_attrs)
        )
    elif resource_type.startswith("aws_iam_role"):
        drift_details.extend(_compare_iam_role_attributes(state_attrs, live_attrs))
    elif resource_type.startswith("aws_iam_policy"):
        drift_details.extend(_compare_iam_policy_attributes(state_attrs, live_attrs))
    elif resource_type.startswith("aws_cloudwatch_event_bus"):
        drift_details.extend(
            _compare_eventbridge_bus_attributes(state_attrs, live_attrs)
        )
    elif resource_type.startswith("aws_cloudwatch_event_rule"):
        drift_details.extend(
            _compare_eventbridge_rule_attributes(state_attrs, live_attrs)
        )
    elif resource_type.startswith("aws_cloudwatch_event_target"):
        drift_details.extend(
            _compare_eventbridge_target_attributes(state_attrs, live_attrs)
        )
    elif resource_type.startswith("aws_ecs_cluster"):
        drift_details.extend(_compare_ecs_cluster_attributes(state_attrs, live_attrs))
    elif resource_type.startswith("aws_ecs_service"):
        drift_details.extend(_compare_ecs_service_attributes(state_attrs, live_attrs))
    elif resource_type.startswith("aws_vpc"):
        drift_details.extend(_compare_vpc_attributes(state_attrs, live_attrs))
    elif resource_type.startswith("aws_api_gateway_rest_api"):
        drift_details.extend(_compare_api_gateway_attributes(state_attrs, live_attrs))
    elif resource_type.startswith("aws_cloudwatch_dashboard"):
        drift_details.extend(
            _compare_cloudwatch_dashboard_attributes(state_attrs, live_attrs)
        )
    elif resource_type.startswith("aws_cloudwatch_metric_alarm"):
        drift_details.extend(
            _compare_cloudwatch_alarm_attributes(state_attrs, live_attrs)
        )
    return drift_details


def _compare_ec2_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Compare EC2 instance attributes between Terraform state and live AWS.
    Returns a list of drift details for any mismatched attributes.
    """
    drift_details: List[Dict[str, Any]] = []
    state_instance_type = state_attrs.get("instance_type")
    live_instance_type = live_attrs.get("InstanceType")
    if state_instance_type != live_instance_type:
        drift_details.append(
            {
                "attribute": "instance_type",
                "state_value": str(state_instance_type),
                "live_value": str(live_instance_type),
            }
        )
    return drift_details


def _compare_s3_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Compare S3 bucket attributes between Terraform state and live AWS.
    Returns a list of drift details for any mismatched attributes.
    """
    drift_details = []
    state_bucket_name = state_attrs.get("bucket")
    live_bucket_name = live_attrs.get("Name")
    if state_bucket_name != live_bucket_name:
        drift_details.append(
            {
                "attribute": "bucket_name",
                "state_value": str(state_bucket_name),
                "live_value": str(live_bucket_name),
            }
        )
    return drift_details


def _compare_dynamodb_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Compare DynamoDB table attributes between Terraform state and live AWS.
    Returns a list of drift details for any mismatched attributes.
    """
    drift_details = []
    state_table_name = state_attrs.get("name")
    live_table_name = live_attrs.get("TableName")
    if state_table_name != live_table_name:
        drift_details.append(
            {
                "attribute": "table_name",
                "state_value": str(state_table_name),
                "live_value": str(live_table_name),
            }
        )
    return drift_details


def _compare_lambda_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Compare Lambda function attributes between Terraform state and live AWS.
    Returns a list of drift details for any mismatched attributes.
    """
    drift_details = []
    state_function_name = state_attrs.get("function_name")
    live_function_name = live_attrs.get("FunctionName")
    if state_function_name != live_function_name:
        drift_details.append(
            {
                "attribute": "function_name",
                "state_value": str(state_function_name),
                "live_value": str(live_function_name),
            }
        )
    return drift_details


def _compare_iam_role_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any]
) -> List[Dict[str, Any]]:
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


def _compare_iam_role_policy_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any]
) -> List[Dict[str, Any]]:
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
    # Compare policy document (normalized comparison)
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


def _compare_iam_policy_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any]
) -> List[Dict[str, Any]]:
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


def _compare_eventbridge_bus_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Compare EventBridge bus attributes between Terraform state and live AWS.
    Returns a list of drift details for any mismatched attributes.
    """
    drift_details = []
    state_bus_name = state_attrs.get("name")
    live_bus_name = live_attrs.get("Name")
    if state_bus_name != live_bus_name:
        drift_details.append(
            {
                "attribute": "bus_name",
                "state_value": str(state_bus_name),
                "live_value": str(live_bus_name),
            }
        )
    return drift_details


def _compare_eventbridge_rule_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Compare EventBridge rule attributes between Terraform state and live AWS.
    Returns a list of drift details for any mismatched attributes.
    """
    drift_details = []
    state_rule_name = state_attrs.get("name")
    live_rule_name = live_attrs.get("Name")
    if state_rule_name != live_rule_name:
        drift_details.append(
            {
                "attribute": "rule_name",
                "state_value": str(state_rule_name),
                "live_value": str(live_rule_name),
            }
        )
    return drift_details


def _compare_eventbridge_target_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Compare EventBridge target attributes between Terraform state and live AWS.
    Returns a list of drift details for any mismatched attributes.
    """
    drift_details = []
    state_target_id = state_attrs.get("target_id")
    live_target_id = live_attrs.get("Id")
    if state_target_id != live_target_id:
        drift_details.append(
            {
                "attribute": "target_id",
                "state_value": str(state_target_id),
                "live_value": str(live_target_id),
            }
        )
    
    state_arn = state_attrs.get("arn")
    live_arn = live_attrs.get("Arn")
    if state_arn != live_arn:
        drift_details.append(
            {
                "attribute": "arn",
                "state_value": str(state_arn),
                "live_value": str(live_arn),
            }
        )
    return drift_details


def _compare_ecs_cluster_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Compare ECS cluster attributes between Terraform state and live AWS.
    Returns a list of drift details for any mismatched attributes.
    """
    drift_details = []
    state_cluster_name = state_attrs.get("name")
    live_cluster_name = live_attrs.get("clusterName")
    if state_cluster_name != live_cluster_name:
        drift_details.append(
            {
                "attribute": "cluster_name",
                "state_value": str(state_cluster_name),
                "live_value": str(live_cluster_name),
            }
        )
    return drift_details


def _compare_ecs_service_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Compare ECS service attributes between Terraform state and live AWS.
    Returns a list of drift details for any mismatched attributes.
    """
    drift_details = []
    state_service_name = state_attrs.get("name")
    live_service_name = live_attrs.get("serviceName")
    if state_service_name != live_service_name:
        drift_details.append(
            {
                "attribute": "service_name",
                "state_value": str(state_service_name),
                "live_value": str(live_service_name),
            }
        )
    return drift_details


def _compare_vpc_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Compare VPC attributes between Terraform state and live AWS.
    Returns a list of drift details for any mismatched attributes.
    """
    drift_details = []
    state_vpc_id = state_attrs.get("id")
    live_vpc_id = live_attrs.get("VpcId")
    if state_vpc_id != live_vpc_id:
        drift_details.append(
            {
                "attribute": "vpc_id",
                "state_value": str(state_vpc_id),
                "live_value": str(live_vpc_id),
            }
        )
    return drift_details


def _compare_api_gateway_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Compare API Gateway REST API attributes between Terraform state and live AWS.
    Returns a list of drift details for any mismatched attributes.
    """
    drift_details = []
    state_api_name = state_attrs.get("name")
    live_api_name = live_attrs.get("name")
    if state_api_name != live_api_name:
        drift_details.append(
            {
                "attribute": "api_name",
                "state_value": str(state_api_name),
                "live_value": str(live_api_name),
            }
        )
    return drift_details


def _compare_cloudwatch_dashboard_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Compare CloudWatch dashboard attributes between Terraform state and live AWS.
    Returns a list of drift details for any mismatched attributes.
    """
    drift_details = []
    state_dashboard_name = state_attrs.get("dashboard_name")
    live_dashboard_name = live_attrs.get("DashboardName")
    if state_dashboard_name != live_dashboard_name:
        drift_details.append(
            {
                "attribute": "dashboard_name",
                "state_value": str(state_dashboard_name),
                "live_value": str(live_dashboard_name),
            }
        )
    return drift_details


def _compare_cloudwatch_alarm_attributes(
    state_attrs: Dict[str, Any], live_attrs: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Compare CloudWatch alarm attributes between Terraform state and live AWS.
    Returns a list of drift details for any mismatched attributes.
    """
    drift_details = []
    state_alarm_name = state_attrs.get("alarm_name")
    live_alarm_name = live_attrs.get("AlarmName")
    if state_alarm_name != live_alarm_name:
        drift_details.append(
            {
                "attribute": "alarm_name",
                "state_value": str(state_alarm_name),
                "live_value": str(live_alarm_name),
            }
        )
    return drift_details
