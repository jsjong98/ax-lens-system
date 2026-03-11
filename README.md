# PwC AX Lens System

HR As-Is 프로세스의 **L5 Task**를 3단계 Knock-out 기준으로  
**AI 수행 가능 / AI + Human / 인간 수행 필요** 세 가지 레이블로 자동 분류하는 풀스택 웹 애플리케이션입니다.

---

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| 백엔드 | Python 3.11+, FastAPI, uvicorn, OpenAI API (gpt-5.4) |
| 프론트엔드 | Next.js 15, React, TypeScript, Tailwind CSS v4 |
| 데이터 처리 | openpyxl (Excel 읽기/쓰기) |

---

## 프로젝트 구조

```
.
├── backend/
│   ├── main.py              # FastAPI 엔트리포인트
│   ├── models.py            # Pydantic 데이터 모델
│   ├── llm_classifier.py   # LLM 분류 로직 (3단계 Knock-out + AI+Human 판정)
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

### Windows (원클릭 설치)

> **최초 1회** — `SETUP.bat`을 더블클릭합니다.
> - Python 3.11, Node.js LTS가 없으면 **winget으로 자동 설치**합니다.
> - pip/npm 의존성 설치 + OpenAI API Key 설정까지 자동으로 진행됩니다.

```
SETUP.bat   ← 최초 1회 실행 (설치 + API Key 설정)
START.bat   ← 이후 매번 실행 (서버 기동 + 브라우저 자동 열기)
```

> **주의**: Windows 10/11에 `winget`이 내장되어 있어야 합니다.  
> 없는 경우 Python(<https://python.org>) 및 Node.js(<https://nodejs.org>)를 직접 설치 후 `SETUP.bat`을 실행하세요.

---

### macOS / Linux

```bash
chmod +x start.sh
./start.sh
```

스크립트가 자동으로:
- Python 환경 탐지 (conda `nlp` → `base` → 시스템 python3)
- 백엔드/프론트엔드 의존성 설치
- 서버 2개 기동 후 브라우저 자동 열기

---

### 수동 실행

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

## 분류 레이블

| 레이블 | 정의 |
|--------|------|
| **AI 수행 가능** | 3단계 Knock-out 기준 모두 해당 없음. 완전 자동화 대상 |
| **AI + Human** | Knock-out 기준 일부에 해당하나, 업무 내 AI 파트와 Human 파트가 명확히 분리 가능. To-be 설계 시 역할 분담 기준으로 활용 |
| **인간 수행 필요** | Knock-out 기준에 해당하며, AI 보조 파트가 분리되지 않는 Human 고유 업무 |

---

## 분류 기준

### Step 1 — 3단계 Knock-out

해당 항목이 하나라도 있으면 1차로 **"인간 수행 필요"** 판정

| 단계 | 기준 |
|------|------|
| 1단계 | 규제 측면 — AI 기본법·EU AI Act 금지 또는 고위험 AI 감독 의무 영역 |
| 2단계 | 확정/승인 업무 — 전사 정책 확정, 고영향·비가역 의사결정 |
| 3단계 | 상호작용 업무 — 공감·심리안전, 협상·중재, 공정성 설득, 변화/리더십, 창의적 설계 |

### Step 2 — AI + Human 판정

Knock-out 해당 시 추가 검토. 아래 패턴 중 하나에 해당하면 **"AI + Human"** 으로 분류

| 패턴 | 구조 | 핵심 신호 |
|------|------|-----------|
| **패턴 A** | 준비·정리는 AI / 판단·확정은 Human | "보고", "확인", "검토 후 반영", "협의", "논의" |
| **패턴 B** | 발송·취합은 AI / 대면 조율은 Human | "의견 수렴", "취합", "공유" → "조율", "합의", "공감대 형성" |
| **패턴 C** | 규칙 기반 처리는 AI / 예외·맥락 판단은 Human | "기준에 따라", "조건 설정 시", "원칙·규정이 합의된 경우" |

> AI + Human 판정 결과는 `hybrid_note` 필드에 `[패턴 X] AI 파트: ~~ / Human 파트: ~~` 형식으로 기록됩니다.

---

## 분석 입력 데이터

LLM은 각 Task를 분류할 때 아래 정보를 종합하여 업무 흐름을 재구성합니다.

| 항목 | 엑셀 열 |
|------|---------|
| L2 Major Process 명 | C열 |
| L3 Unit Process 명 | E열 |
| L4 Activity 명 | G열 |
| L4 Activity 설명 *(있는 경우)* | H열 |
| L5 Task 명 | J열 |
| L5 Task 설명 | K열 |
| 수행주체, Pain Point, Output 유형, 업무 판단 로직 | L~AE열 |

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
