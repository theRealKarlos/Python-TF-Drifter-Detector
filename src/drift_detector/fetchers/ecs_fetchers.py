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
    Fetch ECS clusters from AWS and map them by ARN for drift comparison.
    Returns a dictionary of ARNs to cluster data for all ECS clusters.
    """
    try:
        response = ecs_client.list_clusters()
        live_resources: Dict[str, LiveResourceData] = {}
        
        for cluster_arn in response.get("clusterArns", []):
            cluster_info = ecs_client.describe_clusters(clusters=[cluster_arn])
            if cluster_info.get("clusters"):
                live_resources[cluster_arn] = cluster_info["clusters"][0]

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
    Fetch ECS services from AWS and map them by ARN for drift comparison.
    Returns a dictionary of ARNs to service data for all ECS services.
    """
    try:
        live_resources: Dict[str, LiveResourceData] = {}
        
        # Get all clusters first
        clusters_response = ecs_client.list_clusters()
        
        for cluster_arn in clusters_response.get("clusterArns", []):
            try:
                # Get services for this cluster
                services_response = ecs_client.list_services(cluster=cluster_arn)
                
                for service_arn in services_response.get("serviceArns", []):
                    service_info = ecs_client.describe_services(
                        cluster=cluster_arn, services=[service_arn]
                    )
                    if service_info.get("services"):
                        live_resources[service_arn] = service_info["services"][0]
            except Exception as e:
                logger.debug(f"Could not get services for cluster {cluster_arn}: {e}")
                continue

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
    Fetch ECS task definitions from AWS and map them by ARN for drift comparison.
    Returns a dictionary of ARNs to task definition data for all ECS task definitions.
    """
    try:
        live_resources: Dict[str, LiveResourceData] = {}
        
        # List all task definition families
        families_response = ecs_client.list_task_definition_families()
        
        for family in families_response.get("families", []):
            try:
                # List all revisions for this family
                revisions_response = ecs_client.list_task_definitions(familyPrefix=family)
                
                for task_def_arn in revisions_response.get("taskDefinitionArns", []):
                    try:
                        response = ecs_client.describe_task_definition(taskDefinition=task_def_arn)
                        if response.get("taskDefinition"):
                            live_resources[task_def_arn] = response["taskDefinition"]
                    except Exception as e:
                        logger.debug(f"Could not describe task definition {task_def_arn}: {e}")
                        continue
            except Exception as e:
                logger.debug(f"Could not list task definitions for family {family}: {e}")
                continue

        return live_resources
    except Exception as e:
        logger.error(f"Error fetching ECS task definitions: {e}")
        return {}
