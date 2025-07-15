"""
Base AWS Resource Comparators Module.

This module contains the main orchestration logic for comparing Terraform state resources
with live AWS resources to identify drift.
"""

from datetime import datetime
from typing import Any, Dict, List

from ...utils import setup_logging
from .apigateway_comparators import compare_apigateway_attributes
from .cloudwatch_comparators import compare_cloudwatch_attributes
from .dynamodb_comparators import compare_dynamodb_attributes

# Import service-specific comparators
from .ec2_comparators import compare_ec2_attributes
from .ecs_comparators import compare_ecs_attributes
from .events_comparators import compare_events_attributes
from .iam_comparators import compare_iam_attributes
from .lambda_comparators import compare_lambda_attributes
from .rds_comparators import compare_rds_attributes
from .s3_comparators import compare_s3_attributes
from .sqs_comparators import compare_sqs_attributes

logger = setup_logging()


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
        base_resource_key = f"{resource_type}.{resource_name}"

        # Special handling for SQS queue policy (already loops over all instances)
        if resource_type.startswith("aws_sqs_queue_policy"):
            import json
            for instance in resource.get("instances", []):
                state_attributes = instance.get("attributes", {})
                queue_url = state_attributes.get("queue_url")
                state_policy_raw = state_attributes.get("policy")
                # Find the matching live policy for this queue_url
                live_policy_raw = None
                for live_key, live_val in live_resources.items():
                    if not isinstance(live_val, dict):
                        continue
                    if live_val.get("QueueUrl") == queue_url:
                        live_policy_raw = live_val.get("Policy")
                        break
                    queue_arn = live_val.get("QueueArn", "")
                    if queue_url and queue_arn.endswith(queue_url.split("/")[-1]):
                        live_policy_raw = live_val.get("Policy")
                        break
                try:
                    state_policy_obj = json.loads(state_policy_raw) if state_policy_raw else None
                    live_policy_obj = json.loads(live_policy_raw) if live_policy_raw else None
                    canonical_state_policy = (
                        json.dumps(state_policy_obj, sort_keys=True, separators=(",", ":"))
                        if state_policy_obj else None
                    )
                    canonical_live_policy = (
                        json.dumps(live_policy_obj, sort_keys=True, separators=(",", ":"))
                        if live_policy_obj else None
                    )
                except Exception as e:
                    print(f"DEBUG: JSON parse error for queue_url={queue_url!r}: {e}")
                    canonical_state_policy = state_policy_raw
                    canonical_live_policy = live_policy_raw
                print(f"DEBUG: SQS policy compare for {resource_type}.{resource_name} [{queue_url}]:\n  State={canonical_state_policy}\n  Live={canonical_live_policy}")
                if canonical_state_policy != canonical_live_policy:
                    resource_identifier = f"{resource_type}.{resource_name} [{queue_url}]"
                    drifts.append({
                        "resource_key": resource_identifier,
                        "drift_type": "attribute_drift",
                        "description": f"Policy drift detected for {resource_identifier}",
                        "differences": [
                            {
                                "name": "policy",
                                "state": canonical_state_policy,
                                "live": canonical_live_policy,
                            }
                        ],
                    })
            continue  # Skip generic block for SQS queue policy resources

        # For all other resource types, process all instances with ARN-based keys
        instances = resource.get("instances", [])
        for idx, instance in enumerate(instances):
            state_attributes = instance.get("attributes", {})
            
            # Create unique resource key for this instance (same logic as fetchers)
            try:
                from ..fetchers.base import extract_arn_from_attributes
                arn = extract_arn_from_attributes(state_attributes, resource_type)
                # Use ARN as the primary key for matching
                unique_resource_key = arn
            except (ValueError, ImportError):
                # If no ARN available, fall back to resource name + index
                unique_resource_key = f"{base_resource_key}_{idx}"

            # Special handling for EventBridge targets: use composite key
            if resource_type.startswith("aws_cloudwatch_event_target"):
                event_bus_name = state_attributes.get("event_bus_name", "")
                rule_name = state_attributes.get("rule", "")
                target_arn = state_attributes.get("arn", "")
                unique_resource_key = f"event_target:{event_bus_name}:{rule_name}:{target_arn}"

            # Special handling for Lambda permissions: use composite key
            if resource_type.startswith("aws_lambda_permission"):
                function_name = state_attributes.get("function_name", "")
                statement_id = state_attributes.get("statement_id", "")
                # Normalise function_name: extract name from ARN if needed
                if function_name.startswith("arn:aws:lambda:"):
                    function_name = function_name.split(":")[-1]
                unique_resource_key = f"lambda_permission:{function_name}:{statement_id}"

            # Special handling for API Gateway deployments: use composite key
            if resource_type.startswith("aws_api_gateway_deployment"):
                rest_api_id = state_attributes.get("rest_api_id", "")
                deployment_id = state_attributes.get("id", "")
                unique_resource_key = f"apigw_deployment:{rest_api_id}:{deployment_id}"

            # Special handling for API Gateway integrations: use composite key
            if resource_type.startswith("aws_api_gateway_integration"):
                rest_api_id = state_attributes.get("rest_api_id", "")
                resource_id = state_attributes.get("resource_id", "")
                http_method = state_attributes.get("http_method", "")
                unique_resource_key = f"apigw_integration:{rest_api_id}:{resource_id}:{http_method}"

            # Special handling for API Gateway methods: use composite key
            if resource_type.startswith("aws_api_gateway_method"):
                rest_api_id = state_attributes.get("rest_api_id", "")
                resource_id = state_attributes.get("resource_id", "")
                http_method = state_attributes.get("http_method", "")
                unique_resource_key = f"apigw_method:{rest_api_id}:{resource_id}:{http_method}"

            # Special handling for API Gateway resources: use composite key
            if resource_type.startswith("aws_api_gateway_resource"):
                rest_api_id = state_attributes.get("rest_api_id", "")
                resource_id = state_attributes.get("resource_id", "")
                unique_resource_key = f"apigw_resource:{rest_api_id}:{resource_id}"

            # Special handling for API Gateway rest APIs: use composite key
            if resource_type.startswith("aws_api_gateway_rest_api"):
                rest_api_id = state_attributes.get("id", "")
                unique_resource_key = f"apigw_rest_api:{rest_api_id}"

            # Special handling for API Gateway stages: use composite key
            if resource_type.startswith("aws_api_gateway_stage"):
                rest_api_id = state_attributes.get("rest_api_id", "")
                stage_name = state_attributes.get("stage_name", "")
                unique_resource_key = f"apigw_stage:{rest_api_id}:{stage_name}"

            # Check if resource exists in live AWS using the same key construction as fetchers
            if unique_resource_key not in live_resources:
                drifts.append(
                    {
                        "resource_key": unique_resource_key,
                        "drift_type": "missing_resource",
                        "description": f"Resource {unique_resource_key} exists in state but not in live AWS",
                    }
                )
                continue

            # Compare attributes for existing resources
            live_attributes = live_resources[unique_resource_key]
            differences = compare_attributes(
                state_attributes, live_attributes, resource_type
            )
            if differences:
                drifts.append(
                    {
                        "resource_key": unique_resource_key,
                        "drift_type": "attribute_drift",
                        "description": f"Attribute drift detected for {unique_resource_key}",
                        "differences": differences,
                    }
                )

    return {
        "drifts": drifts,
        "total_drifts": len(drifts),
        "timestamp": datetime.now().isoformat(),
    }


