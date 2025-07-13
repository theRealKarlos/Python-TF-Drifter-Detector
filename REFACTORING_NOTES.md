# Refactoring Notes: Fetcher and Comparator Organization

## Overview

The original `resource_fetchers.py` (802 lines) and `resource_comparators.py` (641 lines) files have been refactored into a more maintainable, service-based organization.

## New Structure

### Fetchers Package (`src/drift_detector/fetchers/`)

- **`__init__.py`** - Package initialization and exports
- **`base.py`** - Main orchestration logic and AWS client initialization
- **`ec2_fetchers.py`** - EC2 instances and VPCs
- **`s3_fetchers.py`** - S3 buckets
- **`rds_fetchers.py`** - RDS database instances
- **`dynamodb_fetchers.py`** - DynamoDB tables
- **`lambda_fetchers.py`** - Lambda functions and permissions
- **`iam_fetchers.py`** - IAM roles, policies, role policies, and OIDC providers
- **`events_fetchers.py`** - EventBridge buses, rules, and targets
- **`ecs_fetchers.py`** - ECS clusters and services
- **`apigateway_fetchers.py`** - API Gateway REST APIs
- **`cloudwatch_fetchers.py`** - CloudWatch dashboards and alarms
- **`data_source_fetchers.py`** - Terraform data sources (aws_region, aws_caller_identity)

### Comparators Package (`src/drift_detector/comparators/`)

- **`__init__.py`** - Package initialization and exports
- **`base.py`** - Main orchestration logic and routing
- **`ec2_comparators.py`** - EC2 instances and VPCs
- **`s3_comparators.py`** - S3 buckets
- **`rds_comparators.py`** - RDS database instances
- **`dynamodb_comparators.py`** - DynamoDB tables
- **`lambda_comparators.py`** - Lambda functions and permissions
- **`iam_comparators.py`** - IAM roles, policies, role policies, and OIDC providers
- **`events_comparators.py`** - EventBridge buses, rules, and targets
- **`ecs_comparators.py`** - ECS clusters and services
- **`apigateway_comparators.py`** - API Gateway REST APIs
- **`cloudwatch_comparators.py`** - CloudWatch dashboards and alarms

## Benefits of Refactoring

### 1. **Service-Based Organization**

- Each AWS service has its own module
- Easier to find and modify code for specific services
- Clear separation of concerns

### 2. **Reduced File Sizes**

- Original: 802 lines (fetchers) + 641 lines (comparators) = 1,443 lines
- New: 12 smaller modules averaging ~50-100 lines each
- Much more manageable and readable

### 3. **Better Maintainability**

- Adding new resource types only requires modifying the relevant service module
- Easier to test individual service functionality
- Reduced merge conflicts when multiple developers work on different services

### 4. **Improved Code Organization**

- Common patterns extracted and reused
- Service-specific logic isolated
- Clear import structure

### 5. **Enhanced Developer Experience**

- Easier to navigate and understand codebase
- Better IDE support with smaller files
- Clearer responsibility boundaries

## Migration Notes

### Import Changes

- Old: `from .resource_fetchers import get_live_aws_resources`
- New: `from .fetchers import get_live_aws_resources`

- Old: `from .resource_comparators import compare_resources`
- New: `from .comparators import compare_resources`

### Function Signatures

All public function signatures remain the same, ensuring backward compatibility.

### Routing Logic

The routing logic in `base.py` modules maintains the same resource type matching as before, ensuring no functional changes.

## Future Enhancements

This refactoring provides a solid foundation for:

1. **Adding new AWS services** - Simply create new service-specific modules
2. **Service-specific configuration** - Each service module can have its own configuration
3. **Parallel processing** - Service modules can be processed independently
4. **Service-specific error handling** - Custom error handling per service
5. **Service-specific logging** - Targeted logging for each service

## Testing

All existing functionality has been preserved. The refactoring is purely organisational - no behavioural changes were made to the drift detection logic.
