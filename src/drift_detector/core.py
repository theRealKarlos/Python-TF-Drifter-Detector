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

        # Step 4: Collect matching resources (present in both state and live, and with no drift)
        # Fix: Count all resource instances in the state file
        total_state_instances = 0
        for resource in state_data.get("resources", []):
            total_state_instances += len(resource.get("instances", []))
        print(f"DEBUG: Total resource instances in state: {total_state_instances}")

        all_state_resources = set()
        state_resource_key_map = (
            {}
        )  # Map from extracted key to (resource_type, resource_name, instance_index)
        for resource in state_data.get("resources", []):
            resource_type = resource.get("type")
            resource_name = resource.get("name")
            for idx, instance in enumerate(resource.get("instances", [])):
                attributes = instance.get("attributes", {})
                # Hybrid key extraction: ARN > ID > fallback
                key = None
                # 1. Try ARN
                for arn_key in ("arn", "Arn", "ARN"):
                    if arn_key in attributes and attributes[arn_key]:
                        key = attributes[arn_key]
                        print(
                            f"DEBUG: Using ARN as key for {resource_type}.{resource_name}_{idx}: "
                            f"{key}"
                        )
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
                            print(
                                f"DEBUG: Using ID as key for {resource_type}."
                                f"{resource_name}_{idx}: {key}"
                            )
                            break
                # 3. Fallback to resource_type.resource_name[_idx]
                if not key:
                    key = f"{resource_type}.{resource_name}_{idx}"
                    print(
                        f"DEBUG: Using fallback key for {resource_type}.{resource_name}_{idx}: "
                        f"{key}"
                    )
                all_state_resources.add(key)
                state_resource_key_map[key] = (resource_type, resource_name, idx)

        all_live_resources = set(live_resources.keys())
        drifted_resources = set(
            drift["resource_key"].split(" [")[0]
            for drift in drift_report.get("drifts", [])
        )

        # Debug: Print total number of resources in state
        print(f"DEBUG: Total resources in state: {len(all_state_resources)}")
        sample_keys = list(all_state_resources)[:5]
        print(f"DEBUG: Sample state resource keys (part 1): {sample_keys[:2]}")
        print(f"DEBUG: Sample state resource keys (part 2): {sample_keys[2:]}")
        print(f"DEBUG: Sample live resource keys: {list(all_live_resources)[:5]}")
        print(f"DEBUG: Total live resources: {len(all_live_resources)}")

        matching_resources = []
        for resource_key in all_state_resources & all_live_resources:
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
                display_name = (
                    logical_name or aws_live_name or f"{resource_type}:{resource_key}"
                )

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

        # Step 5: Return comprehensive drift report with summary
        return {
            "drift_detected": len(drift_report["drifts"]) > 0,
            "drifts": drift_report["drifts"],
            "summary": {
                "total_resources": len(state_data.get("resources", [])),
                "drift_count": len(drift_report["drifts"]),
                "timestamp": drift_report["timestamp"],
                "matching_resources": matching_resources,
            },
        }

    except Exception as e:
        # Handle any errors during drift detection and return error information
        return {"error": str(e), "drift_detected": False, "drifts": []}
