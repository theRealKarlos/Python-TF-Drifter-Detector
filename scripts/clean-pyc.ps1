# PowerShell script to clean Python bytecode
Get-ChildItem -Path . -Include __pycache__, *.pyc -Recurse | Remove-Item -Recurse -Force
Write-Host "All __pycache__ folders and .pyc files have been deleted." 