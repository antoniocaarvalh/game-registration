@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Game Registration

:: Verifica Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Python nao encontrado. Abrindo pagina de download...
    start https://www.python.org/downloads/
    echo.
    echo Instale o Python marcando "Add Python to PATH" e abra este arquivo novamente.
    pause
    exit /b 1
)

:: Instala dependencias se necessario
python -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo Instalando dependencias pela primeira vez...
    python -m pip install streamlit pandas plotly requests pywebview --quiet
)

:: Inicia o app
echo Abrindo Game Registration...
python launcher.py
