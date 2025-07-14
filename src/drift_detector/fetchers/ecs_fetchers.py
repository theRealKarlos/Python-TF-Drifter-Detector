"""
ECS Resource Fetchers Module.

This module contains functions for fetching ECS-related AWS resources.
"""

from typing import Dict, cast

from ...utils import fetcher_error_handler, setup_logging
from ..types import ECSClient, LiveResourceData, ResourceAttributes
from .base import extract_arn_from_attributes

logger = setup_logging()


@fetcher_error_handler
def fetch_ecs_resources(
    ecs_client: ECSClient,
    resource_key: str,
    attributes: ResourceAttributes,
    resource_type: str,
) -> Dict[str, LiveResourceData]:
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
    elif resource_type.startswith("aws_ecs_task_definition"):
        return _fetch_ecs_task_definitions(ecs_client, resource_key, attributes)
    else:
        return {}


def _fetch_ecs_clusters(
    ecs_client: ECSClient,
    resource_key: str,
    attributes: ResourceAttributes,
) -> Dict[str, LiveResourceData]:
    """
    Fetch ECS clusters from AWS and map them by resource key for drift comparison.
    Uses ARN-based matching exclusively as ARNs are always present in Terraform
    state files for AWS managed resources.
    Returns a dictionary of resource keys to cluster data.
    """
    try:
        response = ecs_client.list_clusters()
        live_resources: Dict[str, LiveResourceData] = {}
        
        # Use ARN-based matching exclusively
        arn = extract_arn_from_attributes(attributes, "aws_ecs_cluster")
        
        for cluster_arn in response.get("clusterArns", []):
            if cluster_arn == arn:
                cluster_info = ecs_client.describe_clusters(clusters=[cluster_arn])
                if cluster_info.get("clusters"):
                    live_resources[resource_key] = cluster_info["clusters"][0]
                    return live_resources

        # If no exact match, return empty dict
        # This ensures we only report drift when there's a real mismatch
        return live_resources
    except Exception as e:
        logger.error(f"Error fetching ECS clusters: {e}")
        return {}


def _fetch_ecs_services(
    ecs_client: ECSClient,
    resource_key: str,
    attributes: ResourceAttributes,
) -> Dict[str, LiveResourceData]:
    """
    Fetch ECS services from AWS and map them by resource key for drift comparison.
    Uses ARN-based matching exclusively as ARNs are always present in Terraform
    state files for AWS managed resources.
    Returns a dictionary of resource keys to service data.
    """
    try:
        live_resources: Dict[str, LiveResourceData] = {}
        
        # Determine the cluster name/ARN from attributes
        cluster = (
            attributes.get("cluster")
            or attributes.get("cluster_arn")
        )
        
        if not cluster:
            return live_resources
        
        # Get services for the cluster
        response = ecs_client.list_services(cluster=cluster)
        
        # Use ARN-based matching exclusively
        arn = extract_arn_from_attributes(attributes, "aws_ecs_service")
        
        for service_arn in response.get("serviceArns", []):
            if service_arn == arn:
                service_info = ecs_client.describe_services(
                    cluster=cluster, services=[service_arn]
                )
                if service_info.get("services"):
                    live_resources[resource_key] = service_info["services"][0]
                    return live_resources

        # If no exact match, return empty dict
        # This ensures we only report drift when there's a real mismatch
        return live_resources
    except Exception as e:
        logger.error(f"Error fetching ECS services: {e}")
        return {}


def _fetch_ecs_task_definitions(
    ecs_client: ECSClient,
    resource_key: str,
    attributes: ResourceAttributes,
) -> Dict[str, LiveResourceData]:
    """
    Fetch ECS task definitions from AWS and map them by resource key for drift comparison.
    Uses ARN-based matching exclusively as ARNs are always present in Terraform
    state files for AWS managed resources.
    Returns a dictionary of resource keys to task definition data.
    """
    try:
        live_resources: Dict[str, LiveResourceData] = {}
        
        # Use ARN-based matching exclusively
        arn = extract_arn_from_attributes(attributes, "aws_ecs_task_definition")
        
        # Extract task definition family and revision from ARN
        # ARN format: arn:aws:ecs:region:account:task-definition/family:revision
        if "task-definition/" in arn:
            task_def_part = arn.split("task-definition/")[-1]
            if ":" in task_def_part:
                family, revision = task_def_part.split(":", 1)
                try:
                    response = ecs_client.describe_task_definition(
                        taskDefinition=f"{family}:{revision}"
                    )
                    live_resources[resource_key] = response.get("taskDefinition", {})
                    return live_resources
                except ecs_client.exceptions.ClientError:
                    pass

        # If no exact match, return empty dict
        # This ensures we only report drift when there's a real mismatch
        return live_resources
    except Exception as e:
        logger.error(f"Error fetching ECS task definitions: {e}")
        return {}
