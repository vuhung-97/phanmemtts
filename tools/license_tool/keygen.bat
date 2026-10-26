@echo off
chcp 65001 >nul
cd /d "%~dp0..\.."

if not exist ".venv\Scripts\pythonw.exe" (
    echo [LOI] Khong thay .venv\Scripts\pythonw.exe
    echo Hay tao .venv va cai requirements.txt truoc.
    pause
    exit /b 1
)

start "" ".venv\Scripts\pythonw.exe" "tools\license_tool\keygen.pyw"
