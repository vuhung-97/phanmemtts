@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
cd /d "%~dp0"
set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"

rem ==========================================================================
rem  Build ban v3 modular: inject secret -> PyArmor -> PyInstaller -> manifest
rem
rem  build_v3.bat            -> build full vao dist\<APPNAME>
rem  build_v3.bat test       -> build thu vao build\dist_p4 (models = junction)
rem ==========================================================================

set "APPNAME=PhanMemChuyenDoiVanBanThanhGiongNoiTuNhien_v3"
set "PY=.venv\Scripts\python.exe"
set "PYARMOR=.venv\Scripts\pyarmor.exe"

set "MODE=full"
if /i "%~1"=="test" set "MODE=test"

if "%MODE%"=="test" (
    set "DISTPATH=build\dist_p4"
    set "WORKPATH=build\pyi_p4"
) else (
    set "DISTPATH=dist"
    set "WORKPATH=build\pyi"
)
set "DIST=%DISTPATH%\%APPNAME%"

echo.
echo [1/13] Kiem tra moi truong...
if not exist "%PY%" (
    echo [LOI] Khong thay %PY% - hay tao .venv va cai requirements.txt.
    exit /b 1
)
if not exist "%PYARMOR%" (
    echo [LOI] Khong thay PyArmor - chay: %PY% -m pip install pyarmor==9.2.8
    exit /b 1
)
if not exist "tools\license_tool\keys\license_secret.bin" (
    echo [LOI] Thieu secret: tools\license_tool\keys\license_secret.bin
    echo       Chay: %PY% tools\license_tool\gen_secret.py
    exit /b 1
)

echo [2/13] Chuan bi build\src...
if exist "build\src" rmdir /s /q "build\src"
for %%D in (core engine audio ui) do (
    robocopy "%%D" "build\src\%%D" /E /XD __pycache__ /NFL /NDL /NJH /NJS /NP >nul
)
copy /y "version.py" "build\src\version.py" >nul || exit /b 1
if exist "build\src\models" rmdir "build\src\models"

echo [3/13] Inject secret vao cay source tam...
"%PY%" tools\inject_secret.py build\src
if errorlevel 1 exit /b 1

echo [4/13] Kiem tra kich thuoc code / BOM...
"%PY%" tools\check_code_size.py build\src
if errorlevel 1 (
    echo [LOI] Source chua dat - dung build.
    exit /b 1
)

echo [5/13] Obfuscate bang PyArmor...
if exist "build\obf" rmdir /s /q "build\obf"
"%PYARMOR%" gen -O build\obf -r build\src
if errorlevel 1 (
    echo [LOI] PyArmor that bai.
    exit /b 1
)

echo [6/13] PyInstaller (OneDir, chi main.py + thu vien)...
"%PY%" -m PyInstaller --clean --noconfirm --distpath "%DISTPATH%" --workpath "%WORKPATH%" app_v3_modular.spec
if errorlevel 1 (
    echo [LOI] PyInstaller that bai.
    exit /b 1
)

echo [7/13] Copy code da obfuscate canh EXE...
for %%D in (core engine audio ui) do (
    if exist "%DIST%\%%D" rmdir /s /q "%DIST%\%%D"
    robocopy "build\obf\src\%%D" "%DIST%\%%D" /E /NFL /NDL /NJH /NJS /NP >nul
)
copy /y "build\obf\src\version.py" "%DIST%\version.py" >nul || exit /b 1
if exist "%DIST%\pyarmor_runtime_000000" rmdir /s /q "%DIST%\pyarmor_runtime_000000"
robocopy "build\obf\pyarmor_runtime_000000" "%DIST%\pyarmor_runtime_000000" /E /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 (
    echo [LOI] Copy pyarmor_runtime that bai.
    exit /b 1
)

echo [8/13] Models...
if "%MODE%"=="test" (
    if not exist "%DIST%\models" (
        cmd /c mklink /J "%DIST%\models" "%CD%\models" >nul
    )
) else (
    if exist "%DIST%\models\vieneu\hf_cache" (
        echo        [i] models da co - bo qua copy.
    ) else (
        robocopy "models" "%DIST%\models" /E /XD __pycache__ /NFL /NDL /NJH /NJS /NP >nul
        if errorlevel 8 (
            echo [LOI] Copy models that bai.
            exit /b 1
        )
    )
    "%PY%" packaging\make_full_voice_config.py "%DIST%\models\voice_config.json"
    if errorlevel 1 exit /b 1
)

echo [9/13] Copy HDSD / dieu khoan...
if exist "docs\Huong_dan_su_dung_V3_v3.0.0.docx" (
    copy /y "docs\Huong_dan_su_dung_V3_v3.0.0.docx" "%DIST%\HUONG_DAN_SU_DUNG.docx" >nul
) else (
    echo        [canh bao] Chua co HDSD v3 - chay docs\gen_hdsd_v3.py
)
if exist "packaging\HUONG_DAN_V3.txt" copy /y "packaging\HUONG_DAN_V3.txt" "%DIST%\HUONG_DAN_V3.txt" >nul
for %%F in (DIEU-KHOAN.md PRIVACY.md THIRD-PARTY-NOTICES.md) do (
    if exist "%%F" copy /y "%%F" "%DIST%\%%F" >nul
)

echo [10/13] Tao manifest.json...
"%PY%" tools\make_manifest.py --dist "%DIST%" --archive build\manifests
if errorlevel 1 exit /b 1

echo [11/13] Kiem tra bao mat ban phat hanh...
"%PY%" tools\check_release.py --dist "%DIST%"
if errorlevel 1 exit /b 1

echo [12/13] Tao goi cap nhat (neu co manifest ban truoc)...
"%PY%" tools\make_update_zip.py --dist "%DIST%" --archive build\manifests

echo [13/13] Don dep source tam (chua secret)...
if exist "build\src" rmdir /s /q "build\src"

echo.
echo [XONG] %DIST%
echo        Chay: "%DIST%\%APPNAME%.exe"
endlocal
exit /b 0
