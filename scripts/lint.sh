#!/bin/bash

# Linting Script for Terraform Drift Detector
# Runs mypy (type checking) and flake8 (style checking)

set -e

# Default values
TARGET=${1:-"src,tests"}
FIX=${2:-false}

echo "Running code quality checks..."
echo "Target: $TARGET"

ERROR_COUNT=0
SUCCESS_COUNT=0

# Function to run a command and handle results
run_lint_command() {
    local name="$1"
    local command="$2"
    local success_msg="$3"
    local error_msg="$4"
    
    echo ""
    echo "Running $name..."
    echo "Command: $command"
    
    if eval "$command"; then
        echo "✅ $success_msg"
        ((SUCCESS_COUNT++))
        return 0
    else
        echo "❌ $error_msg"
        ((ERROR_COUNT++))
        return 1
    fi
}

# Check if virtual environment is activated
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "Warning: Virtual environment not detected. Make sure you're in a virtual environment."
fi

# Run flake8 (style checking)
flake8_command="python -m flake8 $TARGET"
run_lint_command "flake8" "$flake8_command" "flake8 passed - no style issues found" "flake8 found style issues"

# Run mypy (type checking)
# mypy needs separate arguments, not comma-separated
mypy_targets=$(echo "$TARGET" | tr ',' ' ')
mypy_command="python -m mypy $mypy_targets"
run_lint_command "mypy" "$mypy_command" "mypy passed - no type issues found" "mypy found type issues"

# Summary
echo ""
echo "=================================================="
echo "LINTING SUMMARY"
echo "=================================================="
echo "✅ Passed: $SUCCESS_COUNT"
echo "❌ Failed: $ERROR_COUNT"

if [[ $ERROR_COUNT -eq 0 ]]; then
    echo ""
    echo "🎉 All linting checks passed!"
    exit 0
else
    echo ""
    echo "⚠️  Some linting checks failed. Please fix the issues above."
    echo ""
    echo "Tips:"
    echo "  - Run 'python -m black src tests' to format code"
    echo "  - Run 'python -m isort src tests' to sort imports"
    echo "  - Add type hints to functions for mypy"
    echo "  - Fix style issues reported by flake8"
    exit 1
fi 