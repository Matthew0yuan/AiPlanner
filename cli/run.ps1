$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".aiplanner-venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
  & (Join-Path $PSScriptRoot "install.ps1")
}

& $Python -m aiplanner_cli
