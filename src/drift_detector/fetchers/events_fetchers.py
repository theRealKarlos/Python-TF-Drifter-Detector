"""
EventBridge Resource Fetchers Module.

This module contains functions for fetching EventBridge-related AWS resources.
"""

from typing import Any, Dict

from ...utils import fetcher_error_handler, setup_logging
from ..types import EventsClient

logger = setup_logging()


@fetcher_error_handler
def fetch_events_resources(
    events_client: EventsClient, resource_key: str, attributes: Dict, resource_type: str
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
    events_client: EventsClient, resource_key: str, attributes: Dict
) -> Dict[str, Any]:
    """
    Fetch EventBridge buses from AWS and map them by ARN for drift comparison.
    Returns a dictionary of ARNs to bus data for all EventBridge buses.
    """
    try:
        response = events_client.list_event_buses()
        live_resources = {}

        for bus in response["EventBuses"]:
            # EventBridge buses have ARNs
            arn = bus.get("Arn")
            if arn:
                live_resources[arn] = bus

        return live_resources
    except Exception as e:
        logger.error(f"Error fetching EventBridge buses: {e}")
        return {}


def _fetch_eventbridge_rules(
    events_client: EventsClient, resource_key: str, attributes: Dict
) -> Dict[str, Any]:
    """
    Fetch EventBridge rules from AWS and map them by ARN for drift comparison.
    Returns a dictionary of ARNs to rule data for all EventBridge rules.
    """
    try:
        live_resources = {}

        # List all event buses and get rules from each
        buses_response = events_client.list_event_buses()
        for bus in buses_response["EventBuses"]:
            bus_name = bus["Name"]
            try:
                rules_response = events_client.list_rules(EventBusName=bus_name)
                for rule in rules_response["Rules"]:
                    arn = rule.get("Arn")
                    if arn:
                        # Extract relevant attributes for comparison
                        rule_data = {
                            "Name": rule.get("Name"),
                            "Arn": arn,
                            "EventPattern": rule.get("EventPattern"),
                            "State": rule.get("State"),
                            "ScheduleExpression": rule.get("ScheduleExpression"),
                            "Description": rule.get("Description"),
                            "RoleArn": rule.get("RoleArn"),
                            "ManagedBy": rule.get("ManagedBy"),
                        }
                        log_msg = (
                            "[EventBridge] Using key for rule: "
                            + str(arn)
                        )
                        logger.debug(log_msg)
                        live_resources[arn] = rule_data
            except Exception as e:
                logger.debug(f"Could not list rules for bus {bus_name}: {e}")
                continue

        return live_resources
    except Exception as e:
        logger.error(f"Error fetching EventBridge rules: {e}")
        return {}


