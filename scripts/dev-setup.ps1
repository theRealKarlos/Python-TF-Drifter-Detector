# Development Setup Script for Terraform Drift Detector
# This script sets up the development environment with all necessary tools

Write-Host "Setting up Terraform Drift Detector development environment..." -ForegroundColor Green

# Check if Python is installed
try {
    $pythonVersion = python --version
    Write-Host "Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "Python not found. Please install Python 3.9 or later." -ForegroundColor Red
    exit 1
}

# Create virtual environment if it doesn't exist
if (-not (Test-Path "env")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv env
} else {
    Write-Host "Virtual environment already exists." -ForegroundColor Yellow
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& ".\env\Scripts\Activate.ps1"

# Upgrade pip
Write-Host "Upgrading pip..." -ForegroundColor Yellow
python -m pip install --upgrade pip

# Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Yellow
pip install -r requirements.txt

# Install development dependencies
Write-Host "Installing development dependencies..." -ForegroundColor Yellow
pip install pytest pytest-cov mypy black isort

# Run initial checks
Write-Host "Running initial code quality checks..." -ForegroundColor Yellow

# Linting
Write-Host "Running flake8..." -ForegroundColor Cyan
python -m flake8 src tests

# Type checking
Write-Host "Running mypy..." -ForegroundColor Cyan
python -m mypy src

# Formatting
Write-Host "Running black..." -ForegroundColor Cyan
python -m black --check src tests

# Import sorting
Write-Host "Running isort..." -ForegroundColor Cyan
python -m isort --check-only src tests

# Run tests
Write-Host "Running tests..." -ForegroundColor Cyan
python -m pytest tests/ -v

Write-Host "Development environment setup complete!" -ForegroundColor Green
Write-Host "To activate the environment in a new shell, run: .\env\Scripts\Activate.ps1" -ForegroundColor Yellow 