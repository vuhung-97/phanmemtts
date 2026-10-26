@echo off
chcp 65001 >nul
title Cap nhat phan mem
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0capnhat.ps1" %*
if errorlevel 1 (
    echo.
    echo Cap nhat that bai. Xem thong bao loi phia tren.
    pause
)
