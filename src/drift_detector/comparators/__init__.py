"""
AWS Resource Comparators Package.

This package contains service-specific modules for comparing Terraform state resources
with live AWS resources. Each module handles resources for a specific AWS service.
"""

from .base import compare_attributes, compare_resources

__all__ = [
    "compare_resources",
    "compare_attributes",
]
