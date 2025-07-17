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
    Fetch CloudWatch dashboards from AWS and map them by consistent key for drift comparison.
    Constructs keys that match the format used in core.py for consistent resource matching.
    Returns a dictionary of keys to dashboard data.
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

        # Extract the dashboard name we're looking for from attributes
        target_dashboard_name = attributes.get("dashboard_name") or attributes.get("id")

        if not target_dashboard_name:
            logger.warning(f"No dashboard name found in attributes for {resource_key}")
            return live_resources

        logger.debug(f"Looking for CloudWatch dashboard: {target_dashboard_name}")

        # Replicate core.py logic to determine what key format it used
        # Check the same conditions as core.py to determine the key format
        state_arn = attributes.get("arn")  # Note: looking for "arn", not "dashboard_arn"
        state_account_id = attributes.get("account_id")
        
        print(f"DEBUG: CloudWatch dashboard state_arn={state_arn}, state_account_id={state_account_id}")
        print(f"DEBUG: CloudWatch dashboard region={region}, dashboard_name={target_dashboard_name}")

        # Find the matching dashboard and construct proper key using same logic as core.py
        for dashboard in response.get("DashboardEntries", []):
            dashboard_name = dashboard.get("DashboardName")
            if dashboard_name == target_dashboard_name:
                # Use the same logic as core.py to determine the key
                if state_arn:
                    # Core.py would use ARN
                    key = state_arn
                    logger.debug(f"Using state ARN as key (matching core.py logic): {key}")
                elif target_dashboard_name and region != "unknown" and state_account_id:
                    # Core.py would construct ARN
                    key = f"arn:aws:cloudwatch:{region}:{state_account_id}:dashboard/{target_dashboard_name}"
                    logger.debug(f"Using constructed ARN key (matching core.py logic): {key}")
                else:
                    # Core.py would fall back to dashboard name
                    key = target_dashboard_name
                    logger.debug(f"Using dashboard name as key (matching core.py fallback): {key}")
                
                live_resources[key] = dashboard
                logger.debug(f"Successfully matched dashboard {dashboard_name} with key {key}")
                print(f"DEBUG: CloudWatch dashboard matched with key={key}")
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
