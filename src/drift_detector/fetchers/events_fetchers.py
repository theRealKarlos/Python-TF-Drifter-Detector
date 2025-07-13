"""
EventBridge Resource Fetchers Module.

This module contains functions for fetching EventBridge-related AWS resources.
"""

from typing import Any, Dict


def fetch_events_resources(
    events_client: Any, resource_key: str, attributes: Dict, resource_type: str
) -> Dict[str, Any]:
    """
    Fetch EventBridge resources from AWS based on resource type.

    Args:
        events_client: Boto3 Events client
        resource_key: Resource key for mapping
        attributes: Resource attributes from Terraform state
        resource_type: Type of EventBridge resource

    Returns:
        Dictionary mapping resource keys to live AWS resource data
    """
    if resource_type.startswith("aws_cloudwatch_event_bus"):
        return _fetch_eventbridge_buses(events_client, resource_key, attributes)
    elif resource_type.startswith("aws_cloudwatch_event_rule"):
        return _fetch_eventbridge_rules(events_client, resource_key, attributes)
    elif resource_type.startswith("aws_cloudwatch_event_target"):
        return _fetch_eventbridge_targets(events_client, resource_key, attributes)
    else:
        return {}


def _fetch_eventbridge_buses(
    events_client: Any, resource_key: str, attributes: Dict
) -> Dict[str, Any]:
    """
    Fetch EventBridge buses from AWS and map them by resource key for drift comparison.
    Returns a dictionary of resource keys to bus data.
    """
    try:
        response = events_client.list_event_buses()
        live_resources = {}
        bus_name = attributes.get("name") or attributes.get("id")

        for bus in response["EventBuses"]:
            if bus_name and bus["Name"] == bus_name:
                live_resources[resource_key] = bus
                return live_resources

        # If no exact match, return empty dict (no fallback)
        # This ensures we only report drift when there's a real mismatch
        return live_resources
    except Exception as e:
        print(f"Error fetching EventBridge buses: {e}")
        return {}


def _fetch_eventbridge_rules(
    events_client: Any, resource_key: str, attributes: Dict
) -> Dict[str, Any]:
    """
    Fetch EventBridge rules from AWS and map them by resource key for drift comparison.
    Only searches the specific event bus given in the Terraform state. If no
    event_bus_name is present, does not search or return any rules. This strictness
    avoids false positives from fallback logic.
    Returns a dictionary of resource keys to rule data.
    """
    try:
        event_bus_name = attributes.get("event_bus_name")
        if not event_bus_name:
            # No event bus specified in state, do not search (strict, avoids false positives)
            return {}
        response = events_client.list_rules(EventBusName=event_bus_name)
        live_resources = {}
        rule_name = attributes.get("name")

        for rule in response["Rules"]:
            if rule_name and rule["Name"] == rule_name:
                live_resources[resource_key] = rule
                return live_resources

        # No match found, return empty dict (no fallback)
        return live_resources
    except Exception as e:
        print(f"Error fetching EventBridge rules: {e}")
        return {}


def _fetch_eventbridge_targets(
    events_client: Any, resource_key: str, attributes: Dict
) -> Dict[str, Any]:
    """
    Fetch EventBridge targets from AWS and map them by resource key for drift comparison.
    Only searches the specific event bus and rule given in the Terraform state. If no
    event_bus_name or rule name is present, does not search or return any targets.
    This strictness avoids false positives.
    Returns a dictionary of resource keys to target data.
    """
    try:
        event_bus_name = attributes.get("event_bus_name")
        rule_name = attributes.get("rule")
        target_id = attributes.get("target_id")

        print(
            f"DEBUG: Fetching EventBridge target - event_bus: {event_bus_name}, "
            f"rule: {rule_name}, target_id: {target_id}"
        )

        if not event_bus_name or not rule_name:
            # No event bus or rule specified in state, do not search (strict, avoids false
            # positives)
            print("DEBUG: Missing event_bus_name or rule_name, skipping")
            return {}

        response = events_client.list_targets_by_rule(
            Rule=rule_name, EventBusName=event_bus_name
        )
        live_resources = {}

        print(f"DEBUG: Found {len(response['Targets'])} targets in AWS")
        for target in response["Targets"]:
            print(f"DEBUG: Checking target {target['Id']} against {target_id}")
            if target_id and target["Id"] == target_id:
                print("DEBUG: Match found! Adding to live_resources")
                live_resources[resource_key] = target
                return live_resources

        print(f"DEBUG: No match found for target_id {target_id}")
        # No match found, return empty dict (no fallback)
        return live_resources
    except Exception as e:
        print(f"Error fetching EventBridge targets: {e}")
        return {}
