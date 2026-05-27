@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Game Registration

:: Verifica dependências rapidamente
python -c "import streamlit, pandas, plotly, webview" >nul 2>&1
if errorlevel 1 (
    echo [!] Dependencias nao instaladas.
    echo [!] Execute setup.bat primeiro.
    pause
    exit /b 1
)

echo Iniciando Game Registration...
python launcher.py
