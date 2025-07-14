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
    Fetch CloudWatch dashboards from AWS and map them by resource key for drift comparison.
    Uses ARN-based matching exclusively as ARNs are always present in Terraform
    state files for AWS managed resources.
    Returns a dictionary of resource keys to dashboard data.
    """
    try:
        response = cloudwatch_client.list_dashboards()
        live_resources: Dict[str, LiveResourceData] = {}
        
        # Use ARN-based matching exclusively
        arn = extract_arn_from_attributes(attributes, "aws_cloudwatch_dashboard")
        
        for dashboard in response.get("DashboardEntries", []):
            if dashboard.get("DashboardArn") == arn:
                live_resources[resource_key] = dashboard
                return live_resources

        # If no exact match, return empty dict
        # This ensures we only report drift when there's a real mismatch
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
    Fetch CloudWatch metric alarms from AWS and map them by resource key for drift comparison.
    Uses ARN-based matching exclusively as ARNs are always present in Terraform
    state files for AWS managed resources.
    Returns a dictionary of resource keys to alarm data.
    """
    try:
        response = cloudwatch_client.describe_alarms()
        live_resources: Dict[str, LiveResourceData] = {}
        
        # Use ARN-based matching exclusively
        arn = extract_arn_from_attributes(attributes, "aws_cloudwatch_metric_alarm")
        
        for alarm in response.get("MetricAlarms", []):
            if alarm.get("AlarmArn") == arn:
                live_resources[resource_key] = alarm
                return live_resources

        # If no exact match, return empty dict
        # This ensures we only report drift when there's a real mismatch
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
    Fetch CloudWatch log groups from AWS and map them by resource key for drift comparison.
    Uses ARN-based matching exclusively as ARNs are always present in Terraform
    state files for AWS managed resources.
    Returns a dictionary of resource keys to log group data.
    """
    try:
        response = cloudwatch_client.describe_log_groups()
        live_resources: Dict[str, LiveResourceData] = {}
        
        # Use ARN-based matching exclusively
        arn = extract_arn_from_attributes(attributes, "aws_cloudwatch_log_group")
        
        for log_group in response.get("logGroups", []):
            if log_group.get("arn") == arn:
                live_resources[resource_key] = log_group
                return live_resources

        # If no exact match, return empty dict
        # This ensures we only report drift when there's a real mismatch
        return live_resources
    except Exception as e:
        logger.error(f"Error fetching CloudWatch log groups: {e}")
        return {}
