# Terraform Drift Detector

> **⚠️ Lab Project Disclaimer**  
> This is a **lab project** designed to demonstrate Python and AWS Lambda best practices. It is intended for educational purposes and learning about cloud infrastructure management, not for production use. The code showcases modern Python development practices, AWS integration patterns, and infrastructure-as-code concepts.

A best-practice Python application for detecting drift between Terraform state and live AWS resources. Designed to run as an AWS Lambda function with comprehensive drift detection capabilities.

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

### 1. Manual Setup

```powershell
# Ensure you have Python 3.13 installed
python --version  # Should show Python 3.13.x

# Create virtual environment
python -m venv env

# Activate the virtual environment
.\env\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

```powershell
# Required
$env:STATE_FILE_S3_PATH = 's3://your-bucket/path/to/terraform.tfstate'

# Optional
$env:AWS_REGION = 'eu-west-2'  # AWS region for all API calls (default: eu-west-2)
$env:LOG_LEVEL = 'INFO'  # DEBUG, INFO, WARNING, ERROR
$env:MAX_RETRIES = '3'
$env:TIMEOUT_SECONDS = '30'
```

- The AWS region is set in the config file (`src/config.py`) and defaults to `eu-west-2`.
- You can override the region by setting the `AWS_REGION` environment variable.

### 3. Code Quality & Security Workflow

The project uses several code quality tools:

- **flake8** (style checks)
- **mypy** (type checks)
- **Safety** (dependency security scan)

```powershell
# Run individual tools:
python -m flake8 src tests      # Linting
python -m mypy src tests        # Type checking
python -m black src tests       # Code formatting
python -m isort src tests       # Import sorting
python -m safety scan           # Dependency security scan
python -m pytest tests/ -v      # Run tests

# Or use the provided scripts:
# Windows (PowerShell):
.\scripts\lint.ps1 src,tests

# Linux/macOS (bash):
./scripts/lint.sh src,tests
```

**Troubleshooting tip:**
If you encounter formatting or import sorting errors, you can fix them by running black and isort on the affected files or directories. For example:

```powershell
python -m black tests/
python -m isort tests/
```

This will automatically reformat and sort imports in your test files.

#### Safety Setup

- The first time you run Safety, you may be prompted to register or log in (free account).
- Follow the instructions in your terminal to complete registration.
- After setup, Safety will automatically scan your dependencies for known vulnerabilities.

## Running the Drift Detector

### Local Execution with Real S3 Path

While this project is designed to run as an AWS Lambda function, we provide local execution tools for **development, testing, and debugging** with real Terraform state files. This is particularly useful for:

- **Testing drift detection** with your actual infrastructure state files
- **Debugging drift issues** with detailed logging and error messages
- **CI/CD integration** for automated drift detection in pipelines
- **Development workflow** without needing to deploy Lambda functions

#### Why Local Execution Instead of Lambda?

The `src/main.py` file contains the AWS Lambda handler function, which is designed for AWS's serverless environment. While you _could_ run it locally by mocking the Lambda event and context, our approach provides several advantages:

**Lambda Function Limitations for Local Use:**

- Expects Lambda event/context objects
- Returns HTTP-style responses with status codes
- Configuration via environment variables only
- Designed for AWS Lambda runtime environment

**Our Local Tools Provide:**

- **Command-line interface** with flexible parameters
- **Better error handling** and debugging output
- **Multiple output formats** (pretty, JSON) for different use cases
- **Direct access** to core drift detection logic
- **Easy integration** into scripts and automation

### Running the Drift Detector Locally

You can run the drift detector locally with a real S3 path using the provided command-line script:

```powershell
# Basic usage with S3 path
python run_drift_detector.py --s3-path s3://your-bucket/path/to/terraform.tfstate

# Specify AWS region
python run_drift_detector.py --s3-path s3://your-bucket/terraform.tfstate --region us-east-1

# Enable debug logging
python run_drift_detector.py --s3-path s3://your-bucket/terraform.tfstate --log-level DEBUG

# Output as JSON format
python run_drift_detector.py --s3-path s3://your-bucket/terraform.tfstate --output-format json

# Using PowerShell script (Windows)
.\scripts\run-drift-detector.ps1 -S3Path "s3://your-bucket/terraform.tfstate" -Region "us-east-1" -LogLevel "DEBUG"

# Using bash script (Linux/macOS)
./scripts/lint.sh src,tests

