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
        for resource in state_data.get("resources", []):
            resource_type = resource.get("type")
            resource_name = resource.get("name")
            for instance in resource.get("instances", []):
                attributes = instance.get("attributes", {})
                unique_key = f"{resource_type}.{resource_name}"
                all_state_resources.add(unique_key)

        all_live_resources = set(live_resources.keys())
        drifted_resources = set(drift["resource_key"].split(" [")[0] for drift in drift_report.get("drifts", []))

        # Debug: Print total number of resources in state
        print(f"DEBUG: Total resources in state: {len(all_state_resources)}")

        matching_resources = []
        for resource_key in all_state_resources & all_live_resources:
            if resource_key in drifted_resources:
                continue
            resource_type, resource_name = resource_key.split(".", 1)
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
                # Fix: Use 'policy_name' (lowercase) as seen in debug output
                aws_live_name = live_attributes.get("policy_name")
            elif resource_type == "aws_region":
                aws_live_name = live_attributes.get("RegionName")
            elif resource_type == "aws_sqs_queue":
                aws_live_name = live_attributes.get("QueueName")
            elif resource_type == "aws_sqs_queue_policy":
                # Fix: Use 'QueueUrl' as the live name for SQS queue policies
                aws_live_name = live_attributes.get("QueueUrl")
            elif resource_type == "aws_vpc":
                aws_live_name = live_attributes.get("VpcId")
            else:
                # Fallback to common keys
                for key in ("name", "Name", "id", "Id"):
                    if key in live_attributes:
                        aws_live_name = live_attributes[key]
                        break
            # Debug print if no name is found
            if not aws_live_name:
                print(f"DEBUG: No live name found for {resource_type}.{resource_name}, available keys: {list(live_attributes.keys())}")
            matching_resources.append({
                "resource_type": resource_type,
                "resource_name": resource_name,
                "aws_live_name": aws_live_name,
            })
        # Debug: Print number of matched and mismatched resources
        print(f"DEBUG: Matched resources: {len(matching_resources)}")
        print(f"DEBUG: Drifted or missing resources: {len(all_state_resources) - len(matching_resources)}")

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
