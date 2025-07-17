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
    Fetch CloudWatch dashboards from AWS and map them by both ARN and dashboard name for drift comparison.
    This ensures robust matching regardless of which key the state file uses.
    Returns a dictionary of keys (ARN and name) to dashboard data.
    """
    print(f"DEBUG: CloudWatch dashboard fetcher called with resource_key={resource_key}, attributes={attributes}")
    try:
        import boto3
        # Get region and account information for ARN construction
        region = getattr(cloudwatch_client.meta, "region_name", "unknown")
        try:
            sts = boto3.client("sts", region_name=region)
            account_id = sts.get_caller_identity().get("Account", "unknown")
        except Exception as e:
            account_id = f"error: {e}"
            logger.debug(f"Could not get account ID: {e}")
        response = cloudwatch_client.list_dashboards()
        live_resources: Dict[str, LiveResourceData] = {}
        # Extract the dashboard name from attributes
        target_dashboard_name = attributes.get("dashboard_name") or attributes.get("id")
        if not target_dashboard_name:
            logger.warning(f"No dashboard name found in attributes for {resource_key}")
            return live_resources
        logger.debug(f"Looking for CloudWatch dashboard: {target_dashboard_name}")
        # Construct the ARN for the dashboard key
        dashboard_arn = f"arn:aws:cloudwatch:{region}:{account_id}:dashboard/{target_dashboard_name}"
        print(f"DEBUG: Will use dashboard ARN as key: {dashboard_arn} and dashboard name as key: {target_dashboard_name}")
        # Find the matching dashboard and return it keyed by both ARN and name
        for dashboard in response.get("DashboardEntries", []):
            dashboard_name = dashboard.get("DashboardName")
            if dashboard_name == target_dashboard_name:
                # Key by ARN
                live_resources[dashboard_arn] = dashboard
                logger.debug(f"Successfully matched dashboard {dashboard_name} with ARN key {dashboard_arn}")
                print(f"DEBUG: CloudWatch dashboard matched with ARN key={dashboard_arn}")
                # Also key by dashboard name
                live_resources[dashboard_name] = dashboard
                logger.debug(f"Also returning dashboard {dashboard_name} with name key {dashboard_name}")
                print(f"DEBUG: CloudWatch dashboard also matched with name key={dashboard_name}")
                return live_resources
        logger.debug(f"Dashboard {target_dashboard_name} not found in AWS response")
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
