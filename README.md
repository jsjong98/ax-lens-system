# PwC AX Lens System

HR As-Is 프로세스의 **L5 Task**를 3단계 Knock-out 기준으로 **AI 수행 가능 / 인간 수행 필요** 로 자동 분류하는 풀스택 웹 애플리케이션입니다.

---

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| 백엔드 | Python 3.11+, FastAPI, uvicorn, OpenAI API |
| 프론트엔드 | Next.js 15, React, TypeScript, Tailwind CSS v4 |
| 데이터 처리 | openpyxl (Excel 읽기/쓰기) |

---

## 프로젝트 구조

```
.
├── backend/
│   ├── main.py              # FastAPI 엔트리포인트
│   ├── models.py            # Pydantic 데이터 모델
│   ├── llm_classifier.py   # LLM 분류 로직 (3단계 Knock-out)
│   ├── classifier.py        # 분류기 팩토리
│   ├── excel_reader.py      # Excel 파싱 (스마트 시트 감지)
│   ├── settings_store.py    # 설정 저장/로드
│   ├── requirements.txt     # Python 의존성
│   └── .env.example         # 환경변수 템플릿 (API Key)
├── frontend/
│   ├── app/                 # Next.js App Router 페이지
│   ├── components/          # 공통 UI 컴포넌트
│   └── lib/api.ts           # 백엔드 API 클라이언트
├── start.sh                 # macOS/Linux 원클릭 실행 스크립트
└── requirements.txt         # 루트 Python 의존성
```

---

## 빠른 시작

### 1. API 키 설정

```bash
cp backend/.env.example backend/.env
# backend/.env 파일을 열고 OPENAI_API_KEY 값을 입력하세요.
```

### 2. 실행 (macOS / Linux)

```bash
chmod +x start.sh
./start.sh
```

스크립트가 자동으로:
- Python 환경 탐지 (conda `nlp` → `base` → 시스템 python3)
- 백엔드 의존성 설치 (`pip install -r backend/requirements.txt`)
- 프론트엔드 의존성 설치 (`npm install`)
- 서버 2개 기동 후 브라우저 자동 열기

### 3. 수동 실행

```bash
# 터미널 1 — 백엔드
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# 터미널 2 — 프론트엔드
cd frontend
npm install
npm run dev
```

앱 주소: http://localhost:3000  
API 문서: http://localhost:8000/docs

---

## 사용 방법

1. **Task 목록** 탭에서 HR As-Is 엑셀 템플릿 `.xlsx` 파일을 업로드합니다.
2. **분류 실행** 탭에서 전체 또는 선택 Task를 분류합니다.
3. **결과 확인** 탭에서 결과를 검토하고 수동으로 수정하거나 Excel로 다운로드합니다.

---

## 분류 기준 (3단계 Knock-out)

| 단계 | 기준 | 해당 시 판정 |
|------|------|-------------|
| 1단계 | 규제 측면 (AI 기본법 · EU AI Act) | 인간 수행 필요 |
| 2단계 | 확정/승인 업무 (책임귀속성) | 인간 수행 필요 |
| 3단계 | 상호작용 업무 (관계·맥락·윤리) | 인간 수행 필요 |
| 통과 | 1~3단계 모두 해당 없음 | AI 수행 가능 |

---

## 로고 교체

기본 로고는 플레이스홀더 SVG입니다. 원하는 로고로 교체하려면:

```
frontend/public/strategyand-logo.svg   # 네비게이션 바 로고
frontend/public/pwc-logo.svg           # 브라우저 탭 파비콘
```

---

## 환경변수

`backend/.env` 파일 (`.env.example` 참고):

```env
OPENAI_API_KEY=sk-...
```
