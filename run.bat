@echo off
echo Starting Camera Comparison Application...
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python main.py
if %errorlevel% neq 0 (
    echo.
    echo Application exited with an error.
    pause
)