def _fetch_eventbridge_targets(
    events_client: EventsClient, resource_key: str, attributes: Dict
) -> Dict[str, Any]:
    """
    Fetch EventBridge targets from AWS and map them by composite key for drift comparison.
    Returns a dictionary of composite keys to target data for all EventBridge targets.
    """
    try:
        live_resources = {}

        # Get the target ARN, rule name, and event bus name from the state attributes
        target_arn = attributes.get("arn")
        rule_name = attributes.get("rule")
        event_bus_name = attributes.get("event_bus_name")
        composite_key = f"event_target:{event_bus_name}:{rule_name}:{target_arn}"
        # Print debug information for the EventBridge target search, each line under 100 characters
        print(
            f"[EventBridge] (EXTRA) Searching for target ARN: '{target_arn}' "
            f"in rule: '{rule_name}'"
        )
        print(
            f"  Bus: '{event_bus_name}' with composite key: "
            f"'{composite_key}'"
        )
        if not target_arn or not rule_name:
            log_msg = (
                "[EventBridge] No target ARN or rule name found in attributes: "
                + str(list(attributes.keys()))
            )
            logger.debug(log_msg)
            # Print debug information for missing target ARN or rule name, each line under 100 characters
            print(
                "[EventBridge] No target ARN or rule name found "
                "in attributes:"
            )
            print(f"  {list(attributes.keys())}")
            return live_resources

        # If event_bus_name is not provided, search all buses
        buses_to_check = []
        if event_bus_name:
            buses_to_check = [event_bus_name]
        else:
            buses_response = events_client.list_event_buses()
            buses_to_check = [bus["Name"] for bus in buses_response["EventBuses"]]

        for bus_name in buses_to_check:
            try:
                targets_response = events_client.list_targets_by_rule(
                    Rule=rule_name,
                    EventBusName=bus_name
                )
                targets = targets_response["Targets"]
                # Print debug information for the EventBridge rule and targets, each line under 100 characters
                print("Rule:")
                print(rule_name)
                print("Target count:")
                print(len(targets))
                print("Target ARNs:")
                for t in targets:
                    print(t['Arn'])
                for target in targets:
                    logger.debug(f"[EventBridge] (EXTRA) Examining target: {target}")
                    print(
                        f"[EventBridge] (EXTRA) Examining target: "
                        f"{target}"
                    )
                    logger.debug("[EventBridge] (EXTRA) Comparing target Arn:")
                    logger.debug(target.get('Arn'))
                    logger.debug("with expected:")
                    logger.debug(target_arn)
                    print("[EventBridge] (EXTRA) Comparing target Arn:")
                    print(target.get('Arn'))
                    print("with expected:")
                    print(target_arn)
                    if target.get("Arn") == target_arn:
                        logger.debug(
                            "[EventBridge] (EXTRA) Found matching target with ARN:"
                        )
                        logger.debug(target_arn)
                        logger.debug("in rule:")
                        logger.debug(f"{rule_name} (bus: {bus_name})")
                        print(
                            "[EventBridge] (EXTRA) Found matching target with ARN:"
                        )
                        print(target_arn)
                        print("in rule:")
                        print(f"{rule_name} (bus: {bus_name})")
                        # Map target data to match state attributes
                        target_data = {
                            "target_id": target.get("Id"),
                            "arn": target_arn,
                            "input": target.get("Input"),
                            "input_path": target.get("InputPath"),
                            "input_transformer": target.get("InputTransformer"),
                        }
                        log_msg = (
                            "[EventBridge] (EXTRA) Returning target_data for "
                            + str(composite_key)
                            + ": "
                            + str(target_data)
                        )
                        logger.debug(log_msg)
                        print(
                            f"[EventBridge] (EXTRA) Returning target_data "
                            f"for {composite_key}:"
                        )
                        print(f"  {target_data}")
                        live_resources[composite_key] = target_data
                        return live_resources  # Found the target, no need to continue searching
            except Exception as e:
                logger.debug(
                    f"Could not list targets for rule {rule_name} "
                    f"(bus: {bus_name}): {e}"
                )
                # Print debug information for exception in listing targets, each line under 100 characters
                print("Could not list targets for rule:")
                print(rule_name)
                print("bus:")
                print(bus_name)
                print("error:")
                print(e)
                continue
        # Print debug information for missing target in rule, each line under 100 characters
        print(
            "[EventBridge] (EXTRA) Target with ARN not found "
            "in rule:"
        )
        print(target_arn)
        print("in rule:")
        print(rule_name)
        print("buses checked:")
        print(buses_to_check)
        # Defensive: Return a dict with all expected fields set to None for this composite key
        live_resources[composite_key] = {
            "target_id": None,
            "arn": None,
            "input": None,
            "input_path": None,
            "input_transformer": None,
        }
        log_msg = (
            "[EventBridge] (EXTRA) Returning default None target_data for "
            + str(composite_key)
            + ": "
            + str(live_resources[composite_key])
        )
        logger.debug(log_msg)
        # Print debug information for returning default None target_data, each line under 100 characters
        print(
            "[EventBridge] (EXTRA) Returning default None target_data "
            "for composite key:"
        )
        print(composite_key)
        print("data:")
        print(live_resources[composite_key])
        return live_resources
    except Exception as e:
        logger.error(f"Error fetching EventBridge targets: {e}")
        print(f"Error fetching EventBridge targets: {e}")
        return {}
