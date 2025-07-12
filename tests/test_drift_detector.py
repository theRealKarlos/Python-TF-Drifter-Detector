"""
Tests for drift detection functionality.
"""

import json
import unittest
from unittest.mock import patch, MagicMock

from src.drift_detector import detect_drift
from src.drift_detector.resource_comparators import compare_resources


class TestDriftDetector(unittest.TestCase):
    """
    Unit tests for the drift detection logic in the Terraform Drift Detector Lambda.
    All AWS interactions are mocked to avoid real API calls.
    """

    def setUp(self) -> None:
        """
        Set up a sample Terraform state for use in tests.
        """
        with open("tests/sample_state.json", "r") as f:
            self.sample_state_json = f.read()
            f.seek(0)
            self.sample_state = json.load(f)

    @patch("src.utils.download_s3_file")
    @patch("src.drift_detector.resource_fetchers.boto3.client")
    def test_detect_drift_success(
        self, mock_boto3_client: MagicMock, mock_download: MagicMock
    ) -> None:
        """
        Test that drift detection completes successfully and returns the expected keys.
        All AWS clients and state file operations are mocked.
        """
        # Mock the S3 download
        mock_download.return_value = self.sample_state_json

        # Mock all AWS clients to return empty responses
        mock_client = MagicMock()
        mock_client.describe_instances.return_value = {"Reservations": []}
        mock_client.list_buckets.return_value = {"Buckets": []}
        mock_client.describe_db_instances.return_value = {"DBInstances": []}
        mock_client.list_tables.return_value = {"TableNames": []}
        mock_client.list_functions.return_value = {"Functions": []}
        mock_client.list_roles.return_value = {"Roles": []}
        mock_client.list_policies.return_value = {"Policies": []}
        mock_client.list_event_buses.return_value = {"EventBuses": []}
        mock_client.list_rules.return_value = {"Rules": []}
        mock_client.list_clusters.return_value = {"clusterArns": []}
        mock_client.list_apis.return_value = {"items": []}
        mock_client.list_dashboards.return_value = {"DashboardEntries": []}
        mock_client.describe_alarms.return_value = {"MetricAlarms": []}
        mock_boto3_client.return_value = mock_client

        config = {"s3_state_path": "s3://test-bucket/state.tfstate"}
        result = detect_drift(config)

        # Assert that the result contains the expected keys
        self.assertIn("drift_detected", result)
        self.assertIn("drifts", result)
        self.assertIn("summary", result)

    def test_compare_resources_missing_resource(self) -> None:
        """
        Test that a missing resource in AWS is correctly reported as drift.
        """
        live_resources: dict = {}  # Simulate no live resources in AWS
        drift_report = compare_resources(self.sample_state, live_resources)

        # There should be one drift, and its type should be 'missing'
        self.assertEqual(len(drift_report["drifts"]), 1)
        self.assertEqual(drift_report["drifts"][0]["type"], "missing")


if __name__ == "__main__":
    unittest.main()
