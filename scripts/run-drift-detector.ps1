# PowerShell script to run the Terraform Drift Detector with a real S3 path
# This script provides a convenient way to run drift detection with proper setup

param(
    [Parameter(Mandatory = $true)]
    [string]$S3Path,
    
    [string]$Region = "eu-west-2",
    [ValidateSet("DEBUG", "INFO", "WARNING", "ERROR", "debug", "info", "warning", "error")]
    [string]$LogLevel = "INFO",
    [int]$MaxRetries = 3,
    [int]$TimeoutSeconds = 30,
    [ValidateSet("json", "pretty")]
    [string]$OutputFormat = "pretty"
)

Write-Host "Terraform Drift Detector - PowerShell Runner" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green

# Convert log level to uppercase for Python script compatibility
$LogLevel = $LogLevel.ToUpper()

# Check if virtual environment exists and activate it
if (Test-Path "env\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    & ".\env\Scripts\Activate.ps1"
}
else {
    Write-Host "Virtual environment not found. Please run the dev setup first:" -ForegroundColor Red
    Write-Host "  .\scripts\dev-setup.ps1" -ForegroundColor Yellow
    exit 1
}

# Validate S3 path
if (-not $S3Path.StartsWith("s3://")) {
    Write-Host "ERROR: S3 path must start with 's3://'" -ForegroundColor Red
    exit 1
}

# Check if run_drift_detector.py exists
if (-not (Test-Path "run_drift_detector.py")) {
    Write-Host "ERROR: run_drift_detector.py not found in current directory" -ForegroundColor Red
    exit 1
}

# Build the command
$cmdArgs = @(
    "python", "run_drift_detector.py",
    "--s3-path", $S3Path,
    "--region", $Region,
    "--log-level", $LogLevel,
    "--max-retries", $MaxRetries,
    "--timeout-seconds", $TimeoutSeconds,
    "--output-format", $OutputFormat
)

Write-Host "Running drift detection with the following parameters:" -ForegroundColor Cyan
Write-Host "  S3 Path: $S3Path" -ForegroundColor White
Write-Host "  Region: $Region" -ForegroundColor White
Write-Host "  Log Level: $LogLevel" -ForegroundColor White
Write-Host "  Max Retries: $MaxRetries" -ForegroundColor White
Write-Host "  Timeout: $TimeoutSeconds seconds" -ForegroundColor White
Write-Host "  Output Format: $OutputFormat" -ForegroundColor White
Write-Host ""

# Run the drift detector
Write-Host "Executing drift detection..." -ForegroundColor Yellow
& $cmdArgs[0] $cmdArgs[1..($cmdArgs.Length - 1)]

# Capture the exit code
$exitCode = $LASTEXITCODE

Write-Host ""
if ($exitCode -eq 0) {
    Write-Host "✅ Drift detection completed successfully (no drift detected)" -ForegroundColor Green
}
elseif ($exitCode -eq 1) {
    Write-Host "⚠️  Drift detection completed with drift detected or error occurred" -ForegroundColor Yellow
}
else {
    Write-Host "❌ Drift detection failed with exit code: $exitCode" -ForegroundColor Red
}

exit $exitCode 