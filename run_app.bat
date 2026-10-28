@echo off
rem ==========================================================================
rem  Khoi dong nhanh ban dev (tu source)
rem
rem  - Nhay dup file nay: app mo truc tiep, khong hien cua so console.
rem  - Xem log/loi:       run_app.bat debug
rem  - Truyen tham so:    run_app.bat debug --help
rem ==========================================================================
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set "PYW=.venv\Scripts\pythonw.exe"
set "PY=.venv\Scripts\python.exe"

if not exist "main.py" goto no_main
if not exist "%PY%" goto no_venv
if /i "%~1"=="debug" goto debug

if not exist "%PYW%" set "PYW=%PY%"

if not exist "models\vieneu\hf_cache" echo [canh bao] Khong thay models\vieneu\hf_cache - app se bao thieu model.

rem start "" -> tra quyen dieu khien lai ngay; dong .bat khong tat app.
start "" "%PYW%" "main.py" %*
exit /b 0

:debug
shift
echo [dev] Chay co console: "%PY%" main.py %*
"%PY%" "main.py" %*
echo.
echo [dev] App da thoat, exit=%ERRORLEVEL%
pause
exit /b 0

:no_main
echo [LOI] Khong thay main.py - hay dat file nay trong thu muc goc cua du an.
pause
exit /b 1

:no_venv
echo [LOI] Chua co moi truong .venv.
echo       Tao bang:  python -m venv .venv
echo                  .venv\Scripts\python.exe -m pip install -r requirements.txt
pause
exit /b 1
