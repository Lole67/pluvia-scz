$ErrorActionPreference = 'Stop'
$floodPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $floodPython -PathType Leaf)) {
    $floodPython = Join-Path $PSScriptRoot '..\.venv\Scripts\python.exe'
}
if (-not (Test-Path -LiteralPath $floodPython -PathType Leaf)) {
    throw 'No se encontro el entorno Python. Consulta README.md para instalarlo.'
}
& $floodPython (Join-Path $PSScriptRoot 'run.py')
exit $LASTEXITCODE
