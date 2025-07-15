"""
IAM Resource Fetchers Module.

This module contains functions for fetching IAM-related AWS resources.
"""

from typing import Dict

from ...utils import fetcher_error_handler, setup_logging
from ..types import IAMClient, LiveResourceData, ResourceAttributes
from .base import extract_arn_from_attributes

logger = setup_logging()


def extract_hybrid_key_from_iam(entity: dict, entity_type: str) -> str:
    """
    Extract the best available key for an IAM entity using hybrid logic.
    1. Try ARN
    2. Try RoleName/UserName/GroupName/PolicyName (ID)
    3. Fallback to 'entity_type.<name>'
    """
    for arn_key in ("Arn", "arn", "ARN"):
        if arn_key in entity and entity[arn_key]:
            return str(entity[arn_key])
    for id_key in ("RoleName", "UserName", "GroupName", "PolicyName", "name", "Name"):
        if id_key in entity and entity[id_key]:
            return str(entity[id_key])
    return f"{entity_type}.unknown"


@fetcher_error_handler
def fetch_iam_resources(
    iam_client: IAMClient, resource_key: str, attributes: dict, resource_type: str = ""
) -> dict:
    """
    Fetch IAM resources from AWS and map them by hybrid key for drift comparison.
    Returns a dictionary of hybrid keys to IAM entity data for all IAM entities.
    """
    print(f"DEBUG: [IAM] fetch_iam_resources called with resource_type={resource_type}, resource_key={resource_key}, attributes={attributes}")
    try:
        live_resources = {}
        # IMPORTANT: Check aws_iam_role_policy_attachment before aws_iam_role_policy to avoid prefix matching bugs.
        if resource_type.startswith("aws_iam_role_policy_attachment"):
            # Handle managed policy attachments
            if not attributes.get("role") and resource_key:
                # Extract role from resource_key (format: role/policy_arn)
                role_from_key = resource_key.split("/")[0]
                attributes = dict(attributes)  # Copy to avoid mutating input
                attributes["role"] = role_from_key
            result = _fetch_iam_role_policy_attachments(
                iam_client, resource_key, attributes
            )
            print(f"DEBUG: [IAM] _fetch_iam_role_policy_attachments returned keys: {list(result.keys())}")
            return result
        elif resource_type.startswith("aws_iam_role_policy"):
            # Handle inline role policies
            return _fetch_iam_role_policies(iam_client, resource_key, attributes)
        elif resource_type.startswith("aws_iam_role"):
            for role in iam_client.list_roles()["Roles"]:
                key = extract_hybrid_key_from_iam(role, "aws_iam_role")
                logger.debug(f"[IAM] Using key for role: {key}")
                live_resources[key] = role
        elif resource_type.startswith("aws_iam_user"):
            for user in iam_client.list_users()["Users"]:
                key = extract_hybrid_key_from_iam(user, "aws_iam_user")
                logger.debug(f"[IAM] Using key for user: {key}")
                live_resources[key] = user
        elif resource_type.startswith("aws_iam_group"):
            for group in iam_client.list_groups()["Groups"]:
                key = extract_hybrid_key_from_iam(group, "aws_iam_group")
                logger.debug(f"[IAM] Using key for group: {key}")
                live_resources[key] = group
        elif resource_type.startswith("aws_iam_policy"):
            for policy in iam_client.list_policies(Scope="Local")["Policies"]:
                key = extract_hybrid_key_from_iam(policy, "aws_iam_policy")
                logger.debug(f"[IAM] Using key for policy: {key}")
                live_resources[key] = policy
        return live_resources
    except Exception as e:
        logger.error(f"[IAM] Error fetching IAM resources: {e}")
        return {}


def _fetch_iam_roles(
    iam_client: IAMClient, resource_key: str, attributes: ResourceAttributes
) -> Dict[str, LiveResourceData]:
    """
    Fetch IAM roles from AWS and map them by ARN for drift comparison.
    Returns a dictionary of ARNs to role data for all IAM roles.
    """
    try:
        response = iam_client.list_roles()
        live_resources = {}

        for role in response["Roles"]:
            arn = role.get("Arn")
            if arn:
                live_resources[arn] = role

        return live_resources
    except Exception as e:
        logger.error(f"Error fetching IAM roles: {e}")
        return {}


def _fetch_iam_policies(
    iam_client: IAMClient, resource_key: str, attributes: ResourceAttributes
) -> Dict[str, LiveResourceData]:
    """
    Fetch IAM policies from AWS and map them by ARN for drift comparison.
    Returns a dictionary of ARNs to policy data for all IAM policies.
    """
    try:
        response = iam_client.list_policies(Scope="Local")
        live_resources = {}

        for policy in response["Policies"]:
            arn = policy.get("Arn")
            if arn:
                live_resources[arn] = policy

        return live_resources
    except Exception as e:
        logger.error(f"Error fetching IAM policies: {e}")
        return {}


