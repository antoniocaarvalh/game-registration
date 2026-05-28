@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Game Registration - Instalação

echo ============================================
echo   Game Registration - Instalação inicial
echo ============================================
echo.

:: Verifica Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [!] Python nao encontrado no sistema.
    echo [!] Abrindo pagina de download do Python...
    start https://www.python.org/downloads/
    echo.
    echo Instale o Python marcando a opcao "Add Python to PATH"
    echo e execute este setup.bat novamente.
    pause
    exit /b 1
)

for /f "tokens=*" %%v in ('python --version') do echo [OK] %%v encontrado.
echo.
echo [*] Instalando dependencias...
python -m pip install --upgrade pip >nul 2>&1
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ERRO] Falha ao instalar dependencias.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Instalacao concluida com sucesso!
echo   Execute run.bat para abrir o app.
echo ============================================
pause
