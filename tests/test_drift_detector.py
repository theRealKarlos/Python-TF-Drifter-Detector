"""
Tests for drift detection functionality.
"""

import unittest
from unittest.mock import patch
import json
from src.drift_detector import detect_drift
from src.drift_detector.resource_comparators import compare_resources


class TestDriftDetector(unittest.TestCase):
    """
    Unit tests for the drift detection logic in the Terraform Drift Detector Lambda.
    All AWS interactions are mocked to avoid real API calls.
    """

    def setUp(self):
        """
        Set up a sample Terraform state for use in tests.
        """
        with open('tests/sample_state.json', 'r') as f:
            self.sample_state_json = f.read()
            f.seek(0)
            self.sample_state = json.load(f)

    @patch('src.utils.download_s3_file')
    def test_detect_drift_success(self, mock_download):
        """
        Test that drift detection completes successfully and returns the expected keys.
        All AWS clients and state file operations are mocked.
        """
        mock_download.return_value = self.sample_state_json

        config = {'s3_state_path': 's3://test-bucket/state.tfstate'}
        result = detect_drift(config)

        # Assert that the result contains the expected keys
        self.assertIn('drift_detected', result)
        self.assertIn('drifts', result)
        self.assertIn('summary', result)

    def test_compare_resources_missing_resource(self):
        """
        Test that a missing resource in AWS is correctly reported as drift.
        """
        live_resources = {}  # Simulate no live resources in AWS
        drift_report = compare_resources(self.sample_state, live_resources)

        # There should be one drift, and its type should be 'missing'
        self.assertEqual(len(drift_report['drifts']), 1)
        self.assertEqual(drift_report['drifts'][0]['type'], 'missing')


if __name__ == '__main__':
    unittest.main()
