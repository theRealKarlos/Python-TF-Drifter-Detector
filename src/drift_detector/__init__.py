"""
Terraform Drift Detector Package.

This package provides comprehensive drift detection for AWS resources by comparing
Terraform state files with live AWS resources. It supports multiple AWS services
including EC2, S3, RDS, DynamoDB, Lambda, IAM, EventBridge, ECS, VPC, API Gateway,
and CloudWatch resources.

The drift detection process:
1. Downloads and parses Terraform state file from S3
2. Fetches live AWS resources for each resource type found in state
3. Compares state attributes with live resource attributes
4. Reports missing resources and attribute changes
"""

from .core import detect_drift

__all__ = ['detect_drift']
