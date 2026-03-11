@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul 2>&1
title PwC AX Lens

echo.
echo ============================================================
echo   PwC AX Lens  ^|  Starting...
echo   App  -^>  http://localhost:3000
echo   API  -^>  http://localhost:8000/docs
echo ============================================================
echo.

set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "FRONTEND=%ROOT%frontend"

REM ── Check Python ─────────────────────────────────────────────
set PYTHON_CMD=
for %%c in (python py python3) do (
    if not defined PYTHON_CMD (
        %%c -c "import uvicorn, fastapi" >nul 2>&1 && set PYTHON_CMD=%%c
    )
)
if not defined PYTHON_CMD (
    echo [ERROR] Python with uvicorn/fastapi not found.
    echo         Run SETUP.bat or:  pip install fastapi uvicorn openpyxl openai anthropic python-multipart
    pause & exit /b 1
)
echo [OK] Python : !PYTHON_CMD!

REM ── Check Node.js ────────────────────────────────────────────
node --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Node.js not found. Install from https://nodejs.org
    pause & exit /b 1
)
for /f "tokens=*" %%v in ('node -v 2^>nul') do echo [OK] Node.js: %%v
echo.

REM ── Kill existing processes on 8000 / 3000 ───────────────────
echo [CLEAN] Stopping any existing servers...
for /f "tokens=5" %%p in ('netstat -aon 2^>nul ^| findstr ":8000 "') do taskkill /PID %%p /F >nul 2>&1
for /f "tokens=5" %%p in ('netstat -aon 2^>nul ^| findstr ":3000 "') do taskkill /PID %%p /F >nul 2>&1
timeout /t 1 >nul

REM ── Check frontend node_modules ──────────────────────────────
if not exist "%FRONTEND%\node_modules" (
    echo [SETUP] node_modules not found - running npm install...
    cd /d "%FRONTEND%" && npm install --silent
)

REM ── Start Backend ────────────────────────────────────────────
echo [BACKEND]  Starting FastAPI on :8000 ...
start "PwC-Backend" /min cmd /c "cd /d "%BACKEND%" && !PYTHON_CMD! -m uvicorn main:app --reload --host 127.0.0.1 --port 8000"

REM ── Wait for backend ─────────────────────────────────────────
set RETRY=0
:wait_backend
timeout /t 2 >nul
curl -sf http://localhost:8000/api/health >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    set /a RETRY+=1
    if !RETRY! LSS 15 (
        echo            . retrying (!RETRY!/15)
        goto wait_backend
    )
    echo [WARN] Backend slow to start. Continuing anyway...
) else (
    echo            -^> OK
)
echo.

REM ── Start Frontend ───────────────────────────────────────────
echo [FRONTEND] Starting Next.js on :3000 ...
start "PwC-Frontend" /min cmd /c "cd /d "%FRONTEND%" && npx next dev --hostname localhost --port 3000"

REM ── Wait for frontend ────────────────────────────────────────
set RETRY=0
:wait_frontend
timeout /t 3 >nul
curl -sf http://localhost:3000 >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    set /a RETRY+=1
    if !RETRY! LSS 15 (
        echo            . retrying (!RETRY!/15)
        goto wait_frontend
    )
    echo [WARN] Frontend slow to start. Opening browser anyway...
) else (
    echo            -^> OK
)
echo.

REM ── Open browser ─────────────────────────────────────────────
echo ============================================================
echo   App is running at  http://localhost:3000
echo   Close the two minimized windows to stop the servers.
echo ============================================================
echo.
start "" "http://localhost:3000"

pause
exit /b 0
