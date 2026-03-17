$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Venv = Join-Path $Root ".aiplanner-venv"
$Python = Join-Path $Venv "Scripts\python.exe"
$TempDir = Join-Path $Root ".aiplanner-tmp"

if (-not (Test-Path $Python)) {
  py -3 -m venv $Venv
}

if (-not (Test-Path (Join-Path $Venv "Scripts\pip.exe"))) {
  py -3 -m venv --clear $Venv
}

$null = New-Item -ItemType Directory -Force -Path $TempDir
$env:TMP = $TempDir
$env:TEMP = $TempDir
& $Python -m pip install -e $Root
