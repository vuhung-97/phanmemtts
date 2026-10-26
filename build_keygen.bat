@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"

set "PY=.venv\Scripts\python.exe"
set "OUT=dist\KeygenTTS"
set "SECRET=tools\license_tool\keys\license_secret.bin"

echo.
echo [1/6] Kiem tra moi truong...
if not exist "%PY%" (
    echo [LOI] Khong thay %PY%
    exit /b 1
)
if not exist "%SECRET%" (
    echo [LOI] Thieu secret: %SECRET%
    echo       Chep tu ban backup vao truoc khi build.
    exit /b 1
)

echo [2/6] Tao icon tu logo...
"%PY%" tools\license_tool\make_icon.py
if errorlevel 1 exit /b 1

echo [3/6] PyInstaller (one-file)...
"%PY%" -m PyInstaller --clean --noconfirm --distpath build\dist_keygen --workpath build\pyi_keygen tools\license_tool\keygen.spec
if errorlevel 1 (
    echo [LOI] PyInstaller that bai.
    exit /b 1
)

echo [4/6] Dong goi thu muc phat hanh (giu nguyen so key cu)...
if not exist "%OUT%" mkdir "%OUT%"
if not exist "%OUT%\keys" mkdir "%OUT%\keys"
move /y "build\dist_keygen\KeygenTTS.exe" "%OUT%\KeygenTTS.exe" >nul || exit /b 1
copy /y "%SECRET%" "%OUT%\keys\license_secret.bin" >nul || exit /b 1
if not exist "%OUT%\keys\issued.sqlite" (
    if exist "tools\license_tool\keys\issued.sqlite" (
        copy /y "tools\license_tool\keys\issued.sqlite" "%OUT%\keys\issued.sqlite" >nul
    )
)
if exist "docs\HUONG_DAN_CAP_KEY.md" copy /y "docs\HUONG_DAN_CAP_KEY.md" "%OUT%\" >nul

echo [5/6] Kiem tra secret khong lot vao exe...
"%PY%" tools\license_tool\check_release.py "%OUT%"
if errorlevel 1 exit /b 1

echo [6/6] Tu kiem tra ban exe (sinh ma thu)...
"%OUT%\KeygenTTS.exe" --selftest "%OUT%\keygen_selftest.txt"
"%PY%" tools\license_tool\check_release.py "%OUT%" --selftest "%OUT%\keygen_selftest.txt"
if errorlevel 1 exit /b 1
del /q "%OUT%\keygen_selftest.txt" >nul 2>&1

echo.
echo [XONG] %OUT%\KeygenTTS.exe
echo        Thu muc: %OUT%\ (gom keys\license_secret.bin)
endlocal
exit /b 0
