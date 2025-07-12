"""
Unit tests for drift detection logic in the Terraform Drift Detector Lambda.
All AWS interactions are mocked to avoid real API calls.
"""

import json
import unittest
from unittest.mock import MagicMock, patch

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
            f.seek(0)
            self.sample_state = json.load(f)

    # The order of patch decorators is important: boto3.client is patched before download_s3_file.
    # This ensures the correct mock objects are injected into the test method.
    @patch("src.drift_detector.resource_fetchers.boto3.client")
    @patch("src.drift_detector.core.download_s3_file")
    def test_detect_drift_success(
        self, mock_download: MagicMock, mock_boto3_client: MagicMock
    ) -> None:
        """
        Test that drift detection completes successfully and returns the expected keys.
        All AWS clients and state file operations are mocked.
        """
        # Mock the S3 download to return a valid JSON string
        mock_download.return_value = json.dumps(self.sample_state)

        # Mock all AWS clients to return empty responses for all resource types
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

        # There should be one drift, and its type should be 'missing_resource'
        self.assertEqual(len(drift_report["drifts"]), 1)
        self.assertEqual(drift_report["drifts"][0]["drift_type"], "missing_resource")


if __name__ == "__main__":
    unittest.main()
