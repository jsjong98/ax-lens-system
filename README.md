# PwC AX Lens System

**Process Innovation System** — AI 기반 업무 혁신 설계 플랫폼

Pain Point 분석부터 To-Be Workflow 설계, 벤치마킹, 과제 정의서/설계서 자동 생성까지
HR 업무 혁신의 전 과정을 지원하는 풀스택 웹 애플리케이션입니다.

> **Live**: [https://pwc-ax-lens.com](https://pwc-ax-lens.com)

---

## 핵심 기능

### 1. Task 분류 (AI / AI+Human / Human)
- HR As-Is 프로세스 엑셀 업로드 → LLM 기반 3단계 Knock-out 분류
- OpenAI / Anthropic 동시 지원, 결과 비교 가능
- 엑셀 다운로드 (`{원본파일명}_a_results.xlsx`)

### 2. New Workflow (To-Be 설계)
- **3단계 설계 프로세스**:
  - **1단계**: Pain Point 기반 AI Workflow 자동 설계 (직접 입력 또는 과제 엑셀 업로드)
  - **2단계**: 웹 벤치마킹 — 선도 기업 AI 적용 사례 검색 (Tavily API) → LLM이 Workflow 개선
  - **3단계**: 스윔레인 에디터에서 직접 편집 (Input → Senior AI → Junior AI → HR)
- **HR AX 프레임워크**: Human-on-the-Loop / Human-in-the-Loop / Human-Supervised
- **내보내기**: HTML (PwC 표준 AI Service Flow) / JSON

### 3. 과제 관리
- New Workflow 결과 기반 과제 정의서 자동 생성
- 과제 설계서 자동 생성 (AI Service Flow, 기술 스택, Agent 정의)
- PPT 내보내기

### 4. 기타
- 로그인/계정 관리 (비밀번호 변경, 이메일 인증번호 재설정)
- 파일별 결과 분리 저장 + 이전 프로젝트 불러오기
- Railway Volume 영구 저장

---

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| Backend | Python 3.12, FastAPI, uvicorn |
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS v4 |
| AI/LLM | OpenAI (GPT-5.4), Anthropic (Claude Sonnet 4.6) |
| 검색 | Tavily API (벤치마킹 심층 검색) |
| 이메일 | Resend API (비밀번호 재설정) |
| 배포 | Railway (Docker, Volume) |
| 도메인 | pwc-ax-lens.com |

---

## 프로젝트 구조

```
├── backend/
│   ├── main.py                    # FastAPI 엔트리포인트
│   ├── models.py                  # Pydantic 데이터 모델
│   ├── llm_classifier.py         # LLM 분류 (3단계 Knock-out)
│   ├── anthropic_classifier.py   # Anthropic Claude 분류기
│   ├── new_workflow_generator.py # New Workflow AI 설계
│   ├── benchmark_search.py       # 웹 벤치마킹 (Tavily/DuckDuckGo)
│   ├── project_definition_generator.py  # 과제 정의서
│   ├── project_design_generator.py     # 과제 설계서
│   ├── project_excel_reader.py   # 과제 엑셀 파서 (2행 병합 헤더)
│   ├── html_exporter.py          # AI Service Flow HTML 내보내기
│   ├── ppt_exporter.py           # PPT 내보내기
│   ├── auth_store.py             # 인증 (세션/비밀번호)
│   ├── data_store.py             # 파일별 영속 저장
│   ├── settings_store.py         # 설정 저장
│   ├── Dockerfile                # Railway 배포용
│   └── requirements.txt
├── frontend/
│   ├── app/                      # Next.js App Router
│   │   ├── login/                # 로그인
│   │   ├── tasks/                # Task 목록
│   │   ├── classify/             # 분류 실행
│   │   ├── results/              # 결과 확인
│   │   ├── new-workflow/         # New Workflow (1-2-3단계)
│   │   ├── project-management/   # 과제 관리
│   │   └── settings/             # 설정
│   ├── components/
│   │   ├── WorkflowEditor.tsx    # 스윔레인 에디터
│   │   ├── AuthProvider.tsx      # 인증 컨텍스트
│   │   └── ...
│   ├── lib/api.ts                # API 클라이언트
│   ├── Dockerfile                # Railway 배포용
│   └── package.json
└── README.md
```

---

## 배포 (Railway)

### 서비스 구성
- **Backend**: `backend/` → Dockerfile 빌드
- **Frontend**: `frontend/` → Dockerfile 빌드
- **Volume**: `/app/persist` (데이터 영구 저장)

### 환경변수 (Backend)

| 변수 | 설명 |
|------|------|
| `OPENAI_API_KEY` | OpenAI API 키 |
| `ANTHROPIC_API_KEY` | Anthropic API 키 |
| `TAVILY_API_KEY` | Tavily 검색 API 키 (벤치마킹) |
| `RESEND_API_KEY` | Resend 이메일 API 키 |
| `DEFAULT_USERS` | 초기 계정 (JSON 배열) |
| `ALLOWED_ORIGINS` | CORS 허용 도메인 |

### 환경변수 (Frontend)

| 변수 | 설명 |
|------|------|
| `NEXT_PUBLIC_BACKEND_URL` | Backend 공개 URL |
| `BACKEND_URL` | Backend 내부 URL (rewrites용) |

---

## 로컬 개발

```bash
# 백엔드
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# 프론트엔드
cd frontend
npm install
npm run dev
```

- 앱: http://localhost:3000
- API 문서: http://localhost:8000/docs

---

## HR AX 프레임워크

| 수준 | 설명 | 비율 목표 |
|------|------|----------|
| **Human-on-the-Loop** | Senior AI가 프로세스 전 영역 관리, Human은 감독·조율만 | 60~70% |
| **Human-in-the-Loop** | Junior AI가 일부 보조, Human이 의사결정·직접 개입 | 20~30% |
| **Human-out-of-the-Loop** | AI 자율 수행, Human 개입 최소 | 지향점 |