# E302: Add two blank lines before function definition
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
        drift_details.extend(compare_ec2_attributes(state_attrs, live_attrs))
    elif resource_type.startswith("aws_s3_bucket"):
        drift_details.extend(compare_s3_attributes(state_attrs, live_attrs))
    elif resource_type.startswith("aws_dynamodb_table"):
        drift_details.extend(compare_dynamodb_attributes(state_attrs, live_attrs))
    elif resource_type.startswith("aws_lambda_function"):
        drift_details.extend(compare_lambda_attributes(state_attrs, live_attrs))
    elif resource_type.startswith("aws_iam_role_policy"):
        # Must come before aws_iam_role!
        drift_details.extend(
            compare_iam_attributes(state_attrs, live_attrs, resource_type)
        )
    elif (
        resource_type.startswith("aws_iam_role")
        or resource_type.startswith("aws_iam_policy")
        or resource_type.startswith("aws_iam_openid_connect_provider")
    ):
        drift_details.extend(
            compare_iam_attributes(state_attrs, live_attrs, resource_type)
        )
    elif (
        resource_type.startswith("aws_cloudwatch_event_bus")
        or resource_type.startswith("aws_cloudwatch_event_rule")
        or resource_type.startswith("aws_cloudwatch_event_target")
    ):
        drift_details.extend(
            compare_events_attributes(state_attrs, live_attrs, resource_type)
        )
    elif resource_type.startswith("aws_lambda_permission"):
        drift_details.extend(
            compare_lambda_attributes(state_attrs, live_attrs, resource_type)
        )
    elif resource_type.startswith("aws_ecs_cluster") or resource_type.startswith(
        "aws_ecs_service"
    ):
        drift_details.extend(
            compare_ecs_attributes(state_attrs, live_attrs, resource_type)
        )
    elif resource_type.startswith("aws_vpc"):
        drift_details.extend(compare_ec2_attributes(state_attrs, live_attrs))
    elif resource_type.startswith("aws_api_gateway_rest_api"):
        drift_details.extend(compare_apigateway_attributes(state_attrs, live_attrs))
    elif resource_type.startswith(
        "aws_cloudwatch_dashboard"
    ) or resource_type.startswith("aws_cloudwatch_metric_alarm"):
        drift_details.extend(
            compare_cloudwatch_attributes(state_attrs, live_attrs, resource_type)
        )
    elif resource_type.startswith("aws_db_instance"):
        drift_details.extend(compare_rds_attributes(state_attrs, live_attrs))
    elif resource_type.startswith("aws_sqs_queue"):
        drift_details.extend(compare_sqs_attributes(state_attrs, live_attrs))

    return drift_details
