"""
Utility functions for Terraform Drift Detector Lambda.
"""

import functools
import json
import logging
from typing import Callable, Dict, Optional, TypeVar, cast
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError


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


F = TypeVar("F", bound=Callable[..., dict])


def fetcher_error_handler(func: F) -> F:
    """
    Decorator for consistent error handling and logging in AWS resource fetchers.
    Catches AWS ClientError (including ClusterNotFoundException) and generic Exception,
    logs appropriately, and returns an empty dict.
    """

    @functools.wraps(func)
    def wrapper(*args: object, **kwargs: object) -> dict:
        logger = setup_logging()
        try:
            return func(*args, **kwargs)
        except ClientError as e:
            error = e.response.get("Error", {})
            code = error.get("Code", "")
            if code == "ClusterNotFoundException":
                logger.info("ECS cluster not found; treating as drift.")
                return {}
            logger.error(f"AWS ClientError in {func.__name__}: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            return {}

    return cast(F, wrapper)


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
) -> Dict:
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
        logger.debug("DEBUG: state_content being parsed:", repr(state_content))
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
