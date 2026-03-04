@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul 2>&1
title PwC AX Lens System

echo.
echo ============================================================
echo   PwC AX Lens System  ^|  Starting...
echo ============================================================
echo.

set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "FRONTEND=%ROOT%frontend"

REM ── Prerequisite checks ─────────────────────────────────────
set PYTHON_CMD=
for %%c in (python py python3) do (
    if not defined PYTHON_CMD (
        %%c --version >nul 2>&1 && set PYTHON_CMD=%%c
    )
)
if not defined PYTHON_CMD (
    echo  [ERROR] Python not found. Please run SETUP.bat first.
    pause & exit /b 1
)

node --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  [ERROR] Node.js not found. Please run SETUP.bat first.
    pause & exit /b 1
)

if not exist "%FRONTEND%\node_modules" (
    echo  [ERROR] Node modules not installed. Please run SETUP.bat first.
    pause & exit /b 1
)

if not exist "%BACKEND%\.env" (
    echo  [WARN] backend\.env not found.
    echo         Classification will not work without an OpenAI API Key.
    echo         Run SETUP.bat or create backend\.env manually.
    echo.
    timeout /t 4 >nul
)

REM ── Stop any existing processes on ports 8000 / 3000 ────────
echo  Stopping any existing servers on ports 8000 and 3000...
for /f "tokens=5" %%p in ('netstat -aon 2^>nul ^| findstr ":8000 "') do (
    taskkill /PID %%p /F >nul 2>&1
)
for /f "tokens=5" %%p in ('netstat -aon 2^>nul ^| findstr ":3000 "') do (
    taskkill /PID %%p /F >nul 2>&1
)
timeout /t 1 >nul

REM ── Find uvicorn ─────────────────────────────────────────────
set UVICORN_CMD=
!PYTHON_CMD! -m uvicorn --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "UVICORN_CMD=!PYTHON_CMD! -m uvicorn"
) else (
    where uvicorn >nul 2>&1
    if %ERRORLEVEL% EQU 0 set UVICORN_CMD=uvicorn
)
if not defined UVICORN_CMD (
    echo  [ERROR] uvicorn not found. Run SETUP.bat to install dependencies.
    pause & exit /b 1
)

REM ── Start Backend ────────────────────────────────────────────
echo  Starting backend  (http://localhost:8000) ...
start "PwC-Backend" /min cmd /c "cd /d "%BACKEND%" && !UVICORN_CMD! main:app --host 0.0.0.0 --port 8000 2>&1"

REM ── Wait for backend ─────────────────────────────────────────
echo  Waiting for backend to be ready...
set RETRY=0
:wait_backend
timeout /t 2 >nul
curl -s http://localhost:8000/api/health >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    set /a RETRY+=1
    if !RETRY! LSS 15 (
        echo  .  retrying (!RETRY!/15)
        goto wait_backend
    )
    echo  [WARN] Backend did not respond in time. Continuing anyway...
)
echo  Backend ready.

REM ── Start Frontend ───────────────────────────────────────────
echo  Starting frontend (http://localhost:3000) ...
start "PwC-Frontend" /min cmd /c "cd /d "%FRONTEND%" && npm run dev 2>&1"

REM ── Wait for frontend ────────────────────────────────────────
echo  Waiting for frontend to be ready...
set RETRY=0
:wait_frontend
timeout /t 3 >nul
curl -s http://localhost:3000 >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    set /a RETRY+=1
    if !RETRY! LSS 15 (
        echo  .  retrying (!RETRY!/15)
        goto wait_frontend
    )
    echo  [WARN] Frontend did not respond in time. Opening browser anyway...
)
echo  Frontend ready.

REM ── Open browser ─────────────────────────────────────────────
echo.
echo ============================================================
echo   App running at  http://localhost:3000
echo   API docs:        http://localhost:8000/docs
echo.
echo   Close the two minimized windows to stop the servers.
echo ============================================================
echo.
start "" "http://localhost:3000"

pause
exit /b 0
