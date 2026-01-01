@echo off
setlocal
cd /d %~dp0\..
if not exist .venv\Scripts\activate (
  echo Virtual environment not found. Run scripts\install_env.bat first.
  exit /b 1
)
call .venv\Scripts\activate
set PYTHONPATH=%cd%
uvicorn main:app --host 0.0.0.0 --port 8000
