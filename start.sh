#!/bin/bash
# start.sh — 백엔드(FastAPI) + 프론트엔드(Next.js) 동시 실행
# 사용: 터미널에서 ./start.sh  또는  더블클릭 실행

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  PwC AX Lens System"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  앱 주소  →  http://localhost:3000"
echo "  API 문서 →  http://localhost:8000/docs"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── Python 실행 경로 자동 탐색 ──────────────────────────
find_python() {
  # 1) conda nlp 환경 (이 프로젝트 권장 환경)
  local CONDA_NLP="/opt/homebrew/anaconda3/envs/nlp/bin/python"
  if [ -x "$CONDA_NLP" ] && "$CONDA_NLP" -c "import uvicorn, fastapi" 2>/dev/null; then
    echo "$CONDA_NLP"; return
  fi

  # 2) conda base 환경
  local CONDA_BASE="/opt/homebrew/anaconda3/bin/python"
  if [ -x "$CONDA_BASE" ] && "$CONDA_BASE" -c "import uvicorn, fastapi" 2>/dev/null; then
    echo "$CONDA_BASE"; return
  fi

  # 3) 시스템 python3
  for PY in python3 python; do
    if command -v "$PY" &>/dev/null && "$PY" -c "import uvicorn, fastapi" 2>/dev/null; then
      echo "$(command -v "$PY")"; return
    fi
  done

  echo ""
}

PYTHON=$(find_python)

if [ -z "$PYTHON" ]; then
  echo "❌  Python 환경을 찾을 수 없습니다."
  echo "   다음 명령어로 필요한 패키지를 설치하세요:"
  echo ""
  echo "   conda activate nlp"
  echo "   pip install fastapi uvicorn openpyxl openai python-multipart"
  echo ""
  exit 1
fi

echo "✓  Python: $PYTHON"

# ── Node.js / npm 확인 ──────────────────────────────────
if ! command -v npm &>/dev/null; then
  echo "❌  npm(Node.js)이 설치되지 않았습니다."
  echo "   https://nodejs.org 에서 LTS 버전을 설치해 주세요."
  exit 1
fi

echo "✓  Node.js: $(node -v)  /  npm: $(npm -v)"
echo ""

# ── 포트 정리 ───────────────────────────────────────────
for PORT in 8000 3000; do
  PID=$(lsof -ti:$PORT 2>/dev/null)
  if [ -n "$PID" ]; then
    kill $PID 2>/dev/null && echo "[정리] 포트 $PORT 기존 프로세스 종료 (PID $PID)"
  fi
done
sleep 1

# ── 프론트엔드 의존성 확인 ──────────────────────────────
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  echo "[프론트] node_modules 없음 → npm install 실행 중..."
  cd "$FRONTEND_DIR" && npm install --silent
fi

# ── 백엔드 시작 ─────────────────────────────────────────
echo "[백엔드] FastAPI 시작..."
cd "$BACKEND_DIR"
"$PYTHON" -m uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!

# 백엔드가 준비될 때까지 대기 (최대 10초)
echo -n "        연결 대기 중"
for i in $(seq 1 10); do
  sleep 1
  if curl -s http://localhost:8000/api/health &>/dev/null; then
    echo " → 완료!"
    break
  fi
  echo -n "."
done
echo ""

# ── 프론트엔드 시작 ─────────────────────────────────────
echo "[프론트] Next.js 시작..."
cd "$FRONTEND_DIR"
npm run dev &
FRONTEND_PID=$!

# 프론트엔드가 준비될 때까지 대기
echo -n "        연결 대기 중"
for i in $(seq 1 15); do
  sleep 1
  if curl -s http://localhost:3000 &>/dev/null; then
    echo " → 완료!"
    break
  fi
  echo -n "."
done
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅  실행 완료!"
echo "  👉  브라우저에서 http://localhost:3000 를 여세요."
echo "  종료하려면 이 창에서 Ctrl+C 를 누르세요."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 브라우저 자동 열기 (macOS)
if command -v open &>/dev/null; then
  sleep 1
  open "http://localhost:3000"
fi

# ── 종료 핸들러 ─────────────────────────────────────────
cleanup() {
  echo ""
  echo "종료 중..."
  kill $BACKEND_PID 2>/dev/null || true
  kill $FRONTEND_PID 2>/dev/null || true
  exit 0
}
trap cleanup SIGINT SIGTERM

wait
