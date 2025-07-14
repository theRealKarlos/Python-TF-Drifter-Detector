"""
IAM Resource Fetchers Module.

This module contains functions for fetching IAM-related AWS resources.
"""

from typing import Dict

from ...utils import fetcher_error_handler, setup_logging
from ..types import IAMClient, LiveResourceData, ResourceAttributes
from .base import extract_arn_from_attributes

logger = setup_logging()


@fetcher_error_handler
def fetch_iam_resources(
    iam_client: IAMClient,
    resource_key: str,
    attributes: ResourceAttributes,
    resource_type: str,
) -> Dict[str, LiveResourceData]:
    """
    Fetch IAM resources from AWS based on resource type.

    Args:
        iam_client: Boto3 IAM client
        resource_key: Resource key for mapping
        attributes: Resource attributes from Terraform state
        resource_type: Type of IAM resource

    Returns:
        Dictionary mapping resource keys to live AWS resource data
    """
    if resource_type.startswith("aws_iam_role_policy"):
        return _fetch_iam_role_policies(iam_client, resource_key, attributes)
    elif resource_type.startswith("aws_iam_role_policy_attachment"):
        return _fetch_iam_role_policy_attachments(iam_client, resource_key, attributes)
    elif resource_type.startswith("aws_iam_role"):
        return _fetch_iam_roles(iam_client, resource_key, attributes)
    elif resource_type.startswith("aws_iam_policy"):
        return _fetch_iam_policies(iam_client, resource_key, attributes)
    elif resource_type.startswith("aws_iam_openid_connect_provider"):
        return _fetch_iam_openid_connect_providers(iam_client, resource_key, attributes)
    else:
        return {}


def _fetch_iam_roles(
    iam_client: IAMClient, resource_key: str, attributes: ResourceAttributes
) -> Dict[str, LiveResourceData]:
    """
    Fetch IAM roles from AWS and map them by resource key for drift comparison.
    Uses ARN-based matching exclusively as ARNs are always present in Terraform
    state files for AWS managed resources.
    Returns a dictionary of resource keys to role data.
    """
    try:
        response = iam_client.list_roles()
        live_resources = {}
        
        # Use ARN-based matching exclusively
        arn = extract_arn_from_attributes(attributes, "aws_iam_role")
        
        for role in response["Roles"]:
            if role.get("Arn") == arn:
                live_resources[resource_key] = role
                return live_resources

        # If no exact match, return empty dict
        # This ensures we only report drift when there's a real mismatch
        return live_resources
    except Exception as e:
        logger.error(f"Error fetching IAM roles: {e}")
        return {}


def _fetch_iam_policies(
    iam_client: IAMClient, resource_key: str, attributes: ResourceAttributes
) -> Dict[str, LiveResourceData]:
    """
    Fetch IAM policies from AWS and map them by resource key for drift comparison.
    Uses ARN-based matching exclusively as ARNs are always present in Terraform
    state files for AWS managed resources.
    Returns a dictionary of resource keys to policy data.
    """
    try:
        response = iam_client.list_policies(Scope="Local")
        live_resources = {}
        
        # Use ARN-based matching exclusively
        arn = extract_arn_from_attributes(attributes, "aws_iam_policy")
        
        for policy in response["Policies"]:
            if policy.get("Arn") == arn:
                live_resources[resource_key] = policy
                return live_resources

        # If no exact match, return empty dict
        # This ensures we only report drift when there's a real mismatch
        return live_resources
    except Exception as e:
        logger.error(f"Error fetching IAM policies: {e}")
        return {}


@fetcher_error_handler
def _fetch_iam_role_policies(
    iam_client: IAMClient, resource_key: str, attributes: ResourceAttributes
) -> Dict[str, LiveResourceData]:
    """
    Fetch IAM role policies from AWS and map them by resource key for drift
    comparison. Returns a dictionary of resource keys to role policy data.
    """
    logger.debug(
        f"DEBUG: Entered _fetch_iam_role_policies with "
        f"resource_key={resource_key}, attributes={attributes}"
    )
    try:
        role_name = attributes.get("role") or attributes.get("name")
        policy_name = attributes.get("name")

        logger.debug(
            f"DEBUG: IAM role policy fetcher - looking for role: {role_name}, "
            f"policy: {policy_name}"
        )

        if not role_name or not policy_name:
            logger.debug(
                f"DEBUG: No role or policy name found in attributes: {attributes}"
            )
            return {}

        # Get the role first
        try:
            role_response = iam_client.get_role(RoleName=role_name)
            role = role_response["Role"]
            logger.debug(f"DEBUG: Found role: {role['RoleName']}")
        except iam_client.exceptions.NoSuchEntityException:
            logger.debug(f"DEBUG: Role {role_name} not found")
            return {}

        # Get inline policies for the role
        try:
            policies_response = iam_client.list_role_policies(RoleName=role_name)
            logger.debug(
                f"DEBUG: Available policies for role {role_name}: "
                f"{policies_response['PolicyNames']}"
            )
            if policy_name in policies_response["PolicyNames"]:
                policy_response = iam_client.get_role_policy(
                    RoleName=role_name, PolicyName=policy_name
                )
                # Return a structure with the policy document and role name for comparison
                result = {
                    resource_key: {
                        "role_name": role_name,
                        "policy_name": policy_name,
                        "policy": policy_response["PolicyDocument"],
                    }
                }
                logger.debug(f"DEBUG: IAM role policy fetcher returning: {result}")
                return result
            else:
                logger.debug(
                    f"DEBUG: Policy {policy_name} not found for role {role_name}"
                )
                logger.debug("DEBUG: IAM role policy fetcher returning empty dict")
                return {}
        except Exception as e:
            logger.error(f"Error fetching IAM role policies: {e}")
            return {}
    except Exception as e:
        logger.error(f"Error fetching IAM role policies: {e}")
        return {}


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
        
        # Get the role name and policy ARN
        role_name = attributes.get("role")
        policy_arn = attributes.get("policy_arn")
        
        if not role_name or not policy_arn:
            return live_resources
        
        # Get attached policies for the role
        try:
            response = iam_client.list_attached_role_policies(RoleName=role_name)
            
            # Check if the policy is attached
            for attached_policy in response.get("AttachedPolicies", []):
                if attached_policy.get("PolicyArn") == policy_arn:
                    live_resources[resource_key] = {
                        "role_name": role_name,
                        "policy_arn": policy_arn,
                        "policy_name": attached_policy.get("PolicyName"),
                    }
                    return live_resources
            
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
