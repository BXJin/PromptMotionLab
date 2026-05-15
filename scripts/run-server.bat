@echo off
setlocal
cd /d "%~dp0..\Server-Python"
python -m uvicorn app.main:app --reload --port 8010

