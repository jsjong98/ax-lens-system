@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul 2>&1
title PwC AX Lens System - Setup

echo.
echo ============================================================
echo   PwC AX Lens System  ^|  Windows Setup
echo ============================================================
echo   This script installs all required components.
echo   Run this ONCE on a new machine, then use START.bat.
echo ============================================================
echo.

set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "FRONTEND=%ROOT%frontend"

REM ── Step 1: Check / Install Python ──────────────────────────
echo [1/5] Checking Python...
set PYTHON_CMD=
for %%c in (python py python3) do (
    if not defined PYTHON_CMD (
        %%c --version >nul 2>&1 && set PYTHON_CMD=%%c
    )
)

if not defined PYTHON_CMD (
    echo       Python not found. Installing via winget...
    winget install Python.Python.3.11 --silent --accept-source-agreements --accept-package-agreements >nul 2>&1
    if !ERRORLEVEL! NEQ 0 (
        echo.
        echo  [ERROR] Could not auto-install Python.
        echo  Please install manually: https://www.python.org/downloads/
        echo  IMPORTANT: Check "Add Python to PATH" during installation.
        echo.
        pause & exit /b 1
    )
    echo       Refreshing PATH...
    call :RefreshPath
    for %%c in (python py) do (
        if not defined PYTHON_CMD (
            %%c --version >nul 2>&1 && set PYTHON_CMD=%%c
        )
    )
    if not defined PYTHON_CMD (
        echo  [WARN] Python installed but not in PATH yet.
        echo  Please CLOSE this window and run SETUP.bat again.
        pause & exit /b 1
    )
)
for /f "tokens=*" %%v in ('!PYTHON_CMD! --version 2^>^&1') do echo       Found: %%v

REM ── Step 2: Check / Install Node.js ─────────────────────────
echo.
echo [2/5] Checking Node.js...
node --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo       Node.js not found. Installing via winget...
    winget install OpenJS.NodeJS.LTS --silent --accept-source-agreements --accept-package-agreements >nul 2>&1
    if !ERRORLEVEL! NEQ 0 (
        echo.
        echo  [ERROR] Could not auto-install Node.js.
        echo  Please install manually: https://nodejs.org/
        echo.
        pause & exit /b 1
    )
    call :RefreshPath
    node --version >nul 2>&1
    if !ERRORLEVEL! NEQ 0 (
        echo  [WARN] Node.js installed but not in PATH yet.
        echo  Please CLOSE this window and run SETUP.bat again.
        pause & exit /b 1
    )
)
for /f "tokens=*" %%v in ('node --version 2^>^&1') do echo       Found: Node.js %%v

REM ── Step 3: Install Python packages ─────────────────────────
echo.
echo [3/5] Installing Python packages (backend)...
!PYTHON_CMD! -m pip install --upgrade pip --quiet
!PYTHON_CMD! -m pip install -r "%BACKEND%\requirements.txt" --quiet
if %ERRORLEVEL% NEQ 0 (
    echo  [ERROR] pip install failed. Check your internet connection.
    pause & exit /b 1
)
echo       Done.

REM ── Step 4: Install Node packages ───────────────────────────
echo.
echo [4/5] Installing Node packages (frontend)...
if not exist "%FRONTEND%\node_modules" (
    pushd "%FRONTEND%"
    call npm install --silent
    if !ERRORLEVEL! NEQ 0 (
        echo  [ERROR] npm install failed.
        popd & pause & exit /b 1
    )
    popd
    echo       Done.
) else (
    echo       Already installed, skipping.
)

REM ── Step 5: OpenAI API Key setup ────────────────────────────
echo.
echo [5/5] Setting up OpenAI API Key...
if exist "%BACKEND%\.env" (
    echo       .env already exists, skipping key setup.
) else (
    copy "%BACKEND%\.env.example" "%BACKEND%\.env" >nul 2>&1
    echo.
    echo  ┌─────────────────────────────────────────────────┐
    echo  │  Enter your OpenAI API Key below.               │
    echo  │  It starts with  sk-...                         │
    echo  │  (Leave blank to skip — add manually later)     │
    echo  └─────────────────────────────────────────────────┘
    set /p "API_KEY=  API Key: "
    if not "!API_KEY!"=="" (
        echo OPENAI_API_KEY=!API_KEY!> "%BACKEND%\.env"
        echo       API Key saved to backend\.env
    ) else (
        echo       Skipped. Add your key to backend\.env later.
    )
)

REM ── Done ────────────────────────────────────────────────────
echo.
echo ============================================================
echo   Setup complete!
echo   Run START.bat to launch the application.
echo ============================================================
echo.
pause
exit /b 0

REM ── Refresh PATH from registry ──────────────────────────────
:RefreshPath
for /f "skip=2 tokens=3*" %%a in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "SYS_PATH=%%a %%b"
for /f "skip=2 tokens=3*" %%a in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "USR_PATH=%%a %%b"
set "PATH=!SYS_PATH!;!USR_PATH!"
exit /b 0
