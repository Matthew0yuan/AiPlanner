@echo off
setlocal
set ROOT=%~dp0..
set PYTHON=%ROOT%\.aiplanner-venv\Scripts\python.exe

if not exist "%PYTHON%" (
  call "%~dp0install.cmd"
)

"%PYTHON%" -m aiplanner_cli
