# Linting Script for Terraform Drift Detector
# Runs mypy (type checking), flake8 (style checking), and safety (dependency security)

param(
    [string]$Target = "src,tests",
    [switch]$Fix = $false
)

Write-Host "Running code quality checks..." -ForegroundColor Green
Write-Host "Target: $Target" -ForegroundColor Cyan

$ErrorCount = 0
$SuccessCount = 0

# Function to run a command and handle results
function Invoke-LintCommand {
    param(
        [string]$Name,
        [string]$Command,
        [string]$SuccessMessage,
        [string]$ErrorMessage
    )
    
    Write-Host "`nRunning $Name..." -ForegroundColor Yellow
    Write-Host "Command: $Command" -ForegroundColor Gray
    
    try {
        $result = Invoke-Expression $Command
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ $SuccessMessage" -ForegroundColor Green
            $script:SuccessCount++
            return $true
        }
        else {
            Write-Host "❌ $ErrorMessage" -ForegroundColor Red
            $script:ErrorCount++
            return $false
        }
    }
    catch {
        Write-Host "❌ Error running $Name`: $($_.Exception.Message)" -ForegroundColor Red
        $script:ErrorCount++
        return $false
    }
}

# Check if virtual environment is activated
if (-not $env:VIRTUAL_ENV) {
    Write-Host "Warning: Virtual environment not detected. Make sure you're in a virtual environment." -ForegroundColor Yellow
}

# Run flake8 (style checking)
# flake8 needs separate arguments, not comma-separated
$flake8Targets = $Target -split ','
$flake8Command = "python -m flake8 $($flake8Targets -join ' ')"
Invoke-LintCommand -Name "flake8" -Command $flake8Command -SuccessMessage "flake8 passed - no style issues found" -ErrorMessage "flake8 found style issues"

# Run mypy (type checking)
# mypy needs separate arguments, not comma-separated
$mypyTargets = $Target -split ','
$mypyCommand = "python -m mypy $($mypyTargets -join ' ')"
Invoke-LintCommand -Name "mypy" -Command $mypyCommand -SuccessMessage "mypy passed - no type issues found" -ErrorMessage "mypy found type issues"

# Run Safety (dependency security scan)
Write-Host "`nRunning Safety (dependency security scan)..." -ForegroundColor Yellow
$safetyCommand = "python -m safety scan"
Invoke-LintCommand -Name "safety" -Command $safetyCommand -SuccessMessage "No known dependency vulnerabilities found" -ErrorMessage "Dependency vulnerabilities found (see above)"

# Summary
Write-Host "`n" + ("=" * 50) -ForegroundColor Blue
Write-Host "LINTING SUMMARY" -ForegroundColor Blue
Write-Host ("=" * 50) -ForegroundColor Blue
Write-Host "✅ Passed: $SuccessCount" -ForegroundColor Green
Write-Host "❌ Failed: $ErrorCount" -ForegroundColor Red

if ($ErrorCount -eq 0) {
    Write-Host "`n🎉 All linting checks passed!" -ForegroundColor Green
    exit 0
}
else {
    Write-Host "`n⚠️  Some linting checks failed. Please fix the issues above." -ForegroundColor Yellow
    Write-Host "`nTips:" -ForegroundColor Cyan
    Write-Host "  - Run 'python -m black src tests' to format code" -ForegroundColor Gray
    Write-Host "  - Run 'python -m isort src tests' to sort imports" -ForegroundColor Gray
    Write-Host "  - Add type hints to functions for mypy" -ForegroundColor Gray
    Write-Host "  - Fix style issues reported by flake8" -ForegroundColor Gray
    Write-Host "  - Fix dependency vulnerabilities reported by safety" -ForegroundColor Gray
    exit 1
} 