@echo off
setlocal
cd /d "%~dp0..\Server-Python"
python -m compileall app
if errorlevel 1 exit /b 1
python -m app.self_check
if errorlevel 1 exit /b 1
python -m pytest
