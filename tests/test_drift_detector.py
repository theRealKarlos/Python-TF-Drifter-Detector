"""
Unit tests for drift detection logic in the Terraform Drift Detector Lambda.
All AWS interactions are mocked to avoid real API calls.
"""

import json
import unittest
from unittest.mock import MagicMock, patch

from src.drift_detector import detect_drift
from src.drift_detector.comparators import compare_resources


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
    @patch("src.drift_detector.fetchers.base.boto3.client")
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

    def test_lambda_function_no_drift(self) -> None:
        """Test Lambda function: no drift when attributes match."""
        state = {
            "resources": [
                {
                    "type": "aws_lambda_function",
                    "name": "test_lambda",
                    "instances": [
                        {
                            "attributes": {
                                "function_name": "my-func",
                                "arn": "arn:aws:lambda:region:acct:function:my-func",
                            }
                        }
                    ],
                }
            ]
        }
        # Keying logic: use ARN
        state_key = "arn:aws:lambda:region:acct:function:my-func"
        live = {state_key: {"function_name": "my-func", "arn": state_key}}
        drifts = compare_resources(state, live)
        print(
            f"DEBUG (Lambda): state key = {state_key}, live keys = {list(live.keys())}, "
            f"drifts = {drifts['drifts']}"
        )
        self.assertEqual(len(drifts["drifts"]), 0)

    def test_lambda_function_attribute_drift(self) -> None:
        """Test Lambda function: drift detected when function_name differs."""
        state = {
            "resources": [
                {
                    "type": "aws_lambda_function",
                    "name": "test_lambda",
                    "instances": [
                        {
                            "attributes": {
                                "function_name": "my-func",
                                "arn": "arn:aws:lambda:region:acct:function:my-func",
                            }
                        }
                    ],
                }
            ]
        }
        state_key = "arn:aws:lambda:region:acct:function:my-func"
        live = {state_key: {"function_name": "other-func", "arn": state_key}}
        drifts = compare_resources(state, live)
        print(
            f"DEBUG (Lambda): state key = {state_key}, live keys = {list(live.keys())}, "
            f"drifts = {drifts['drifts']}"
        )
        self.assertEqual(len(drifts["drifts"]), 1)
        self.assertEqual(drifts["drifts"][0]["drift_type"], "attribute_drift")

    def test_sqs_queue_no_drift(self) -> None:
        """Test SQS queue: no drift when attributes match."""
        state = {
            "resources": [
                {
                    "type": "aws_sqs_queue",
                    "name": "test_queue",
                    "instances": [
                        {
                            "attributes": {
                                "arn": "arn:aws:sqs:region:acct:my-queue",
                                "QueueName": "my-queue",
                            }
                        }
                    ],
                }
            ]
        }
        state_key = "arn:aws:sqs:region:acct:my-queue"
        live = {state_key: {"QueueName": "my-queue", "arn": state_key}}
        drifts = compare_resources(state, live)
        print(
            f"DEBUG (SQS): state key = {state_key}, live keys = {list(live.keys())}, "
            f"drifts = {drifts['drifts']}"
        )
        self.assertEqual(len(drifts["drifts"]), 0)

    def test_sqs_queue_attribute_drift(self) -> None:
        """Test SQS queue: drift detected when QueueName differs."""
        state = {
            "resources": [
                {
                    "type": "aws_sqs_queue",
                    "name": "test_queue",
                    "instances": [
                        {
                            "attributes": {
                                "arn": "arn:aws:sqs:region:acct:my-queue",
                                "QueueName": "my-queue",
                            }
                        }
                    ],
                }
            ]
        }
        state_key = "arn:aws:sqs:region:acct:my-queue"
        live = {state_key: {"QueueName": "other-queue", "arn": state_key}}
        drifts = compare_resources(state, live)
        print(
            f"DEBUG (SQS): state key = {state_key}, live keys = {list(live.keys())}, "
            f"drifts = {drifts['drifts']}"
        )
        self.assertEqual(len(drifts["drifts"]), 1)
        self.assertEqual(drifts["drifts"][0]["drift_type"], "attribute_drift")

    def test_dynamodb_table_no_drift(self) -> None:
        """Test DynamoDB table: no drift when attributes match."""
        state = {
            "resources": [
                {
                    "type": "aws_dynamodb_table",
                    "name": "test_table",
                    "instances": [
                        {
                            "attributes": {
                                "arn": "arn:aws:dynamodb:region:acct:table/my-table",
                                "TableName": "my-table",
                            }
                        }
                    ],
                }
            ]
        }
        state_key = "arn:aws:dynamodb:region:acct:table/my-table"
        live = {state_key: {"TableName": "my-table", "arn": state_key}}
        drifts = compare_resources(state, live)
        print(
            f"DEBUG (DynamoDB): state key = {state_key}, live keys = {list(live.keys())}, "
            f"drifts = {drifts['drifts']}"
        )
        self.assertEqual(len(drifts["drifts"]), 0)

    def test_dynamodb_table_attribute_drift(self) -> None:
        """Test DynamoDB table: drift detected when TableName differs."""
        state = {
            "resources": [
                {
                    "type": "aws_dynamodb_table",
                    "name": "test_table",
                    "instances": [
                        {
                            "attributes": {
                                "arn": "arn:aws:dynamodb:region:acct:table/my-table",
                                "TableName": "my-table",
                            }
                        }
                    ],
                }
            ]
        }
        state_key = "arn:aws:dynamodb:region:acct:table/my-table"
        live = {state_key: {"TableName": "other-table", "arn": state_key}}
        drifts = compare_resources(state, live)
        print(
            f"DEBUG (DynamoDB): state key = {state_key}, live keys = {list(live.keys())}, "
            f"drifts = {drifts['drifts']}"
        )
        self.assertEqual(len(drifts["drifts"]), 1)
        self.assertEqual(drifts["drifts"][0]["drift_type"], "attribute_drift")

    def test_ecs_cluster_no_drift(self) -> None:
        """Test ECS cluster: no drift when attributes match."""
        state = {
            "resources": [
                {
                    "type": "aws_ecs_cluster",
                    "name": "test_cluster",
                    "instances": [
                        {
                            "attributes": {
                                "arn": "arn:aws:ecs:region:acct:cluster/my-cluster",
                                "clusterName": "my-cluster",
                            }
                        }
                    ],
                }
            ]
        }
        state_key = "arn:aws:ecs:region:acct:cluster/my-cluster"
        live = {state_key: {"clusterName": "my-cluster", "arn": state_key}}
        drifts = compare_resources(state, live)
        print(
            f"DEBUG (ECS): state key = {state_key}, live keys = {list(live.keys())}, "
            f"drifts = {drifts['drifts']}"
        )
        self.assertEqual(len(drifts["drifts"]), 0)

    def test_ecs_cluster_attribute_drift(self) -> None:
        """Test ECS cluster: drift detected when clusterName differs."""
        state = {
            "resources": [
                {
                    "type": "aws_ecs_cluster",
                    "name": "test_cluster",
                    "instances": [
                        {
                            "attributes": {
                                "arn": "arn:aws:ecs:region:acct:cluster/my-cluster",
                                "clusterName": "my-cluster",
                            }
                        }
                    ],
                }
            ]
        }
        state_key = "arn:aws:ecs:region:acct:cluster/my-cluster"
        live = {state_key: {"clusterName": "other-cluster", "arn": state_key}}
        drifts = compare_resources(state, live)
        print(
            f"DEBUG (ECS): state key = {state_key}, live keys = {list(live.keys())}, "
            f"drifts = {drifts['drifts']}"
        )
        self.assertEqual(len(drifts["drifts"]), 1)
        self.assertEqual(drifts["drifts"][0]["drift_type"], "attribute_drift")

    def test_eventbridge_rule_no_drift(self) -> None:
        """Test EventBridge rule: no drift when attributes match."""
        state = {
            "resources": [
                {
                    "type": "aws_cloudwatch_event_rule",
                    "name": "test_rule",
                    "instances": [
                        {
                            "attributes": {
                                "arn": "arn:aws:events:region:acct:rule/my-rule",
                                "name": "my-rule",
                            }
                        }
                    ],
                }
            ]
        }
        state_key = "arn:aws:events:region:acct:rule/my-rule"
        live = {state_key: {"name": "my-rule", "arn": state_key}}
        drifts = compare_resources(state, live)
        print(
            f"DEBUG (EventBridge): state key = {state_key}, live keys = {list(live.keys())}, "
            f"drifts = {drifts['drifts']}"
        )
        self.assertEqual(len(drifts["drifts"]), 0)

    def test_eventbridge_rule_attribute_drift(self) -> None:
        """Test EventBridge rule: drift detected when name differs."""
        state = {
            "resources": [
                {
                    "type": "aws_cloudwatch_event_rule",
                    "name": "test_rule",
                    "instances": [
                        {
                            "attributes": {
                                "arn": "arn:aws:events:region:acct:rule/my-rule",
                                "name": "my-rule",
                            }
                        }
                    ],
                }
            ]
        }
        state_key = "arn:aws:events:region:acct:rule/my-rule"
        live = {state_key: {"name": "other-rule", "arn": state_key}}
        drifts = compare_resources(state, live)
        print(
            f"DEBUG (EventBridge): state key = {state_key}, live keys = {list(live.keys())}, "
            f"drifts = {drifts['drifts']}"
        )
        self.assertEqual(len(drifts["drifts"]), 1)
        self.assertEqual(drifts["drifts"][0]["drift_type"], "attribute_drift")

    def test_apigateway_resource_no_drift(self) -> None:
        """Test API Gateway resource: no drift when attributes match."""
        state = {
            "resources": [
                {
                    "type": "aws_api_gateway_resource",
                    "name": "test_resource",
                    "instances": [
                        {
                            "attributes": {
                                "rest_api_id": "apiid",
                                "resource_id": "resid",
                                "id": "abc123",
                            }
                        }
                    ],
                }
            ]
        }
        # Keying logic: composite key
        state_key = "apigw_resource:apiid:resid"
        live = {
            state_key: {"rest_api_id": "apiid", "resource_id": "resid", "id": "abc123"}
        }
        drifts = compare_resources(state, live)
        print(
            f"DEBUG (APIGW): state key = {state_key}, live keys = {list(live.keys())}, "
            f"drifts = {drifts['drifts']}"
        )
        self.assertEqual(len(drifts["drifts"]), 0)

    def test_apigateway_resource_attribute_drift(self) -> None:
        """Test API Gateway resource: drift detected when id differs."""
        state = {
            "resources": [
                {
                    "type": "aws_api_gateway_resource",
                    "name": "test_resource",
                    "instances": [
                        {
                            "attributes": {
                                "rest_api_id": "apiid",
                                "resource_id": "resid",
                                "id": "abc123",
                            }
                        }
                    ],
                }
            ]
        }
        state_key = "apigw_resource:apiid:resid"
        live = {
            state_key: {"rest_api_id": "apiid", "resource_id": "resid", "id": "otherid"}
        }
        drifts = compare_resources(state, live)
        print(
            f"DEBUG (APIGW): state key = {state_key}, live keys = {list(live.keys())}, "
            f"drifts = {drifts['drifts']}"
        )
        self.assertEqual(len(drifts["drifts"]), 1)
        self.assertEqual(drifts["drifts"][0]["drift_type"], "attribute_drift")

    def test_s3_bucket_no_drift(self) -> None:
        """Test S3 bucket: no drift when attributes match."""
        state = {
            "resources": [
                {
                    "type": "aws_s3_bucket",
                    "name": "test_bucket",
                    "instances": [
                        {
                            "attributes": {
                                "arn": "arn:aws:s3:::my-bucket",
                                "bucket": "my-bucket",
                            }
                        }
                    ],
                }
            ]
        }
        state_key = "arn:aws:s3:::my-bucket"
        live = {state_key: {"bucket": "my-bucket", "arn": state_key}}
        drifts = compare_resources(state, live)
        print(
            f"DEBUG (S3): state key = {state_key}, live keys = {list(live.keys())}, "
            f"drifts = {drifts['drifts']}"
        )
        self.assertEqual(len(drifts["drifts"]), 0)

    def test_s3_bucket_attribute_drift(self) -> None:
        """Test S3 bucket: drift detected when bucket name differs."""
        state = {
            "resources": [
                {
                    "type": "aws_s3_bucket",
                    "name": "test_bucket",
                    "instances": [
                        {
                            "attributes": {
                                "arn": "arn:aws:s3:::my-bucket",
                                "bucket": "my-bucket",
                            }
                        }
                    ],
                }
            ]
        }
        state_key = "arn:aws:s3:::my-bucket"
        live = {state_key: {"bucket": "other-bucket", "arn": state_key}}
        drifts = compare_resources(state, live)
        print(
            f"DEBUG (S3): state key = {state_key}, live keys = {list(live.keys())}, "
            f"drifts = {drifts['drifts']}"
        )
        self.assertEqual(len(drifts["drifts"]), 1)
        self.assertEqual(drifts["drifts"][0]["drift_type"], "attribute_drift")


if __name__ == "__main__":
    unittest.main()
