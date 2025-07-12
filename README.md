# Terraform Drift Detector

A best-practice Python application for detecting drift between Terraform state and live AWS resources. Runs as an AWS Lambda function on an hourly schedule. Includes a lightweight React UI for visualising drift.

## Features

- Downloads Terraform state file from S3 (configurable path)
- Compares state to live AWS resources (EC2, S3, RDS, DynamoDB, Lambda, IAM, EventBridge, ECS, VPC, API Gateway, CloudWatch)
- Reports drift with detailed attribute comparisons
- Modular architecture for easy extension
- Comprehensive logging and error handling
- Designed for AWS Lambda with proper configuration validation

## Architecture

```
src/
├── main.py                    # Lambda entry point
├── config.py                  # Configuration management
├── utils.py                   # Utility functions and logging
└── drift_detector/           # Core drift detection logic
    ├── __init__.py           # Package exports
    ├── core.py               # Main orchestration
    ├── resource_fetchers.py  # AWS resource fetching
    └── resource_comparators.py # Resource comparison logic
```

## Development Setup

### 1. Install Dependencies

```powershell
# Create virtual environment
python -m venv env
.\env\Scripts\Activate.ps1

# Install runtime dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -e ".[dev]"
```

### 2. Environment Configuration

```powershell
# Required
$env:STATE_FILE_S3_PATH = 's3://your-bucket/path/to/terraform.tfstate'

# Optional
$env:LOG_LEVEL = 'INFO'  # DEBUG, INFO, WARNING, ERROR
$env:MAX_RETRIES = '3'
$env:TIMEOUT_SECONDS = '30'
```

### 3. Code Quality Tools

```powershell
# Linting
python -m flake8 src tests

# Type checking
python -m mypy src

# Code formatting
python -m black src tests
python -m isort src tests

# Run tests
python -m pytest tests/ -v --cov=src --cov-report=html
```

## Testing

The project includes comprehensive unit tests with mocking for AWS services:

```powershell
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=term-missing

# Run specific test file
python -m pytest tests/test_config.py -v
```

## Deployment

Deployment is handled via Terraform and GitHub Actions (see infra/ and .github/workflows/).

### Lambda Configuration

Required environment variables:

- `STATE_FILE_S3_PATH`: S3 path to Terraform state file

Optional environment variables:

- `LOG_LEVEL`: Logging level (default: INFO)
- `MAX_RETRIES`: Number of retries for AWS API calls (default: 3)
- `TIMEOUT_SECONDS`: Timeout for AWS API calls (default: 30)

## Supported AWS Resources

The drift detector supports comparison of the following AWS resources:

- **EC2**: Instances, VPCs
- **S3**: Buckets
- **RDS**: Database instances
- **DynamoDB**: Tables
- **Lambda**: Functions
- **IAM**: Roles and policies
- **EventBridge**: Buses and rules
- **ECS**: Clusters and services
- **API Gateway**: REST APIs
- **CloudWatch**: Dashboards and alarms

## Adding New Resource Types

To add support for new AWS resource types:

1. Add fetcher function to `src/drift_detector/resource_fetchers.py`
2. Add comparator function to `src/drift_detector/resource_comparators.py`
3. Register the new functions in the main routing logic
4. Add corresponding tests

## Code Quality Standards

- **Type Hints**: All functions include proper type annotations
- **Documentation**: Comprehensive docstrings for all public APIs
- **Error Handling**: Graceful error handling with proper logging
- **Testing**: Unit tests with mocking for all AWS interactions
- **Linting**: flake8 compliance with custom configuration
- **Formatting**: Black and isort for consistent code style

## Contributing

1. Follow the established code style (Black + isort)
2. Add type hints to all new functions
3. Include comprehensive docstrings
4. Write unit tests for new functionality
5. Ensure all tests pass and linting is clean

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure virtual environment is activated
2. **AWS Permissions**: Lambda execution role needs appropriate IAM permissions
3. **S3 Access**: Verify S3 bucket permissions and path correctness
4. **Timeout Issues**: Adjust `TIMEOUT_SECONDS` for large state files

### Debugging

Enable debug logging:

```powershell
$env:LOG_LEVEL = 'DEBUG'
```

Check CloudWatch logs for detailed execution information.
