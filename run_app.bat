@echo off
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [LOI] Khong tim thay moi truong ao .venv trong thu muc nay.
    echo       Hay chay: python -m venv .venv  va  pip install -r requirements.txt
    pause
    exit /b 1
)

".venv\Scripts\python.exe" main.py
