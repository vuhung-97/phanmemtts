@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set "APPNAME=PhanMemChuyenDoiVanBanThanhGiongNoiTuNhien_v3"
set "PY=.venv\Scripts\python.exe"

echo [1/5] Dong goi PyInstaller (OneDir)...
if not exist "%PY%" (
    echo [LOI] Khong tim thay %PY% - hay tao .venv va cai requirements.txt.
    exit /b 1
)
"%PY%" -m PyInstaller --clean --noconfirm app_v3.spec
if errorlevel 1 (
    echo [LOI] PyInstaller that bai.
    exit /b 1
)

echo [2/5] Copy models/ canh EXE (607MB, offline)...
robocopy "models" "dist\%APPNAME%\models" /E /NFL /NDL /NJH /NJS /NP /XD __pycache__ >nul
if errorlevel 8 (
    echo [LOI] Copy models that bai.
    exit /b 1
)

echo [3/5] Bat tat ca giong trong ban phat hanh...
"%PY%" packaging\make_full_voice_config.py "dist\%APPNAME%\models\voice_config.json"
if errorlevel 1 (
    echo [LOI] Sinh voice_config.json that bai.
    exit /b 1
)

echo [4/5] Copy HDSD...
if not exist "docs\Huong_dan_su_dung_V3_v3.0.0.docx" (
    echo [LOI] Chua co HDSD v3 - hay chay: .venv\Scripts\python.exe docs\gen_hdsd_v3.py
    exit /b 1
)
copy /y "docs\Huong_dan_su_dung_V3_v3.0.0.docx" "dist\%APPNAME%\HUONG_DAN_SU_DUNG.docx" >nul

echo [5/5] Tao file HUONG_DAN_V3.txt...
copy /y "packaging\HUONG_DAN_V3.txt" "dist\%APPNAME%\HUONG_DAN_V3.txt" >nul

echo.
echo [XONG] Ban phat hanh tai: dist\%APPNAME%\
echo        Chay: dist\%APPNAME%\%APPNAME%.exe
endlocal
