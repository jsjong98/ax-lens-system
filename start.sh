#!/bin/bash
# start.sh — Launch backend (FastAPI) + frontend (Next.js) in one shot
# Usage: ./start.sh   or double-click in Finder (set executable first: chmod +x start.sh)

set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

echo ""
echo "============================================================"
echo "  PwC AX Lens  |  Starting..."
echo "  App  ->  http://localhost:3000"
echo "  API  ->  http://localhost:8000/docs"
echo "============================================================"
echo ""

# ── Locate Python with uvicorn + fastapi ─────────────────────
find_python() {
  local CANDIDATES=(
    "/opt/homebrew/anaconda3/envs/nlp/bin/python"
    "/opt/homebrew/anaconda3/bin/python"
    "/Users/$USER/anaconda3/envs/nlp/bin/python"
    "/Users/$USER/miniconda3/envs/nlp/bin/python"
  )
  for PY in "${CANDIDATES[@]}"; do
    if [ -x "$PY" ] && "$PY" -c "import uvicorn, fastapi" 2>/dev/null; then
      echo "$PY"; return
    fi
  done
  # fallback: any python3 in PATH that has uvicorn
  for PY in python3 python; do
    if command -v "$PY" &>/dev/null && "$PY" -c "import uvicorn, fastapi" 2>/dev/null; then
      echo "$(command -v "$PY")"; return
    fi
  done
  echo ""
}

PYTHON=$(find_python)

if [ -z "$PYTHON" ]; then
  echo "[ERROR] Python environment with uvicorn/fastapi not found."
  echo "        Run: conda activate nlp"
  echo "        Then: pip install fastapi uvicorn openpyxl openai anthropic python-multipart"
  exit 1
fi
echo "[OK] Python : $PYTHON"

# ── Check Node / npm ─────────────────────────────────────────
if ! command -v npm &>/dev/null; then
  echo "[ERROR] Node.js / npm not found. Install from https://nodejs.org"
  exit 1
fi
echo "[OK] Node.js: $(node -v)  /  npm: $(npm -v)"
echo ""

# ── Kill any existing processes on 8000 / 3000 ───────────────
for PORT in 8000 3000; do
  PIDS=$(lsof -ti:$PORT 2>/dev/null || true)
  if [ -n "$PIDS" ]; then
    echo "[CLEAN] Killing existing process on port $PORT (PID $PIDS)"
    kill $PIDS 2>/dev/null || true
  fi
done
sleep 1

# ── Install frontend dependencies if missing ──────────────────
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  echo "[SETUP] node_modules not found — running npm install..."
  cd "$FRONTEND_DIR" && npm install --silent
fi

# ── Start backend ─────────────────────────────────────────────
echo "[BACKEND]  Starting FastAPI on :8000 ..."
cd "$BACKEND_DIR"
"$PYTHON" -m uvicorn main:app --reload --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

echo -n "           Waiting for backend"
for i in $(seq 1 15); do
  sleep 1
  if curl -sf http://localhost:8000/api/health &>/dev/null; then
    echo " -> OK"
    break
  fi
  echo -n "."
  if [ "$i" -eq 15 ]; then echo " [WARN] backend slow to start"; fi
done
echo ""

# ── Start frontend ────────────────────────────────────────────
# --hostname localhost avoids uv_interface_addresses error on macOS
echo "[FRONTEND] Starting Next.js on :3000 ..."
cd "$FRONTEND_DIR"
npx next dev --hostname localhost --port 3000 &
FRONTEND_PID=$!

echo -n "           Waiting for frontend"
for i in $(seq 1 20); do
  sleep 1
  if curl -sf http://localhost:3000 &>/dev/null; then
    echo " -> OK"
    break
  fi
  echo -n "."
  if [ "$i" -eq 20 ]; then echo " [WARN] frontend slow to start"; fi
done
echo ""

# ── Open browser ──────────────────────────────────────────────
if command -v open &>/dev/null; then
  open "http://localhost:3000"
fi

echo "============================================================"
echo "  App is running at http://localhost:3000"
echo "  Press Ctrl+C to stop all servers."
echo "============================================================"
echo ""

# ── Cleanup on exit ───────────────────────────────────────────
cleanup() {
  echo ""
  echo "Shutting down..."
  kill $BACKEND_PID  2>/dev/null || true
  kill $FRONTEND_PID 2>/dev/null || true
  # also kill child processes (uvicorn reloader spawns sub-processes)
  pkill -f "uvicorn main:app" 2>/dev/null || true
  pkill -f "next dev"         2>/dev/null || true
  exit 0
}
trap cleanup SIGINT SIGTERM

wait
