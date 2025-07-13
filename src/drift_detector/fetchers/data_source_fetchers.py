"""
Data Source Fetchers Module.

This module contains functions for fetching Terraform data source information.
"""

from typing import Any, Dict


def fetch_data_source_resources(
    sts_client: Any, region_name: str, resource_key: str, attributes: Dict, resource_type: str
) -> Dict[str, Any]:
    """
    Fetch Terraform data source information.
    
    Args:
        sts_client: Boto3 STS client
        region_name: AWS region name
        resource_key: Resource key for mapping
        attributes: Resource attributes from Terraform state
        resource_type: Type of data source
        
    Returns:
        Dictionary mapping resource keys to data source information
    """
    if resource_type.startswith("aws_region"):
        return _fetch_aws_region_data(region_name, resource_key, attributes)
    elif resource_type.startswith("aws_caller_identity"):
        return _fetch_aws_caller_identity_data(sts_client, resource_key, attributes)
    else:
        return {}


def _fetch_aws_region_data(
    region_name: str, resource_key: str, attributes: Dict
) -> Dict[str, Any]:
    """
    Fetch AWS region data for Terraform data source.

    This handles the aws_region data source which provides information about
    the current AWS region. Since this is a data source, we create a mock
    resource that represents the current region information.

    Returns a dictionary with region information that matches the Terraform data source.
    """
    try:
        # Create a mock resource that represents the current region
        # This matches what Terraform's aws_region data source provides
        region_data = {
            "name": region_name,
            "description": f"Current AWS region: {region_name}",
            "endpoint": f"https://{region_name}.amazonaws.com",
            "id": region_name,
        }
        return {resource_key: region_data}
    except Exception as e:
        print(f"Error creating AWS region data: {e}")
        return {}


def _fetch_aws_caller_identity_data(
    sts_client: Any, resource_key: str, attributes: Dict
) -> Dict[str, Any]:
    """
    Fetch AWS caller identity data for Terraform data source.

    This handles the aws_caller_identity data source which provides information about
    the current AWS account and user/role. Since this is a data source, we create a mock
    resource that represents the current caller identity information.

    Returns a dictionary with caller identity information that matches the Terraform data source.
    """
    try:
        # Get the current caller identity from AWS
        response = sts_client.get_caller_identity()
        # Create a mock resource that represents the current caller identity
        # This matches what Terraform's aws_caller_identity data source provides
        caller_identity_data = {
            "account_id": response["Account"],
            "arn": response["Arn"],
            "user_id": response["UserId"],
            "id": response["Account"],  # Terraform uses account ID as the ID
        }
        return {resource_key: caller_identity_data}
    except Exception as e:
        print(f"Error fetching AWS caller identity data: {e}")
        return {} 