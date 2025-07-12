"""
Core drift detection orchestration logic.

This module contains the main entry point for drift detection and coordinates
the overall drift detection process across all supported AWS resource types.
"""

from typing import Dict, Any
from ..utils import download_s3_file, parse_terraform_state
from .resource_fetchers import get_live_aws_resources
from .resource_comparators import compare_resources


def detect_drift(config: Dict) -> Dict[str, Any]:
    """
    Main entry point for drift detection. Orchestrates the entire drift detection process.

    This function:
    - Downloads the Terraform state file from S3
    - Parses the state file to extract resource information
    - Fetches live AWS resources for comparison
    - Compares state with live resources to identify drift
    - Returns a comprehensive drift report

    Args:
        config: Configuration dictionary containing S3 state file path

    Returns:
        Dictionary containing drift report with detected changes and summary statistics
    """
    try:
        # Step 1: Download and parse Terraform state file from S3
        state_content = download_s3_file(config['s3_state_path'])
        state_data = parse_terraform_state(state_content)

        # Step 2: Fetch live AWS resources for comparison
        live_resources = get_live_aws_resources(state_data)

        # Step 3: Compare state resources with live AWS resources
        drift_report = compare_resources(state_data, live_resources)

        # Step 4: Return comprehensive drift report with summary
        return {
            'drift_detected': len(drift_report['drifts']) > 0,
            'drifts': drift_report['drifts'],
            'summary': {
                'total_resources': len(state_data.get('resources', [])),
                'drift_count': len(drift_report['drifts']),
                'timestamp': drift_report['timestamp']
            }
        }

    except Exception as e:
        # Handle any errors during drift detection and return error information
        return {
            'error': str(e),
            'drift_detected': False,
            'drifts': []
        }
