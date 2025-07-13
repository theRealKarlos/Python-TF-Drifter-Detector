"""
CloudWatch Resource Fetchers Module.

This module contains functions for fetching CloudWatch-related AWS resources.
"""

from typing import Any, Dict


def fetch_cloudwatch_resources(
    cloudwatch_client: Any, resource_key: str, attributes: Dict, resource_type: str
) -> Dict[str, Any]:
    """
    Fetch CloudWatch resources from AWS based on resource type.
    
    Args:
        cloudwatch_client: Boto3 CloudWatch client
        resource_key: Resource key for mapping
        attributes: Resource attributes from Terraform state
        resource_type: Type of CloudWatch resource
        
    Returns:
        Dictionary mapping resource keys to live AWS resource data
    """
    if resource_type.startswith("aws_cloudwatch_dashboard"):
        return _fetch_cloudwatch_dashboards(cloudwatch_client, resource_key, attributes)
    elif resource_type.startswith("aws_cloudwatch_metric_alarm"):
        return _fetch_cloudwatch_alarms(cloudwatch_client, resource_key, attributes)
    else:
        return {}


def _fetch_cloudwatch_dashboards(
    cloudwatch_client: Any, resource_key: str, attributes: Dict
) -> Dict[str, Any]:
    """
    Fetch CloudWatch dashboards from AWS and map them by resource key for drift comparison.
    Returns a dictionary of resource keys to dashboard data.
    """
    try:
        response = cloudwatch_client.list_dashboards()
        live_resources = {}
        dashboard_name = attributes.get("name") or attributes.get("id")

        for dashboard in response["DashboardEntries"]:
            if dashboard_name and dashboard["DashboardName"] == dashboard_name:
                live_resources[resource_key] = dashboard
                return live_resources

        # If no exact match, return empty dict (no fallback)
        # This ensures we only report drift when there's a real mismatch
        return live_resources
    except Exception as e:
        print(f"Error fetching CloudWatch dashboards: {e}")
        return {}


def _fetch_cloudwatch_alarms(
    cloudwatch_client: Any, resource_key: str, attributes: Dict
) -> Dict[str, Any]:
    """
    Fetch CloudWatch alarms from AWS and map them by resource key for drift comparison.
    Returns a dictionary of resource keys to alarm data.
    """
    try:
        response = cloudwatch_client.describe_alarms()
        live_resources = {}
        alarm_name = attributes.get("name") or attributes.get("id")

        for alarm in response["MetricAlarms"]:
            if alarm_name and alarm["AlarmName"] == alarm_name:
                live_resources[resource_key] = alarm
                return live_resources

        # If no exact match, return empty dict (no fallback)
        # This ensures we only report drift when there's a real mismatch
        return live_resources
    except Exception as e:
        print(f"Error fetching CloudWatch alarms: {e}")
        return {} 