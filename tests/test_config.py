"""
Tests for configuration module.
"""

import unittest
from unittest.mock import patch

from src.config import Config, load_config


class TestConfig(unittest.TestCase):
    """Test configuration loading and validation."""

    @patch.dict("os.environ", {"STATE_FILE_S3_PATH": "s3://test-bucket/state.tfstate"})
    def test_load_config_success(self) -> None:
        """Test successful configuration loading."""
        config = load_config()
        self.assertIsInstance(config, Config)
        self.assertEqual(config.s3_state_path, "s3://test-bucket/state.tfstate")
        self.assertEqual(config.log_level, "INFO")
        self.assertEqual(config.max_retries, 3)

    @patch.dict("os.environ", {}, clear=True)
    def test_load_config_missing_required(self) -> None:
        """Test that missing required config raises ValueError."""
        with self.assertRaises(ValueError) as context:
            load_config()
        self.assertIn("STATE_FILE_S3_PATH", str(context.exception))

    @patch.dict("os.environ", {"STATE_FILE_S3_PATH": "invalid-path"})
    def test_load_config_invalid_s3_path(self) -> None:
        """Test that invalid S3 path raises ValueError."""
        with self.assertRaises(ValueError) as context:
            load_config()
        self.assertIn("must be a valid S3 path", str(context.exception))

    @patch.dict(
        "os.environ",
        {
            "STATE_FILE_S3_PATH": "s3://test-bucket/state.tfstate",
            "LOG_LEVEL": "DEBUG",
            "MAX_RETRIES": "5",
            "TIMEOUT_SECONDS": "60",
        },
    )
    def test_load_config_with_optional_values(self) -> None:
        """Test configuration loading with optional values."""
        config = load_config()
        self.assertEqual(config.log_level, "DEBUG")
        self.assertEqual(config.max_retries, 5)
        self.assertEqual(config.timeout_seconds, 60)


if __name__ == "__main__":
    unittest.main()