# Note: PowerShell parameters are case-insensitive, but log level values should be uppercase
# Valid log levels: DEBUG, INFO, WARNING, ERROR
```

**Prerequisites:**

- AWS credentials configured (via AWS CLI, environment variables, or IAM roles)
- Python 3.13+ and virtual environment set up
- Dependencies installed (`pip install -r requirements.txt`)

**Exit Codes:**

- `0`: No drift detected
- `1`: Drift detected or error occurred

### Testing

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

This is a lab project designed for educational purposes. For production deployment, you would need to:

1. Set up AWS Lambda function with appropriate IAM permissions
2. Configure environment variables for S3 state file access
3. Set up CloudWatch logging and monitoring

### Lambda Configuration

Required environment variables:

- `STATE_FILE_S3_PATH`: S3 path to Terraform state file

Optional environment variables:

- `AWS_REGION`: AWS region for all API calls (default: eu-west-2)
- `LOG_LEVEL`: Logging level (default: INFO)
- `MAX_RETRIES`: Number of retries for AWS API calls (default: 3)
- `TIMEOUT_SECONDS`: Timeout for AWS API calls (default: 30)

## Supported AWS Resources

The drift detector supports comparison of the following AWS resources:

| Resource Type   | Subtypes/Notes                              | Status | Notes/Comments                                                              |
| --------------- | ------------------------------------------- | ------ | --------------------------------------------------------------------------- |
| **EC2**         | Instances, VPCs, subnets, route tables      | ⚠️     | Implemented, some subtypes confirmed, some “No live name found” need review |
| **S3**          | Buckets                                     | ✅     | Confirmed working                                                           |
| **RDS**         | Database instances                          | ⚠️     | Implemented, not yet tested                                                 |
| **DynamoDB**    | Tables                                      | ✅     | Confirmed working                                                           |
| **Lambda**      | Functions, permissions                      | ✅     | Confirmed working                                                           |
| **IAM**         | Roles, policies                             | ✅     | Confirmed working, policy normalisation robust                              |
| **EventBridge** | Buses, rules, targets                       | ✅     | Confirmed working, composite keying robust                                  |
| **ECS**         | Clusters, services, task definitions        | ⚠️     | Implemented, some subtypes confirmed, task definitions need review          |
| **API Gateway** | REST APIs, resources, methods, stages, etc. | ⚠️     | Implemented, some subtypes confirmed, some “missing_resource”/empty keys    |
| **CloudWatch**  | Dashboards, alarms, log groups, event rules | ⚠️     | Implemented, some subtypes confirmed, log groups need review                |
| **SQS**         | Queues, queue policies                      | ✅     | Confirmed working                                                           |

**Legend:**

- ✅ **Tested**: Resource type has been verified with real AWS resources and drift detection confirmed working
- ⚠️ **Implemented but not fully confirmed**: Resource fetcher and comparator implemented, but not all subtypes or edge cases have been tested with live AWS resources. Some subtypes may have issues (see Notes/Comments).

**Note:**

- SQS queue policy drift detection is now confirmed working and included under SQS.
- IAM role policy document comparison uses normalisation to avoid false drift due to format differences.
- For resource types marked ⚠️, see debug output and logs for details on which subtypes may need further review or fixes.

### Special Handling: IAM Role Policy Normalisation

The drift detector normalises IAM role policy document comparisons. This means that differences in format (e.g. JSON string in state vs dict from AWS) do **not** cause false drift. Only real content differences are reported. This is implemented in the IAM role policy comparator in `src/drift_detector/resource_comparators.py`.

## Adding New Resource Types

To add support for new AWS resource types:

1. Add fetcher function to `src/drift_detector/resource_fetchers.py`
2. Add comparator function to `src/drift_detector/resource_comparators.py`
3. Register the new functions in the main routing logic
4. Add corresponding tests

**Important:** When adding new comparators, always register more specific resource types (e.g. `aws_iam_role_policy`) before more general ones (e.g. `aws_iam_role`) in the routing logic. This ensures the correct comparator is called and prevents subtle bugs.

## Centralised Logging

- All logging is centralised using Python's `logging` module, configured via `setup_logging()` in `src/utils.py`.
- All operational, debug, and error output uses the logger (`logger.debug`, `logger.info`, `logger.error`, etc.).
- No `print()` statements are used in the main codebase; all output is routed through the logger for consistency and production readiness.
- Log level can be configured via the `LOG_LEVEL` environment variable (e.g., `DEBUG`, `INFO`, `WARNING`, `ERROR`).

## Code Quality Standards

- **Type Hints**: All functions include proper type annotations. For AWS clients, `Any` is used intentionally due to the dynamic nature of boto3 clients. For drift details and resource attributes, `Dict[str, Any]` is used for flexibility and to accommodate the variety of AWS resource data.
- **Documentation**: Comprehensive docstrings for all public APIs
- **Error Handling & Logging**: Graceful error handling with proper, centralised logging throughout the codebase. All logs are routed through a single logger instance for consistency and easy configuration.

## Troubleshooting

### Deprecation Warnings

The project suppresses deprecation warnings from the AWS SDK (`botocore`) that use the deprecated `datetime.datetime.utcnow()` method. This is configured in `pyproject.toml` and is a known issue in the AWS SDK that doesn't affect functionality.

If you see other deprecation warnings, they can be addressed by updating dependencies or adding specific filters to the pytest configuration.

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

## Future Improvements

This lab project demonstrates core drift detection concepts. For a production-ready system, consider these enhancements:

### AWS Lambda Deployment

- **Scheduled Execution**: Set up CloudWatch Events/EventBridge rules for hourly drift detection
- **IAM Permissions**: Configure least-privilege IAM roles for Lambda execution
- **Environment Variables**: Secure configuration management for S3 paths and AWS regions
- **CloudWatch Logging**: Structured logging with proper log levels and filtering

### React UI for Drift Visualisation

- **Real-time Dashboard**: Web interface showing current drift status
- **Historical Tracking**: Timeline view of drift changes over time
- **Resource Details**: Drill-down views for individual resource drift
- **Alert Management**: Configure and manage drift notifications
- **User Authentication**: Secure access control for drift reports

### CI/CD Workflow Automation

- **GitHub Actions**: Automated testing and deployment pipelines
- **Terraform Infrastructure**: IaC for Lambda, S3, and supporting resources
- **Security Scanning**: Automated dependency and code security checks
- **Environment Promotion**: Staging to production deployment workflows
- **Monitoring Integration**: CloudWatch alarms and SNS notifications

### Enhanced Features

- **Multi-Region Support**: Detect drift across multiple AWS regions
- **Custom Resource Types**: Extensible framework for new AWS services
- **Drift Remediation**: Automated fixes for common drift scenarios
- **Integration APIs**: REST API for external system integration
- **Advanced Filtering**: Resource type and attribute-based drift filtering

These improvements would transform this educational project into a production-ready infrastructure monitoring solution.
