"""
Core drift detection orchestration logic.

This module contains the main entry point for drift detection and coordinates
the overall drift detection process across all supported AWS resource types.
"""

from typing import Any, Dict

from ..utils import download_s3_file, parse_terraform_state
from .comparators import compare_resources
from .fetchers import get_live_aws_resources


def detect_drift(config: Dict) -> Dict[str, Any]:
    """
    Main entry point for drift detection. Orchestrates the entire drift detection process.

    This function:
    - Downloads the Terraform state file from S3 (or reads from local file)
    - Parses the state file to extract resource information
    - Fetches live AWS resources for comparison
    - Compares state with live resources to identify drift
    - Returns a comprehensive drift report

    Args:
        config: Configuration dictionary containing S3 state file path or local file path

    Returns:
        Dictionary containing drift report with detected changes and summary statistics
    """
    try:
        # Step 1: Download and parse Terraform state file from S3 or read from local file
        s3_path = config["s3_state_path"]

        if s3_path.startswith("local://"):
            # Handle local file path
            local_path = s3_path[8:]  # Remove "local://" prefix
            with open(local_path, "r") as f:
                state_content = f.read()
        else:
            # Handle S3 path
            state_content = download_s3_file(s3_path)

        state_data = parse_terraform_state(state_content)

        # Step 2: Fetch live AWS resources for comparison
        region = config.get("aws_region", "eu-west-2")
        live_resources = get_live_aws_resources(state_data, region_name=region)

        # Step 3: Compare state resources with live AWS resources
        drift_report = compare_resources(state_data, live_resources)

        # Exclude meta resources from drift detection and reporting
        META_RESOURCE_TYPES = {"aws_region", "aws_caller_identity"}

        # Step 4: Collect resource counts
        resource_block_count = len(state_data.get("resources", []))
        total_instance_count = 0
        for resource in state_data.get("resources", []):
            total_instance_count += len(resource.get("instances", []))
        print(f"DEBUG: Resource block count (top-level resources): {resource_block_count}")
        print(f"DEBUG: Total resource instances (including meta): {total_instance_count}")

        all_state_resources = set()
        state_resource_key_map = {}  # Map from extracted key to (resource_type, resource_name, instance_index)
        monitoring_attachment_key = (
            "dev-pulsequeue-monitoring-execution-role/arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
        )
        for resource in state_data.get("resources", []):
            resource_type = resource.get("type")
            resource_name = resource.get("name")
            # Print every resource type, name, and attributes before fetcher routing
            print(f"DEBUG: DISPATCH resource_type={resource_type}, resource_name={resource_name}")
            for idx, instance in enumerate(resource.get("instances", [])):
                attributes = instance.get("attributes", {})
                print(f"DEBUG: DISPATCH instance idx={idx}, attributes={attributes}")
                # Print the attributes for aws_api_gateway_resource.this_0 if encountered
                if resource_type == "aws_api_gateway_resource" and resource_name == "this" and attributes.get("id") == "55xlh7":
                    print(f"DEBUG: ATTRIBUTES for aws_api_gateway_resource.this_0: {attributes}")
                # Special key extraction for aws_lambda_permission
                if resource_type == "aws_lambda_permission":
                    function_name = attributes.get("function_name")
                    statement_id = attributes.get("statement_id")
                    if function_name and statement_id:
                        # If function_name is an ARN, extract the last segment
                        if function_name.startswith("arn:aws:lambda:"):
                            function_name = function_name.split(":")[-1]
                        key = f"lambda_permission:{function_name}:{statement_id}"
                    else:
                        key = statement_id or f"{resource_type}.{resource_name}_{idx}"
                # Special key extraction for aws_api_gateway_stage
                elif resource_type == "aws_api_gateway_stage":
                    arn = attributes.get("arn")
                    region = attributes.get("region")
                    rest_api_id = attributes.get("rest_api_id")
                    stage_name = attributes.get("stage_name")
                    if arn:
                        key = arn
                    elif region and rest_api_id and stage_name:
                        key = f"arn:aws:apigateway:{region}::/restapis/{rest_api_id}/stages/{stage_name}"
                    else:
                        key = f"{resource_type}.{resource_name}_{idx}"
                # Special key extraction for aws_api_gateway_integration
                elif resource_type == "aws_api_gateway_integration":
                    rest_api_id = attributes.get("rest_api_id")
                    resource_id = attributes.get("resource_id")
                    http_method = attributes.get("http_method")
                    if rest_api_id and resource_id and http_method:
                        key = f"agi-{rest_api_id}-{resource_id}-{http_method}"
                    else:
                        key = f"{resource_type}.{resource_name}_{idx}"
                # Special key extraction for aws_sqs_queue_policy
                elif resource_type == "aws_sqs_queue_policy":
                    arn = attributes.get("arn")
                    queue_url = attributes.get("queue_url")
                    queue_id = attributes.get("id")
                    key = None
                    if arn:
                        key = arn
                    elif queue_url:
                        # Try to find the corresponding aws_sqs_queue resource in the state and extract its ARN
                        queue_arn = None
                        for res in state_data.get("resources", []):
                            if res.get("type") == "aws_sqs_queue":
                                for inst in res.get("instances", []):
                                    attrs = inst.get("attributes", {})
                                    if (
                                        attrs.get("url") == queue_url
                                        or attrs.get("queue_url") == queue_url
                                        or attrs.get("id") == queue_url
                                    ):
                                        queue_arn = attrs.get("arn") or attrs.get("queue_arn") or attrs.get("QueueArn")
                                        if queue_arn:
                                            break
                                if queue_arn:
                                    break
                        if queue_arn:
                            key = queue_arn
                        else:
                            key = queue_url
                    elif queue_id:
                        key = queue_id
                    else:
                        key = f"{resource_type}.{resource_name}_{idx}"
                # Special key extraction for aws_api_gateway_rest_api
                elif resource_type == "aws_api_gateway_rest_api":
                    arn = attributes.get("arn")
                    region = attributes.get("region")
                    rest_api_id = attributes.get("id") or attributes.get("rest_api_id")
                    if arn:
                        key = arn
                    elif region and rest_api_id:
                        key = f"arn:aws:apigateway:{region}::/restapis/{rest_api_id}"
                    else:
                        key = f"{resource_type}.{resource_name}_{idx}"
                # Special key extraction for aws_route_table
                elif resource_type == "aws_route_table":
                    arn = attributes.get("arn")
                    region = attributes.get("region")
                    account_id = attributes.get("account_id")
                    route_table_id = attributes.get("id")
                    if arn:
                        key = arn
                    elif region and account_id and route_table_id:
                        key = f"arn:aws:ec2:{region}:{account_id}:route-table/{route_table_id}"
                    else:
                        key = route_table_id or f"{resource_type}.{resource_name}_{idx}"
                # Special key extraction for aws_route_table_association
                elif resource_type == "aws_route_table_association":
                    association_id = attributes.get("id")
                    if association_id:
                        key = association_id
                    else:
                        key = f"{resource_type}.{resource_name}_{idx}"
                # Special key extraction for aws_api_gateway_method
                elif resource_type == "aws_api_gateway_method":
                    rest_api_id = attributes.get("rest_api_id")
                    resource_id = attributes.get("resource_id")
                    http_method = attributes.get("http_method")
                    if rest_api_id and resource_id and http_method:
                        key = f"agm-{rest_api_id}-{resource_id}-{http_method}"
                    else:
                        key = f"{resource_type}.{resource_name}_{idx}"
                # Special key extraction for aws_iam_role_policy_attachment
                elif resource_type == "aws_iam_role_policy_attachment":
                    role_name = attributes.get("role") or attributes.get("role_name")
                    policy_arn = attributes.get("policy_arn")
                    if role_name and policy_arn:
                        key = f"{role_name}/{policy_arn}"
                    else:
                        key = f"{resource_type}.{resource_name}_{idx}"
                # Special key extraction for aws_cloudwatch_dashboard (already fixed above)
                elif resource_type == "aws_cloudwatch_dashboard":
                    arn = attributes.get("arn")
                    dashboard_name = attributes.get("dashboard_name") or attributes.get("id")
                    region = attributes.get("region")
                    account_id = attributes.get("account_id")
                    if arn:
                        key = arn
                    elif dashboard_name and region and account_id:
                        key = f"arn:aws:cloudwatch:{region}:{account_id}:dashboard/{dashboard_name}"
                    else:
                        key = dashboard_name or f"{resource_type}.{resource_name}_{idx}"
                else:
                    # Hybrid key extraction: ARN > ID > fallback
                    key = None
                    # 1. Try ARN
                    for arn_key in ("arn", "Arn", "ARN"):
                        if arn_key in attributes and attributes[arn_key]:
                            key = attributes[arn_key]
                            print(f"DEBUG: Using ARN as key for {resource_type}.{resource_name}_{idx}: " f"{key}")
                            break
                    # 2. Try ID (for resources without ARNs)
                    if not key:
                        for id_key in (
                            "id",
                            "Id",
                            "ID",
                            "instance_id",
                            "InstanceId",
                            "resource_id",
                            "ResourceId",
                        ):
                            if id_key in attributes and attributes[id_key]:
                                key = attributes[id_key]
                                print(f"DEBUG: Using ID as key for {resource_type}." f"{resource_name}_{idx}: {key}")
                                break
                    # 3. Fallback to resource_type.resource_name[_idx]
                    if not key:
                        key = f"{resource_type}.{resource_name}_{idx}"
                        print(f"DEBUG: Using fallback key for {resource_type}.{resource_name}_{idx}: " f"{key}")
                all_state_resources.add(key)
                state_resource_key_map[key] = (resource_type, resource_name, idx)
                if resource_type == "aws_iam_role_policy_attachment":
                    print(f"DEBUG: [STATE] aws_iam_role_policy_attachment resource key: {key}, attributes: {attributes}")
                    if not attributes.get("role") and key:
                        role_from_key = key.split("/")[0]
                        # Fix F541: f-string is missing placeholders
                        print("DEBUG: [STATE] Extracted role from resource_key: {}".format(role_from_key))

        all_live_resources = set(live_resources.keys())
        drifted_resources = set(drift["resource_key"].split(" [")[0] for drift in drift_report.get("drifts", []))

        # Debug: Print total number of resources in state
        print(f"DEBUG: Total resources in state: {len(all_state_resources)}")
        sample_keys = list(all_state_resources)[:5]
        print(f"DEBUG: Sample state resource keys (part 1): {sample_keys[:2]}")
        print(f"DEBUG: Sample state resource keys (part 2): {sample_keys[2:]}")
        print(f"DEBUG: Sample live resource keys: {list(all_live_resources)[:5]}")
        print(f"DEBUG: Total live resources: {len(all_live_resources)}")

        # DEBUG: Print all keys for aws_iam_role_policy_attachment
        print("DEBUG: All state resource keys for aws_iam_role_policy_attachment:")
        for k in all_state_resources:
            if k is not None and k.startswith("dev-pulsequeue-monitoring-execution-role/"):
                print(f"  STATE: {k}")
        print("DEBUG: All live resource keys for aws_iam_role_policy_attachment:")
        for k in all_live_resources:
            if k is not None and k.startswith("dev-pulsequeue-monitoring-execution-role/"):
                print(f"  LIVE: {k}")
        # DEBUG: Check if monitoring_execution key is present in both
        print(f"DEBUG: monitoring_execution key in state: {monitoring_attachment_key in all_state_resources}")
        print(f"DEBUG: monitoring_execution key in live: {monitoring_attachment_key in all_live_resources}")

        # Debug: Print all keys for aws_route_table_association in state and live
        print("DEBUG: All state resource keys for aws_route_table_association:")
        for k in all_state_resources:
            if k is not None and (isinstance(k, str) and k.startswith("rtbassoc-")):
                print(f"  STATE: {k}")
        print("DEBUG: All live resource keys for aws_route_table_association:")
        for k in all_live_resources:
            if k is not None and (isinstance(k, str) and k.startswith("rtbassoc-")):
                print(f"  LIVE: {k}")

        matching_resources = []
        for resource_key in all_state_resources & all_live_resources:
            if not isinstance(resource_key, str):
                continue
            if resource_key in drifted_resources:
                continue
            resource_type, resource_name, idx = state_resource_key_map[resource_key]
            live_attributes = live_resources[resource_key]
            # Resource-type-specific extraction of AWS live name
            aws_live_name = None
            if resource_type == "aws_api_gateway_rest_api":
                aws_live_name = live_attributes.get("name")
            elif resource_type == "aws_cloudwatch_dashboard":
                aws_live_name = live_attributes.get("DashboardName")
            elif resource_type == "aws_dynamodb_table":
                aws_live_name = live_attributes.get("TableName")
            elif resource_type == "aws_ecs_cluster":
                aws_live_name = live_attributes.get("clusterName")
            elif resource_type == "aws_ecs_service":
                aws_live_name = live_attributes.get("serviceName")
            elif resource_type == "aws_iam_role":
                aws_live_name = live_attributes.get("RoleName")
            elif resource_type == "aws_iam_role_policy":
                aws_live_name = live_attributes.get("policy_name")
            elif resource_type == "aws_region":
                aws_live_name = live_attributes.get("RegionName")
            elif resource_type == "aws_sqs_queue":
                aws_live_name = live_attributes.get("QueueName")
            elif resource_type == "aws_sqs_queue_policy":
                aws_live_name = live_attributes.get("QueueUrl")
            elif resource_type == "aws_vpc":
                aws_live_name = live_attributes.get("VpcId")
            else:
                for key_name in ("name", "Name", "id", "Id"):
                    if key_name in live_attributes:
                        aws_live_name = live_attributes[key_name]
                        break
            if not aws_live_name:
                print(
                    f"DEBUG: No live name found for {resource_type}.{resource_name}_{idx}, "
                    f"available keys: {list(live_attributes.keys())}"
                )

            # Concise display name logic (British English spelling)
            # 1. If resource_name is not 'this', use it as logical name
            if resource_name and resource_name != "this":
                logical_name = resource_name
            else:
                # 2. If resource_name is 'this', try to extract a more descriptive name
                key_candidates = [
                    aws_live_name,
                    live_attributes.get("function_name"),
                    live_attributes.get("FunctionName"),
                    live_attributes.get("clusterName"),
                    live_attributes.get("serviceName"),
                    live_attributes.get("TableName"),
                    live_attributes.get("RoleName"),
                    live_attributes.get("policy_name"),
                    live_attributes.get("QueueName"),
                    live_attributes.get("id"),
                    live_attributes.get("Id"),
                    live_attributes.get("arn"),
                    live_attributes.get("Arn"),
                ]
                logical_name = next((k for k in key_candidates if k), None)
                if not logical_name:
                    logical_name = f"{resource_type}:{resource_key}"

            # 3. If both logical_name and aws_live_name are present and different, show both
            if logical_name and aws_live_name and logical_name != aws_live_name:
                display_name = f"{logical_name} (AWS: {aws_live_name})"
            else:
                display_name = logical_name or aws_live_name or f"{resource_type}:{resource_key}"

            matching_resources.append(
                {
                    "resource_type": resource_type,
                    "resource_name": resource_name,
                    "aws_live_name": aws_live_name,
                    "display_name": display_name,
                }
            )
        # Debug: Print number of matched and mismatched resources, each line under 100 characters
        print("DEBUG: Matched resources:")
        print(len(matching_resources))
        drifted_or_missing = len(all_state_resources) - len(matching_resources)
        print("DEBUG: Drifted or missing resources:")
        print(drifted_or_missing)
        # Debug: Print unique drifted resource keys and total drift entries
        print("DEBUG: Unique drifted resource keys:", len(drifted_resources))
        print("DEBUG: Total drift entries:", len(drift_report["drifts"]))

        # Step 5: Identify unmatched/unreported resources (in state, not matched, not drifted)
        matched_keys = set([k for k in all_state_resources & all_live_resources if k not in drifted_resources])
        unmatched = all_state_resources - matched_keys - drifted_resources
        print("DEBUG: Unmatched/unreported resources:", unmatched)
        print("DEBUG: Count of unmatched/unreported resources:", len(unmatched))

        # Identify meta resources (excluded from drift detection)
        meta_resources = []  # For reporting: list of dicts
        meta_resource_keys = set()  # For set operations
        for resource in state_data.get("resources", []):
            resource_type = resource.get("type")
            resource_name = resource.get("name")
            if resource_type in META_RESOURCE_TYPES:
                for idx, instance in enumerate(resource.get("instances", [])):
                    attributes = instance.get("attributes", {})
                    # Hybrid key extraction: ARN > ID > fallback
                    value = None
                    key = None
                    for arn_key in ("arn", "Arn", "ARN"):
                        if arn_key in attributes and attributes[arn_key]:
                            value = attributes[arn_key]
                            key = attributes[arn_key]
                            break
                    if not value:
                        for id_key in (
                            "id",
                            "Id",
                            "ID",
                            "instance_id",
                            "InstanceId",
                            "resource_id",
                            "ResourceId",
                        ):
                            if id_key in attributes and attributes[id_key]:
                                value = attributes[id_key]
                                key = attributes[id_key]
                                break
                    if not value:
                        value = "(no id/arn)"
                        key = f"{resource_type}.{resource_name}_{idx}"
                    meta_resources.append(
                        {
                            "resource_type": resource_type,
                            "resource_name": resource_name,
                            "value": value,
                        }
                    )
                    meta_resource_keys.add(key)

        # Unmatched and undetected drift resources: present in state, not matched, not drifted, not meta
        unmatched_undetected = all_state_resources - matched_keys - drifted_resources - meta_resource_keys
        print("DEBUG: Meta resources:", meta_resources)
        print("DEBUG: Count of meta resources:", len(meta_resources))
        print("DEBUG: Unmatched and undetected drift resources:", unmatched_undetected)
        print(
            "DEBUG: Count of unmatched and undetected drift resources:",
            len(unmatched_undetected),
        )

        # Patch: For any unmatched_undetected resource, add a missing_resource drift entry
        for resource_key in unmatched_undetected:
            if isinstance(resource_key, str) and resource_key in state_resource_key_map:
                already_reported = any(drift.get("resource_key") == resource_key for drift in drift_report["drifts"])
                if not already_reported:
                    drift_report["drifts"].append(
                        {
                            "resource_key": resource_key,
                            "drift_type": "missing_resource",
                            "description": f"Resource {resource_key} exists in state but not in live AWS",
                        }
                    )

        # Build unmatched_resources in the same format as matching_resources
        unmatched_resources = []
        for resource_key in unmatched_undetected:
            if isinstance(resource_key, str) and resource_key in state_resource_key_map:
                resource_type, resource_name, idx = state_resource_key_map[resource_key]
                unmatched_resources.append(
                    {
                        "resource_type": resource_type,
                        "resource_name": resource_name,
                        "key": resource_key,
                    }
                )

        # Step 6: Return comprehensive drift report with summary
        return {
            "drift_detected": len(drift_report["drifts"]) > 0,
            "drifts": drift_report["drifts"],
            "summary": {
                "resource_block_count": resource_block_count,
                "total_instance_count": total_instance_count,
                "total_resources": len(all_state_resources),
                "drift_count": len(drifted_resources),
                "timestamp": drift_report["timestamp"],
                "matching_resources": matching_resources,
                "skipped_resources": list(unmatched),
                "meta_resources": meta_resources,
                "unmatched_undetected_resources": unmatched_resources,
                "unmatched_resources": unmatched_resources,
            },
        }

    except Exception as e:
        # Handle any errors during drift detection and return error information
        return {"error": str(e), "drift_detected": False, "drifts": []}
