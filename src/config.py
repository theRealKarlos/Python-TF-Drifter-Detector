"""
Configuration loader for Terraform Drift Detector Lambda.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    """Configuration class for the drift detector."""

    s3_state_path: str
    aws_region: Optional[str] = None
    log_level: str = "INFO"
    max_retries: int = 3
    timeout_seconds: int = 30


def load_config() -> Config:
    """
    Loads and validates configuration for the Lambda function.

    Returns:
        Config object with validated settings

    Raises:
        ValueError: If required configuration is missing or invalid
    """
    # Required configuration
    s3_state_path = os.environ.get("STATE_FILE_S3_PATH")
    if not s3_state_path:
        raise ValueError("STATE_FILE_S3_PATH environment variable is required")

    # Validate S3 path format
    if not s3_state_path.startswith("s3://"):
        raise ValueError(
            "STATE_FILE_S3_PATH must be a valid S3 path starting with s3://"
        )

    # Optional configuration with defaults
    aws_region = os.environ.get("AWS_REGION")
    log_level = os.environ.get("LOG_LEVEL", "INFO")
    max_retries = int(os.environ.get("MAX_RETRIES", "3"))
    timeout_seconds = int(os.environ.get("TIMEOUT_SECONDS", "30"))

    return Config(
        s3_state_path=s3_state_path,
        aws_region=aws_region,
        log_level=log_level,
        max_retries=max_retries,
        timeout_seconds=timeout_seconds,
    )
