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

## Development Setup (Python 3.13+)

### 1. Automated Environment Setup

**Windows/PowerShell:**

```powershell
# This script will:
# - Check for Python 3.13
# - Create a virtual environment (env/) with Python 3.13
# - Install all dependencies and dev tools
# - Run initial code quality checks and tests

./scripts/dev-setup.ps1
```

**Unix/Linux:**

- Manual setup is required (see below), or adapt the PowerShell script to Bash.

### 2. Manual Setup (if not using dev-setup.ps1)

```powershell
# Ensure you have Python 3.13 installed
python --version  # Should show Python 3.13.x

# Create virtual environment
python -m venv env
.\env\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration

```powershell
# Required
$env:STATE_FILE_S3_PATH = 's3://your-bucket/path/to/terraform.tfstate'

# Optional
$env:LOG_LEVEL = 'INFO'  # DEBUG, INFO, WARNING, ERROR
$env:MAX_RETRIES = '3'
$env:TIMEOUT_SECONDS = '30'
```

### 4. Code Quality & Security Workflow

The lint script now includes:

- **flake8** (style checks)
- **mypy** (type checks)
- **Safety** (dependency security scan)

```powershell
# Run all linting and security checks
./scripts/lint.ps1

# Or run individual tools:
python -m flake8 src tests      # Linting
python -m mypy src tests        # Type checking
python -m black src tests       # Code formatting
python -m isort src tests       # Import sorting
python -m safety scan           # Dependency security scan
python -m pytest tests/ -v      # Run tests
```

**For Unix/Linux systems:**

```bash
# Run all linting checks
./scripts/lint.sh

# Run with custom target
./scripts/lint.sh "src"
```

#### Safety Setup

- The first time you run the lint script, you may be prompted to register or log in to Safety (free account).
- Follow the instructions in your terminal to complete registration.
- After setup, Safety will automatically scan your dependencies for known vulnerabilities every time you run the lint script.

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
- **Security**: Safety scan for dependency vulnerabilities

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
