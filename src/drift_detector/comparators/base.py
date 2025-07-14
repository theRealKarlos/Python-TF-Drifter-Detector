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
        resource_key = f"{resource_type}.{resource_name}"

        # Handle EventBridge rules specially - create unique key with event bus name
        if resource_type.startswith("aws_cloudwatch_event_rule"):
            state_attributes = resource.get("instances", [{}])[0].get("attributes", {})
            event_bus_name = state_attributes.get("event_bus_name", "")
            unique_resource_key = (
                f"{resource_key}_{event_bus_name}" if event_bus_name else resource_key
            )
        elif resource_type.startswith("aws_cloudwatch_event_target"):
            state_attributes = resource.get("instances", [{}])[0].get("attributes", {})
            event_bus_name = state_attributes.get("event_bus_name", "")
            unique_resource_key = (
                f"{resource_key}_{event_bus_name}" if event_bus_name else resource_key
            )
        elif resource_type.startswith("aws_lambda_permission"):
            state_attributes = resource.get("instances", [{}])[0].get("attributes", {})
            function_name = state_attributes.get("function_name", "")
            statement_id = state_attributes.get("statement_id", "")
            if function_name.startswith("arn:aws:lambda:"):
                # Extract function name from ARN
                function_name = function_name.split(":")[-1]
            unique_resource_key = resource_key
            if function_name:
                unique_resource_key += f"_{function_name}"
            if statement_id:
                unique_resource_key += f"_{statement_id}"
        elif resource_type.startswith("aws_sqs_queue_policy"):
            # For each SQS queue policy instance, use queue_url as the unique identifier.
            # For each instance, find the matching live resource by queue_url or QueueArn.
            # Extract the policy from both state and live, parse as JSON, canonicalise, and compare.
            # Report drift only for the policy attribute, using aws_sqs_queue_policy.<resource_name>
            # [<queue_url>] as the identifier.
            import json
            for instance in resource.get("instances", []):
                state_attributes = instance.get("attributes", {})
                queue_url = state_attributes.get("queue_url")
                state_policy_raw = state_attributes.get("policy")
                # Parse state policy as JSON and canonicalise
                try:
                    state_policy_obj = json.loads(state_policy_raw) if state_policy_raw else None
                    canonical_state_policy = json.dumps(
                        state_policy_obj, sort_keys=True, separators=(",", ":")
                    ) if state_policy_obj else None
                except Exception:
                    canonical_state_policy = None
                # Find the live resource for this queue by queue_url or QueueArn
                live_policy_raw = None
                for live_key, live_val in live_resources.items():
                    if not isinstance(live_val, dict):
                        continue
                    # Match by queue_url or QueueArn ending
                    if (
                        live_val.get("queue_url") == queue_url
                        or live_val.get("QueueArn", "").endswith(queue_url.split("/")[-1])
                    ):
                        live_policy_raw = (
                            live_val.get("Policy") or live_val.get("policy")
                        )
                        break
                # Parse live policy as JSON and canonicalise
                try:
                    live_policy_obj = json.loads(live_policy_raw) if live_policy_raw else None
                    canonical_live_policy = json.dumps(
                        live_policy_obj, sort_keys=True, separators=(",", ":")
                    ) if live_policy_obj else None
                except Exception:
                    canonical_live_policy = None
                # Compare canonicalised policies; report drift if they differ
                if canonical_state_policy != canonical_live_policy:
                    resource_identifier = (
                        f"{resource_type}.{resource_name} [{queue_url}]"
                    )
                    drifts.append({
                        "resource_key": resource_identifier,
                        "drift_type": "attribute_drift",
                        "description": (
                            f"Policy drift detected for {resource_identifier}"
                        ),
                        "differences": [
                            {
                                "attribute": "policy",
                                "state": (
                                    canonical_state_policy
                                    if canonical_state_policy is not None
                                    else "N/A"
                                ),
                                "live": (
                                    canonical_live_policy
                                    if canonical_live_policy is not None
                                    else "N/A"
                                ),
                            }
                        ],
                    })
            continue
        elif resource_type.startswith("aws_sqs_queue"):
            state_attributes = resource.get("instances", [{}])[0].get("attributes", {})
            queue_name = state_attributes.get("name", "")
            if queue_name.startswith("https://"):
                # Normalise queue name if it's a URL
                queue_name = queue_name.split("/")[-1]
            unique_resource_key = resource_key
            if queue_name:
                unique_resource_key = f"{resource_key}_{queue_name}"
        else:
            unique_resource_key = resource_key

        # Debug output for IAM role policy
        if resource_key == "aws_iam_role_policy.github_actions":
            logger.debug(f"DEBUG: Checking IAM role policy drift for {resource_key}")
            logger.debug(f"DEBUG: Resource type: {resource_type}")
            logger.debug(
                f"DEBUG: State attributes: "
                f"{resource.get('instances', [{}])[0].get('attributes', {})}"
            )
            if unique_resource_key in live_resources:
                logger.debug(
                    f"DEBUG: Live attributes: {live_resources[unique_resource_key]}"
                )
            else:
                logger.debug("DEBUG: Resource not found in live_resources")

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

        # Compare key attributes (customise based on resource type)
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
