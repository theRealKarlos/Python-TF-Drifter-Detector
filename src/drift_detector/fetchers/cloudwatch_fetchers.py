"""
CloudWatch Resource Fetchers Module.

This module contains functions for fetching CloudWatch-related AWS resources.
"""

from typing import Dict

from ...utils import fetcher_error_handler, setup_logging
from ..types import CloudWatchClient, LiveResourceData, ResourceAttributes

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
    Fetch CloudWatch dashboards from AWS and map them by both ARN forms (with and without region) for drift comparison.
    This ensures robust matching regardless of which ARN form the state file uses.
    Returns a dictionary of keys (ARN with region, ARN without region, and name) to dashboard data.
    """
    print(f"DEBUG: CloudWatch dashboard fetcher called with resource_key={resource_key}, attributes={attributes}")
    dashboards = {}
    try:
        import boto3

        # Get region and account information
        session = boto3.session.Session()
        region = attributes.get("region")
        if not isinstance(region, str) or not region:
            region = session.region_name
        account_id = attributes.get("account_id")
        if not account_id:
            # Try to get account ID from caller identity
            sts = boto3.client("sts", region_name=region)
            account_id = sts.get_caller_identity()["Account"]
        dashboard_name = attributes.get("dashboard_name") or attributes.get("id")
        if not dashboard_name:
            print("DEBUG: No dashboard name found in attributes, skipping.")
            return {}
        # Construct both ARN forms
        arn_with_region = f"arn:aws:cloudwatch:{region}:{account_id}:dashboard/{dashboard_name}"
        arn_without_region = f"arn:aws:cloudwatch::{account_id}:dashboard/{dashboard_name}"
        dashboard_data = {
            "dashboard_name": dashboard_name,
            "region": region,
            "account_id": account_id,
            "attributes": attributes,
        }
        # Return under both ARN forms
        dashboards[arn_with_region] = dashboard_data
        dashboards[arn_without_region] = dashboard_data
        # Also return under dashboard name for legacy matching
        dashboards[str(dashboard_name)] = dashboard_data  # Ensure key is a string for type safety
        print(f"DEBUG: Returning dashboard under keys: {arn_with_region}, {arn_without_region}, {dashboard_name}")
        return dashboards
    except Exception as e:
        print(f"ERROR: Exception in _fetch_cloudwatch_dashboards: {e}")
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