@fetcher_error_handler
def _fetch_iam_role_policies(
    iam_client: IAMClient, resource_key: str, attributes: ResourceAttributes
) -> Dict[str, LiveResourceData]:
    """
    Fetch IAM role policies from AWS and map them by hybrid key for drift comparison.
    Returns a dictionary of hybrid keys to role policy data.
    """
    logger.debug(
        f"DEBUG: Entered _fetch_iam_role_policies with "
        f"resource_key={resource_key}, attributes={attributes}"
    )
    try:
        live_resources: Dict[str, LiveResourceData] = {}

        # Extract role name and policy name from attributes
        role_name = attributes.get("role") or attributes.get("name")
        policy_name = attributes.get("name") or attributes.get("policy_name")

        logger.debug(
            f"DEBUG: IAM role policy fetcher - looking for role: {role_name}, "
            f"policy: {policy_name}"
        )

        if not role_name or not policy_name:
            logger.debug(
                f"DEBUG: No role or policy name found in attributes: {attributes}"
            )
            return live_resources

        # Get the role first
        try:
            role_response = iam_client.get_role(RoleName=role_name)
            role = role_response["Role"]
            logger.debug(f"DEBUG: Found role: {role['RoleName']}")
        except iam_client.exceptions.NoSuchEntityException:
            logger.debug(f"DEBUG: Role {role_name} not found")
            return live_resources

        # Get inline policies for the role
        try:
            policies_response = iam_client.list_role_policies(RoleName=role_name)
            logger.debug(
                f"DEBUG: Available policies for role {role_name}: "
                f"{policies_response['PolicyNames']}"
            )

            # Return all inline policies for this role, keyed by role_name:policy_name
            for policy_name in policies_response["PolicyNames"]:
                policy_response = iam_client.get_role_policy(
                    RoleName=role_name, PolicyName=policy_name
                )
                # Use the same key format as state file: role_name:policy_name
                key = f"{role_name}:{policy_name}"
                logger.debug(f"[IAM] Using key for role policy: {key}")
                live_resources[key] = {
                    "role_name": role_name,
                    "policy_name": policy_name,
                    "policy": policy_response["PolicyDocument"],
                }

            logger.debug(
                f"DEBUG: IAM role policy fetcher returning {len(live_resources)} policies"
            )
            return live_resources

        except Exception as e:
            logger.error(f"Error fetching IAM role policies: {e}")
            return live_resources
    except Exception as e:
        logger.error(f"Error fetching IAM role policies: {e}")
        return live_resources


@fetcher_error_handler
def _fetch_iam_role_policy_attachments(
    iam_client: IAMClient, resource_key: str, attributes: ResourceAttributes
) -> Dict[str, LiveResourceData]:
    """
    Fetch IAM role policy attachments from AWS and map them by resource key for drift comparison.
    Returns a dictionary of resource keys to role policy attachment data.
    """
    try:
        live_resources: Dict[str, LiveResourceData] = {}

        # Get the role name
        role_name = attributes.get("role")
        print(f"DEBUG: [IAM] _fetch_iam_role_policy_attachments called with role_name={role_name}, attributes={attributes}")
        if not role_name:
            return live_resources

        # Get attached policies for the role
        try:
            response = iam_client.list_attached_role_policies(RoleName=role_name)
            print(f"DEBUG: [IAM] list_attached_role_policies response for role {role_name}: {response}")

            # For each attached policy, build the key as '{role_name}/{policy_arn}'
            for attached_policy in response.get("AttachedPolicies", []):
                policy_arn = attached_policy.get("PolicyArn")
                key = f"{role_name}/{policy_arn}"
                print(f"DEBUG: [IAM] Fetched live policy attachment key: {key}")
                live_resources[key] = {
                    "role_name": role_name,
                    "policy_arn": policy_arn,
                    "policy_name": attached_policy.get("PolicyName"),
                }
            print(f"DEBUG: [IAM] All fetched live policy attachment keys: {list(live_resources.keys())}")
            return live_resources
        except iam_client.exceptions.NoSuchEntityException:
            return live_resources

    except Exception as e:
        logger.error(f"Error fetching IAM role policy attachments: {e}")
        return {}


@fetcher_error_handler
def _fetch_iam_openid_connect_providers(
    iam_client: IAMClient, resource_key: str, attributes: ResourceAttributes
) -> Dict[str, LiveResourceData]:
    """
    Fetch IAM OpenID Connect providers from AWS and map them by resource key for drift comparison.
    Uses ARN-based matching exclusively as ARNs are always present in Terraform
    state files for AWS managed resources.
    Returns a dictionary of resource keys to provider data.
    """
    try:
        response = iam_client.list_open_id_connect_providers()
        live_resources = {}

        # Use ARN-based matching exclusively
        arn = extract_arn_from_attributes(attributes, "aws_iam_openid_connect_provider")

        provider_list = response.get("OpenIDConnectProviderList", [])
        for provider in provider_list:
            provider_arn_from_aws = provider.get("Arn")
            if provider_arn_from_aws == arn:
                try:
                    provider_response = iam_client.get_open_id_connect_provider(
                        OpenIDConnectProviderArn=provider_arn_from_aws
                    )
                    live_resources[resource_key] = {
                        "arn": provider_arn_from_aws,
                        **provider_response,
                    }
                    return live_resources
                except Exception as e:
                    logger.error(f"Error getting OIDC provider details: {e}")
                    continue

        # If no exact match, return empty dict
        # This ensures we only report drift when there's a real mismatch
        return live_resources
    except Exception as e:
        logger.error(f"Error fetching IAM OpenID Connect providers: {e}")
        return {}
