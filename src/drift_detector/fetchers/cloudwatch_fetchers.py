"""
CloudWatch Resource Fetchers Module.

This module contains functions for fetching CloudWatch-related AWS resources.
"""

from typing import Dict

from ...utils import fetcher_error_handler, setup_logging
from ..types import CloudWatchClient, LiveResourceData, ResourceAttributes
from .base import extract_arn_from_attributes

logger = setup_logging()


@fetcher_error_handler
def fetch_cloudwatch_resources(
    cloudwatch_client: CloudWatchClient,
    resource_key: str,
    attributes: ResourceAttributes,
    resource_type: str,
    cloudwatch_logs_client: CloudWatchClient = None,
) -> Dict[str, LiveResourceData]:
    """
    Fetch CloudWatch resources from AWS based on resource type.

    Args:
        cloudwatch_client: Boto3 CloudWatch client
        resource_key: Resource key for mapping
        attributes: Resource attributes from Terraform state
        resource_type: Type of CloudWatch resource
        cloudwatch_logs_client: Boto3 CloudWatch Logs client (optional)

    Returns:
        Dictionary mapping resource keys to live AWS resource data
    """
    if resource_type.startswith("aws_cloudwatch_dashboard"):
        return _fetch_cloudwatch_dashboards(cloudwatch_client, resource_key, attributes)
    elif resource_type.startswith("aws_cloudwatch_metric_alarm"):
        return _fetch_cloudwatch_metric_alarms(cloudwatch_client, resource_key, attributes)
    elif resource_type.startswith("aws_cloudwatch_log_group"):
        if cloudwatch_logs_client:
            return _fetch_cloudwatch_log_groups(cloudwatch_logs_client, resource_key, attributes)
        else:
            logger.error("CloudWatch Logs client not provided for log group fetching")
            return {}
    else:
        return {}


def _fetch_cloudwatch_dashboards(
    cloudwatch_client: CloudWatchClient,
    resource_key: str,
    attributes: ResourceAttributes,
) -> Dict[str, LiveResourceData]:
    """
    Fetch CloudWatch dashboards from AWS and map them by ARN for drift comparison.
    Returns a dictionary of ARNs to dashboard data for all CloudWatch dashboards.
    """
    try:
        response = cloudwatch_client.list_dashboards()
        live_resources: Dict[str, LiveResourceData] = {}
        
        for dashboard in response.get("DashboardEntries", []):
            arn = dashboard.get("DashboardArn")
            if arn:
                live_resources[arn] = dashboard

        return live_resources
    except Exception as e:
        logger.error(f"Error fetching CloudWatch dashboards: {e}")
        return {}


def _fetch_cloudwatch_metric_alarms(
    cloudwatch_client: CloudWatchClient,
    resource_key: str,
    attributes: ResourceAttributes,
) -> Dict[str, LiveResourceData]:
    """
    Fetch CloudWatch metric alarms from AWS and map them by ARN for drift comparison.
    Returns a dictionary of ARNs to alarm data for all CloudWatch metric alarms.
    """
    try:
        response = cloudwatch_client.describe_alarms()
        live_resources: Dict[str, LiveResourceData] = {}
        
        for alarm in response.get("MetricAlarms", []):
            arn = alarm.get("AlarmArn")
            if arn:
                live_resources[arn] = alarm

        return live_resources
    except Exception as e:
        logger.error(f"Error fetching CloudWatch metric alarms: {e}")
        return {}


def _fetch_cloudwatch_log_groups(
    cloudwatch_client: CloudWatchClient,
    resource_key: str,
    attributes: ResourceAttributes,
) -> Dict[str, LiveResourceData]:
    """
    Fetch CloudWatch log groups from AWS and map them by ARN for drift comparison.
    Returns a dictionary of ARNs to log group data for all CloudWatch log groups.
    """
    try:
        response = cloudwatch_client.describe_log_groups()
        live_resources: Dict[str, LiveResourceData] = {}
        
        for log_group in response.get("logGroups", []):
            arn = log_group.get("arn")
            if arn:
                live_resources[arn] = log_group

        return live_resources
    except Exception as e:
        logger.error(f"Error fetching CloudWatch log groups: {e}")
        return {}
