@echo off
setlocal
set ROOT=%~dp0..
set VENV=%ROOT%\.aiplanner-venv
set PYTHON=%VENV%\Scripts\python.exe
set TMPDIR=%ROOT%\.aiplanner-tmp

if not exist "%PYTHON%" (
  py -3 -m venv "%VENV%"
)

if not exist "%VENV%\Scripts\pip.exe" (
  py -3 -m venv --clear "%VENV%"
)

if not exist "%TMPDIR%" mkdir "%TMPDIR%"
set TMP=%TMPDIR%
set TEMP=%TMPDIR%
"%PYTHON%" -m pip install -e "%ROOT%"
