"""
Utility functions for Terraform Drift Detector Lambda.
"""

import json
import logging
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import boto3


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Sets up logging configuration for the Lambda function.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("drift_detector")
    logger.setLevel(getattr(logging, log_level.upper()))

    # Prevent duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def download_s3_file(s3_path: str, logger: Optional[logging.Logger] = None) -> str:
    """
    Downloads a file from S3 and returns its content as a string.

    Args:
        s3_path: S3 path in format 's3://bucket/key'
        logger: Logger instance for error logging

    Returns:
        File content as string

    Raises:
        ValueError: If S3 path is invalid
        Exception: If S3 download fails
    """
    if logger is None:
        logger = setup_logging()

    try:
        parsed = urlparse(s3_path)
        bucket = parsed.netloc
        key = parsed.path.lstrip("/")

        if not bucket or not key:
            raise ValueError(f"Invalid S3 path: {s3_path}")

        logger.info(f"Downloading S3 file: {s3_path}")
        s3_client = boto3.client("s3")
        response = s3_client.get_object(Bucket=bucket, Key=key)
        content_bytes = response["Body"].read()
        content = (
            content_bytes.decode("utf-8")
            if isinstance(content_bytes, bytes)
            else str(content_bytes)
        )
        logger.info(f"Successfully downloaded {len(content)} bytes from S3")
        return content

    except Exception as e:
        logger.error(f"Failed to download S3 file {s3_path}: {str(e)}")
        raise


def parse_terraform_state(
    state_content: str, logger: Optional[logging.Logger] = None
) -> Dict[str, Any]:
    """
    Parses Terraform state file content into a Python dict.

    Args:
        state_content: Raw state file content as string
        logger: Logger instance for error logging

    Returns:
        Parsed state data as dict

    Raises:
        ValueError: If state file contains invalid JSON
    """
    if logger is None:
        logger = setup_logging()

    try:
        logger.info("Parsing Terraform state file")
        state_data = json.loads(state_content)
        if not isinstance(state_data, dict):
            raise ValueError("State file did not parse to a dictionary.")
        logger.info(
            f"Successfully parsed state file with "
            f"{len(state_data.get('resources', []))} resources"
        )
        return state_data
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in state file: {e}")
        raise ValueError(f"Invalid JSON in state file: {e}")


def get_resource_id(resource: Dict[str, Any]) -> str:
    """
    Extracts the resource ID from a Terraform state resource.

    Args:
        resource: Resource dict from Terraform state

    Returns:
        Resource ID as string
    """
    instances = resource.get("instances", [])
    if instances and len(instances) > 0:
        attributes = instances[0].get("attributes", {})
        if isinstance(attributes, dict):
            return str(attributes.get("id", ""))
    return ""
