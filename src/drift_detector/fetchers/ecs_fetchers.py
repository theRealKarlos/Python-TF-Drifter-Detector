"""
ECS Resource Fetchers Module.

This module contains functions for fetching ECS-related AWS resources.
"""

from typing import Any, Dict


def fetch_ecs_resources(
    ecs_client: Any, resource_key: str, attributes: Dict, resource_type: str
) -> Dict[str, Any]:
    """
    Fetch ECS resources from AWS based on resource type.

    Args:
        ecs_client: Boto3 ECS client
        resource_key: Resource key for mapping
        attributes: Resource attributes from Terraform state
        resource_type: Type of ECS resource

    Returns:
        Dictionary mapping resource keys to live AWS resource data
    """
    if resource_type.startswith("aws_ecs_cluster"):
        return _fetch_ecs_clusters(ecs_client, resource_key, attributes)
    elif resource_type.startswith("aws_ecs_service"):
        return _fetch_ecs_services(ecs_client, resource_key, attributes)
    else:
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
