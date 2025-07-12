"""
AWS Lambda entry point for Terraform Drift Detector.
"""

import json
from .config import load_config
from .drift_detector import detect_drift
from .utils import setup_logging


def lambda_handler(event: dict, context: object) -> dict:
    """
    AWS Lambda handler function.

    Args:
        event: Lambda event data
        context: Lambda context

    Returns:
        Dictionary with statusCode and body containing drift report
    """
    try:
        # Load and validate configuration
        config = load_config()

        # Setup logging
        logger = setup_logging(config.log_level)
        logger.info("Starting Terraform drift detection")

        # Convert config to dict for backward compatibility
        config_dict = {
            's3_state_path': config.s3_state_path,
            'aws_region': config.aws_region,
            'log_level': config.log_level,
            'max_retries': config.max_retries,
            'timeout_seconds': config.timeout_seconds
        }

        # Perform drift detection
        drift_report = detect_drift(config_dict)

        logger.info(
            f"Drift detection completed. "
            f"Drift detected: {drift_report.get('drift_detected', False)}"
        )

        return {
            'statusCode': 200,
            'body': json.dumps(drift_report),
            'headers': {
                'Content-Type': 'application/json'
            }
        }

    except ValueError as e:
        # Configuration or validation errors
        logger.error(f"Configuration error: {str(e)}")
        return {
            'statusCode': 400,
            'body': json.dumps({
                'error': 'Configuration error',
                'message': str(e)
            }),
            'headers': {
                'Content-Type': 'application/json'
            }
        }

    except Exception as e:
        # Unexpected errors
        logger.error(f"Unexpected error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            }),
            'headers': {
                'Content-Type': 'application/json'
            }
        }
