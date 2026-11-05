$ErrorActionPreference = 'Stop'
$python = Join-Path $PSScriptRoot '..\.venv\Scripts\python.exe'
& $python (Join-Path $PSScriptRoot 'run.py')
