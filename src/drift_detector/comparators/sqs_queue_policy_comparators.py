"""
Comparator for AWS SQS Queue Policy resources.
Compares only the policy document between state and live.
"""
from typing import Any, Dict, List
import logging
import json

def compare_sqs_queue_policy_attributes(state_attrs: Dict[str, Any], live_attrs: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Compare the policy document between Terraform state and live AWS for SQS queue policies.
    Args:
        state_attrs: The attributes from the Terraform state resource.
        live_attrs: The attributes from the live AWS resource.
    Returns:
        A list of drift dictionaries, or an empty list if no drift is detected.
    """
    drifts = []
    state_policy = state_attrs.get("policy")
    live_policy = live_attrs.get("policy")
    # Parse state policy if it's a string
    state_policy_dict = None
    live_policy_dict = None
    try:
        if isinstance(state_policy, str):
            state_policy_dict = json.loads(state_policy)
        elif isinstance(state_policy, dict):
            state_policy_dict = state_policy
    except Exception as e:
        logging.getLogger("drift_detector").warning(f"Could not parse state policy as JSON: {e}")
    if isinstance(live_policy, str):
        try:
            live_policy_dict = json.loads(live_policy)
        except Exception as e:
            logging.getLogger("drift_detector").warning(f"Could not parse live policy as JSON: {e}")
    elif isinstance(live_policy, dict):
        live_policy_dict = live_policy
    print(f"FORCE DEBUG: SQS queue policy compare (dict): state={state_policy_dict!r}, live={live_policy_dict!r}")
    logging.getLogger("drift_detector").debug(f"DEBUG: Comparing SQS queue policy (dict): state={state_policy_dict!r}, live={live_policy_dict!r}")
    if state_policy_dict != live_policy_dict:
        drifts.append({
            "attribute": "policy",
            "state": json.dumps(state_policy_dict, sort_keys=True) if state_policy_dict is not None else "Missing or invalid",
            "live": json.dumps(live_policy_dict, sort_keys=True) if live_policy_dict is not None else "Missing or invalid",
        })
    # DEBUG: Print the drifts being returned
    print(f"DEBUG: compare_sqs_queue_policy_attributes returning drifts: {drifts!r}")
    return drifts 