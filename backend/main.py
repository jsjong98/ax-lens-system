"""
main.py — FastAPI 애플리케이션 엔트리포인트

실행:
  uvicorn main:app --reload --port 8000
"""
from __future__ import annotations
import asyncio
import io
import json
import os
import shutil
from pathlib import Path
from typing import Optional


def _natural_key(s: str) -> list[int | str]:
    """자연수 정렬 키: '1.1.1.2' < '1.1.1.10' 순서를 보장합니다."""
    import re
    return [int(c) if c.isdigit() else c for c in re.split(r'(\d+)', s)]

# .env 파일 자동 로드 (python-dotenv 없어도 동작하는 fallback 포함)
def _load_dotenv() -> None:
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path, override=False)
    except ImportError:
        for line in env_path.read_text("utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                key = key.strip()
                if key and key not in os.environ:
                    os.environ[key] = val.strip()

_load_dotenv()

from fastapi import FastAPI, HTTPException, Query, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment

from classifier import get_classifier
from excel_reader import load_tasks
from models import (
    ClassificationResult,
    ClassificationResultUpdate,
    ClassifierSettings,
    ClassifyRequest,
    ResultsResponse,
    StatsResponse,
    Task,
    TaskListResponse,
)
from settings_store import (
    clear_results,
    load_results,
    load_settings,
    save_results,
    save_settings,
    set_current_file,
    upsert_result,
)
from usage_store import get_usage, reset_usage
from auth_store import (
    init_default_users,
    authenticate,
    get_session_user,
    change_password,
    logout,
    generate_reset_code,
    verify_reset_code,
    reset_password,
    send_reset_email,
)
from data_store import (
    save_data, load_data, clear_data, get_saved_status,
    set_current_project, get_current_project, list_projects, save_meta,
)

# ── 앱 초기화 ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="PwC AX Lens — Process Innovation API",
    description="AI 기반 업무 혁신 설계 플랫폼",
    version="2.0.0",
)

# CORS: ALLOWED_ORIGINS 환경변수 + Railway 도메인 자동 허용
_default_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
_extra_origins = [
    o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()
]
_all_origins = _default_origins + _extra_origins

# Railway 배포 환경이면 모든 .up.railway.app 도메인 허용
_is_railway = bool(os.getenv("RAILWAY_ENVIRONMENT"))
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _is_railway else _all_origins,
    allow_credentials=True if not _is_railway else False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 기본 사용자 초기화 ─────────────────────────────────────────────────────────
init_default_users()

# ── 인증 엔드포인트 ──────────────────────────────────────────────────────────

from pydantic import BaseModel as _BaseModel


class _LoginRequest(_BaseModel):
    email: str
    password: str


class _ChangePasswordRequest(_BaseModel):
    old_password: str
    new_password: str


@app.post("/api/auth/login", tags=["Auth"])
async def api_login(body: _LoginRequest):
    token = authenticate(body.email, body.password)
    if not token:
        raise HTTPException(401, "이메일 또는 비밀번호가 올바르지 않습니다.")
    user = get_session_user(token)
    return {"ok": True, "token": token, "user": user}


@app.get("/api/auth/me", tags=["Auth"])
async def api_me(request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    user = get_session_user(token)
    if not user:
        raise HTTPException(401, "인증이 필요합니다.")
    return {"ok": True, "user": user}


@app.post("/api/auth/change-password", tags=["Auth"])
async def api_change_password(body: _ChangePasswordRequest, request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    user = get_session_user(token)
    if not user:
        raise HTTPException(401, "인증이 필요합니다.")
    ok = change_password(user["email"], body.old_password, body.new_password)
    if not ok:
        raise HTTPException(400, "기존 비밀번호가 올바르지 않습니다.")
    return {"ok": True}


@app.post("/api/auth/logout", tags=["Auth"])
async def api_logout(request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    logout(token)
    return {"ok": True}


class _ResetRequestBody(_BaseModel):
    email: str


class _ResetVerifyBody(_BaseModel):
    email: str
    code: str


class _ResetPasswordBody(_BaseModel):
    email: str
    code: str
    new_password: str


@app.post("/api/auth/reset/request", tags=["Auth"])
async def api_reset_request(body: _ResetRequestBody):
    """비밀번호 재설정 인증번호를 이메일로 발송합니다."""
    code = generate_reset_code(body.email)
    if not code:
        raise HTTPException(404, "등록되지 않은 이메일입니다. 관리자에게 문의해 주세요.")
    sent = await send_reset_email(body.email, code)
    if not sent:
        raise HTTPException(500, "이메일 발송에 실패했습니다. 잠시 후 다시 시도해 주세요.")
    return {"ok": True, "message": "인증번호가 이메일로 발송되었습니다."}


@app.post("/api/auth/reset/verify", tags=["Auth"])
async def api_reset_verify(body: _ResetVerifyBody):
    """인증번호를 검증합니다."""
    valid = verify_reset_code(body.email, body.code)
    if not valid:
        raise HTTPException(400, "인증번호가 올바르지 않거나 만료되었습니다.")
    return {"ok": True}


@app.post("/api/auth/reset/confirm", tags=["Auth"])
async def api_reset_confirm(body: _ResetPasswordBody):
    """인증번호 확인 후 새 비밀번호를 설정합니다."""
    ok = reset_password(body.email, body.code, body.new_password)
    if not ok:
        raise HTTPException(400, "인증번호가 올바르지 않거나 만료되었습니다.")
    return {"ok": True, "message": "비밀번호가 재설정되었습니다."}


# ── 인메모리 Task 캐시 ────────────────────────────────────────────────────────
_tasks_cache: list[Task] = []


# ── 영속 저장 헬퍼 ──────────────────────────────────────────────────────────

def _persist_cache(key: str, cache: dict) -> None:
    """캐시 데이터를 JSON 파일로 영속 저장합니다."""
    save_data(key, dict(cache))


def _restore_cache(key: str, cache: dict) -> None:
    """서버 시작 시 JSON 파일에서 캐시를 복원합니다."""
    data = load_data(key)
    if data and isinstance(data, dict):
        cache.update(data)
        print(f"[data_store] '{key}' 복원 완료 ({len(data)} keys)")


# 데이터 저장 상태 확인 API
@app.get("/api/data-status", tags=["Data"])
async def get_data_status():
    """각 단계별 데이터 저장 상태를 반환합니다."""
    return {
        "ok": True,
        "current_project": get_current_project(),
        "tasks_loaded": len(_tasks_cache) > 0,
        "saved": get_saved_status(),
    }


@app.delete("/api/data/reset-all", tags=["Data"])
async def reset_all_data():
    """모든 데이터를 초기화합니다 (Volume 포함)."""
    import shutil
    # 인메모리 캐시 초기화
    _new_workflow_cache.clear()
    _project_definition_cache.clear()
    _project_design_cache.clear()
    _nw_tasks_cache.clear()
    _nw_projects_cache.clear()
    # Volume 데이터 삭제
    data_dir = _PERSIST_ROOT / "data"
    if data_dir.exists():
        shutil.rmtree(data_dir, ignore_errors=True)
        data_dir.mkdir(exist_ok=True)
    results_dir = _PERSIST_ROOT / "results"
    if results_dir.exists():
        shutil.rmtree(results_dir, ignore_errors=True)
        results_dir.mkdir(exist_ok=True)
    uploads_dir = _PERSIST_ROOT / "uploads"
    if uploads_dir.exists():
        shutil.rmtree(uploads_dir, ignore_errors=True)
        uploads_dir.mkdir(exist_ok=True)
    for f in ["current_project.json", "new_workflow_result.json", "project_definition.json", "project_design.json"]:
        p = _PERSIST_ROOT / f
        if p.exists():
            p.unlink(missing_ok=True)
    return {"ok": True, "message": "모든 데이터가 초기화되었습니다."}


@app.get("/api/projects", tags=["Data"])
async def get_project_list():
    """저장된 모든 프로젝트(파일) 목록을 반환합니다."""
    return {"ok": True, "projects": list_projects()}


@app.post("/api/projects/load", tags=["Data"])
async def load_project(request: Request):
    """이전 프로젝트의 결과를 로드합니다."""
    body = await request.json()
    filename = body.get("filename", "")
    if not filename:
        raise HTTPException(400, "파일명이 필요합니다.")

    set_current_project(filename)

    # 저장된 결과 로드
    loaded = {}

    nw_data = load_data("new_workflow_result", filename)
    if nw_data:
        _new_workflow_cache.clear()
        _new_workflow_cache.update(nw_data)
        loaded["new_workflow"] = True

    pd_data = load_data("project_definition", filename)
    if pd_data:
        _project_definition_cache.clear()
        _project_definition_cache.update(pd_data)
        loaded["project_definition"] = True

    pds_data = load_data("project_design", filename)
    if pds_data:
        _project_design_cache.clear()
        _project_design_cache.update(pds_data)
        loaded["project_design"] = True

    return {
        "ok": True,
        "filename": filename,
        "loaded": loaded,
        "saved": get_saved_status(filename),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Task 엔드포인트
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/tasks", response_model=TaskListResponse, tags=["Tasks"])
async def get_tasks(
    search: Optional[str] = Query(None),
    l2: Optional[str] = Query(None),
    l3: Optional[str] = Query(None),
    l4: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=10000),
):
    tasks = _tasks_cache

    if search:
        q = search.lower()
        tasks = [
            t for t in tasks
            if q in t.name.lower()
            or q in t.description.lower()
            or q in t.performer.lower()
        ]
    if l2:
        tasks = [t for t in tasks if t.l2 == l2]
    if l3:
        tasks = [t for t in tasks if t.l3 == l3]
    if l4:
        tasks = [t for t in tasks if t.l4 == l4]

    total = len(tasks)
    start = (page - 1) * page_size
    tasks = tasks[start : start + page_size]

    return TaskListResponse(total=total, tasks=tasks)


@app.get("/api/tasks/filters", tags=["Tasks"])
async def get_filter_options():
    l2_set: dict[str, str] = {}
    l3_set: dict[str, str] = {}
    l4_set: dict[str, str] = {}

    for t in _tasks_cache:
        l2_set[t.l2_id] = t.l2
        l3_set[t.l3_id] = t.l3
        l4_set[t.l4_id] = t.l4

    return {
        "l2": [{"id": k, "name": v} for k, v in sorted(l2_set.items(), key=lambda x: _natural_key(x[0]))],
        "l3": [{"id": k, "name": v} for k, v in sorted(l3_set.items(), key=lambda x: _natural_key(x[0]))],
        "l4": [{"id": k, "name": v} for k, v in sorted(l4_set.items(), key=lambda x: _natural_key(x[0]))],
    }


@app.get("/api/tasks/{task_id}", response_model=Task, tags=["Tasks"])
async def get_task(task_id: str):
    for t in _tasks_cache:
        if t.id == task_id:
            return t
    raise HTTPException(status_code=404, detail=f"Task '{task_id}' 없음")


# ─────────────────────────────────────────────────────────────────────────────
# 분류 엔드포인트 (SSE 스트리밍)
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/classify", tags=["Classify"])
async def classify_tasks(req: ClassifyRequest):
    """
    Task를 분류합니다. provider 필드로 OpenAI / Anthropic 선택 가능.
    Server-Sent Events (SSE) 형식으로 진행 상황을 스트리밍합니다.
    """
    provider = req.provider  # "openai" | "anthropic"
    settings = req.settings or load_settings()

    # 마스킹된 키가 넘어오면 저장된 실제 키로 교체
    if provider == "openai":
        if settings.api_key and settings.api_key.startswith("sk-" + "*"):
            stored = load_settings()
            settings.api_key = stored.api_key
    elif provider == "anthropic":
        if settings.anthropic_api_key and settings.anthropic_api_key.startswith("sk-ant-" + "*"):
            stored = load_settings()
            settings.anthropic_api_key = stored.anthropic_api_key

    if req.task_ids:
        id_set = set(req.task_ids)
        tasks = [t for t in _tasks_cache if t.id in id_set]
    else:
        tasks = list(_tasks_cache)

    if not tasks:
        raise HTTPException(status_code=400, detail="분류할 Task가 없습니다.")

    classifier = get_classifier(settings, provider)
    results_store = load_results(provider)
    total = len(tasks)

    async def event_generator():
        current = 0
        try:
            async for result in classifier.classify_stream(tasks, settings):
                result.provider = provider
                current += 1
                results_store[result.task_id] = result
                payload = {
                    "type": "progress",
                    "task_id": result.task_id,
                    "current": current,
                    "total": total,
                    "result": result.model_dump(),
                }
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

            save_results(results_store, provider)
            yield f"data: {json.dumps({'type': 'done', 'total': current}, ensure_ascii=False)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ─────────────────────────────────────────────────────────────────────────────
# 결과 엔드포인트
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/results", response_model=ResultsResponse, tags=["Results"])
async def get_results(
    label: Optional[str] = Query(None),
    provider: str = Query("openai", description="openai | anthropic"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=10000),
):
    results_store = load_results(provider)
    results = sorted(results_store.values(), key=lambda r: _natural_key(r.task_id))

    if label:
        results = [r for r in results if r.label == label]

    total = len(results)
    classified = sum(1 for r in results_store.values() if r.label != "미분류")
    unclassified = len(results_store) - classified

    start = (page - 1) * page_size
    paged = results[start : start + page_size]

    return ResultsResponse(
        total=total,
        classified=classified,
        unclassified=unclassified,
        results=paged,
    )


@app.get("/api/results/compare", tags=["Results"])
async def get_comparison_results(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=10000),
):
    """OpenAI와 Anthropic 분류 결과를 나란히 비교합니다."""
    openai_results    = load_results("openai")
    anthropic_results = load_results("anthropic")

    all_ids = sorted(set(openai_results.keys()) | set(anthropic_results.keys()), key=_natural_key)

    comparison = []
    for task_id in all_ids:
        o = openai_results.get(task_id)
        a = anthropic_results.get(task_id)
        comparison.append({
            "task_id": task_id,
            "openai_label":       o.label      if o else None,
            "openai_reason":      o.reason     if o else None,
            "anthropic_label":    a.label      if a else None,
            "anthropic_reason":   a.reason     if a else None,
            "match": (o.label == a.label) if (o and a) else None,
        })

    total    = len(comparison)
    both     = sum(1 for c in comparison if c["openai_label"] and c["anthropic_label"])
    matching = sum(1 for c in comparison if c.get("match") is True)

    start = (page - 1) * page_size
    paged = comparison[start : start + page_size]

    return {
        "total": total,
        "both_classified": both,
        "matching": matching,
        "match_rate": round(matching / both * 100, 1) if both else 0,
        "comparison": paged,
    }


@app.put("/api/results/{task_id}", response_model=ClassificationResult, tags=["Results"])
async def update_result(
    task_id: str,
    update: ClassificationResultUpdate,
    provider: str = Query("openai"),
):
    results_store = load_results(provider)
    existing = results_store.get(task_id)

    if existing is None:
        existing = ClassificationResult(task_id=task_id, provider=provider)

    existing.label = update.label
    if update.reason is not None:
        existing.reason = update.reason
    existing.manually_edited = True

    upsert_result(existing, provider)
    return existing


@app.delete("/api/results", tags=["Results"])
async def delete_all_results(
    provider: str = Query("openai", description="openai | anthropic | all"),
):
    """분류 결과를 초기화합니다. provider=all 이면 양쪽 모두 초기화."""
    if provider == "all":
        clear_results("openai")
        clear_results("anthropic")
    else:
        clear_results(provider)
    return {"message": f"'{provider}' 결과가 초기화되었습니다."}


@app.get("/api/results/stats", response_model=StatsResponse, tags=["Results"])
async def get_stats(
    provider: str = Query("openai", description="openai | anthropic"),
):
    results_store = load_results(provider)
    total        = len(_tasks_cache)
    ai_count     = sum(1 for r in results_store.values() if r.label == "AI")
    hybrid_count = sum(1 for r in results_store.values() if r.label == "AI + Human")
    human_count  = sum(1 for r in results_store.values() if r.label == "Human")
    unclassified_count = total - ai_count - hybrid_count - human_count

    l3_map: dict[str, dict] = {}
    for t in _tasks_cache:
        if t.l3 not in l3_map:
            l3_map[t.l3] = {"l3": t.l3, "total": 0, "ai": 0, "hybrid": 0, "human": 0}
        l3_map[t.l3]["total"] += 1
        r = results_store.get(t.id)
        if r:
            if r.label == "AI":
                l3_map[t.l3]["ai"] += 1
            elif r.label == "AI + Human":
                l3_map[t.l3]["hybrid"] += 1
            elif r.label == "Human":
                l3_map[t.l3]["human"] += 1

    return StatsResponse(
        total=total,
        ai_count=ai_count,
        hybrid_count=hybrid_count,
        human_count=human_count,
        unclassified_count=unclassified_count,
        ai_ratio=round(ai_count / total * 100, 1) if total else 0,
        hybrid_ratio=round(hybrid_count / total * 100, 1) if total else 0,
        human_ratio=round(human_count / total * 100, 1) if total else 0,
        by_l3=sorted(l3_map.values(), key=lambda x: x["ai"], reverse=True),
    )


# ─────────────────────────────────────────────────────────────────────────────
# 설정 엔드포인트
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/settings", response_model=ClassifierSettings, tags=["Settings"])
async def get_settings():
    settings = load_settings()
    masked = settings.model_copy()
    if masked.api_key:
        masked.api_key = "sk-" + "*" * 20
    if masked.anthropic_api_key:
        masked.anthropic_api_key = "sk-ant-" + "*" * 20
    return masked


@app.post("/api/settings", response_model=ClassifierSettings, tags=["Settings"])
async def update_settings(settings: ClassifierSettings):
    existing = load_settings()
    if settings.api_key.startswith("sk-" + "*"):
        settings.api_key = existing.api_key
    if settings.anthropic_api_key.startswith("sk-ant-" + "*"):
        settings.anthropic_api_key = existing.anthropic_api_key
    save_settings(settings)
    masked = settings.model_copy()
    if masked.api_key:
        masked.api_key = "sk-" + "*" * 20
    if masked.anthropic_api_key:
        masked.anthropic_api_key = "sk-ant-" + "*" * 20
    return masked


# ─────────────────────────────────────────────────────────────────────────────
# 엑셀 내보내기
# ─────────────────────────────────────────────────────────────────────────────

def _build_result_sheet(ws, tasks_cache: list[Task], results_store: dict, provider_label: str):
    """결과 시트 생성 공통 함수."""
    headers = ["L5_ID", "L2", "L3", "L4", "L5_Name", "L5_Description", "수행주체",
               "분류결과", "적용기준(Knock-out)", "판단근거", "AI수행필요여건", "수동수정여부"]
    ws.append(headers)

    header_fill = PatternFill("solid", fgColor="1F4E79")
    ai_fill     = PatternFill("solid", fgColor="FFE0E0")
    hybrid_fill = PatternFill("solid", fgColor="FFF9DB")
    human_fill  = PatternFill("solid", fgColor="D6F5E3")

    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = Font(bold=True, color="FFFFFF")
        cell.alignment = Alignment(horizontal="center")

    for t in tasks_cache:
        r = results_store.get(t.id)
        label     = r.label if r else "미분류"
        criterion = r.criterion if r else ""
        reason    = r.reason if r else ""
        ai_prereq = r.ai_prerequisites if r else ""
        edited    = "Y" if (r and r.manually_edited) else ""
        row = [t.id, t.l2, t.l3, t.l4, t.name, t.description, t.performer[:100],
               label, criterion, reason, ai_prereq, edited]
        ws.append(row)

        last_row = ws.max_row
        label_cell = ws.cell(row=last_row, column=8)
        if label == "AI":
            label_cell.fill = ai_fill
        elif label == "AI + Human":
            label_cell.fill = hybrid_fill
        elif label == "Human":
            label_cell.fill = human_fill

    col_widths = [12, 10, 14, 14, 28, 45, 35, 16, 28, 40, 50, 10]
    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[ws.cell(1, i).column_letter].width = w


@app.get("/api/export", tags=["Export"])
async def export_results(
    provider: str = Query("openai", description="openai | anthropic"),
):
    """분류 결과를 엑셀 파일로 다운로드합니다."""
    results_store = load_results(provider)
    provider_label = "OpenAI" if provider == "openai" else "Claude"

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"분류결과_{provider_label}"
    _build_result_sheet(ws, _tasks_cache, results_store, provider_label)

    # 요약 시트
    ws2 = wb.create_sheet("요약")
    total    = len(_tasks_cache)
    ai_cnt   = sum(1 for r in results_store.values() if r.label == "AI")
    hyb_cnt  = sum(1 for r in results_store.values() if r.label == "AI + Human")
    hum_cnt  = sum(1 for r in results_store.values() if r.label == "Human")
    rows = [
        ["항목", "값"],
        ["모델", provider_label],
        ["전체 Task", total],
        ["AI", ai_cnt],
        ["AI + Human", hyb_cnt],
        ["Human", hum_cnt],
        ["미분류", total - ai_cnt - hyb_cnt - hum_cnt],
        ["AI 비율", f"{ai_cnt/total*100:.1f}%" if total else "0%"],
        ["AI + Human 비율", f"{hyb_cnt/total*100:.1f}%" if total else "0%"],
    ]
    for row in rows:
        ws2.append(row)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    base = _current_excel_path.stem if _current_excel_path else "results"
    filename = f"{base}_a_results.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@app.get("/api/export/compare", tags=["Export"])
async def export_comparison():
    """OpenAI와 Claude 결과를 비교하는 엑셀 다운로드 (3개 시트)."""
    openai_results    = load_results("openai")
    anthropic_results = load_results("anthropic")

    wb = openpyxl.Workbook()

    # 시트 1: OpenAI 결과
    ws1 = wb.active
    ws1.title = "OpenAI (GPT-5.4)"
    _build_result_sheet(ws1, _tasks_cache, openai_results, "OpenAI")

    # 시트 2: Claude 결과
    ws2 = wb.create_sheet("Claude (Sonnet 4.6)")
    _build_result_sheet(ws2, _tasks_cache, anthropic_results, "Claude")

    # 시트 3: 비교
    ws3 = wb.create_sheet("비교")
    comp_headers = ["L5_ID", "L5_Name", "OpenAI 결과", "Claude 결과", "일치 여부",
                    "OpenAI 근거", "Claude 근거"]
    ws3.append(comp_headers)
    header_fill = PatternFill("solid", fgColor="374151")
    for cell in ws3[1]:
        cell.fill = header_fill
        cell.font = Font(bold=True, color="FFFFFF")
        cell.alignment = Alignment(horizontal="center")

    match_fill    = PatternFill("solid", fgColor="D1FAE5")
    mismatch_fill = PatternFill("solid", fgColor="FEE2E2")

    task_map = {t.id: t for t in _tasks_cache}
    all_ids  = sorted(set(openai_results.keys()) | set(anthropic_results.keys()), key=_natural_key)

    for task_id in all_ids:
        o = openai_results.get(task_id)
        a = anthropic_results.get(task_id)
        task = task_map.get(task_id)
        name = task.name if task else task_id
        match = (o.label == a.label) if (o and a) else None

        row = [
            task_id,
            name,
            o.label if o else "-",
            a.label if a else "-",
            "✓ 일치" if match is True else ("✗ 불일치" if match is False else "-"),
            o.reason if o else "",
            a.reason if a else "",
        ]
        ws3.append(row)

        last = ws3.max_row
        fill = match_fill if match is True else (mismatch_fill if match is False else None)
        if fill:
            for col in range(1, 6):
                ws3.cell(row=last, column=col).fill = fill

    for i, w in enumerate([12, 35, 16, 16, 12, 40, 40], 1):
        ws3.column_dimensions[ws3.cell(1, i).column_letter].width = w

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={(_current_excel_path.stem if _current_excel_path else 'compare')}_a_results_compare.xlsx"},
    )


# ─────────────────────────────────────────────────────────────────────────────
# 엑셀 업로드
# ─────────────────────────────────────────────────────────────────────────────

_PERSIST_ROOT = Path("/app/persist") if Path("/app/persist").exists() else Path(__file__).parent
_UPLOAD_DIR = _PERSIST_ROOT / "uploads"
_UPLOAD_DIR.mkdir(exist_ok=True)
_current_excel_path: Path | None = None


@app.get("/api/upload/current", tags=["Upload"])
async def get_current_file():
    """현재 세션에서 업로드한 파일 정보만 반환합니다."""
    if _current_excel_path and _current_excel_path.exists():
        return {
            "filename": _current_excel_path.name,
            "size_kb": round(_current_excel_path.stat().st_size / 1024, 1),
            "task_count": len(_tasks_cache),
        }
    # 이 세션에서 업로드한 파일이 없으면 빈 응답
    return {"filename": None, "size_kb": 0, "task_count": 0}


@app.post("/api/upload", tags=["Upload"])
async def upload_excel(file: UploadFile = File(...)):
    """엑셀 파일 업로드 — 시트 목록을 반환합니다. 시트 선택은 /api/upload/select-sheet로."""
    global _tasks_cache, _current_excel_path
    from excel_reader import list_sheets

    if not file.filename or not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail=".xlsx 파일만 업로드 가능합니다.")

    save_path = _UPLOAD_DIR / file.filename
    try:
        contents = await file.read()
        save_path.write_bytes(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 저장 실패: {e}")

    # 시트 목록 조회
    try:
        sheets = list_sheets(save_path)
    except Exception as e:
        save_path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=f"엑셀 파싱 실패: {e}")

    _current_excel_path = save_path

    # 파일별 결과 분리를 위해 현재 파일 설정
    set_current_file(file.filename)
    set_current_project(file.filename)
    save_meta(file.filename, task_count=len(_tasks_cache), source="tasks_page")

    # 추천 시트가 있으면 자동 로드
    recommended = next((s for s in sheets if s["recommended"]), None)
    if recommended:
        try:
            new_tasks = load_tasks(save_path, sheet_name=recommended["name"])
            _tasks_cache = new_tasks
        except Exception:
            pass

    return {
        "message": "업로드 성공",
        "filename": file.filename,
        "task_count": len(_tasks_cache),
        "sheets": sheets,
    }


@app.get("/api/upload/sheets", tags=["Upload"])
async def get_excel_sheets():
    """현재 업로드된 엑셀 파일의 시트 목록을 반환합니다."""
    from excel_reader import list_sheets

    if not _current_excel_path or not _current_excel_path.exists():
        raise HTTPException(404, "업로드된 엑셀 파일이 없습니다.")

    sheets = list_sheets(_current_excel_path)
    return {"filename": _current_excel_path.name, "sheets": sheets}


@app.post("/api/upload/select-sheet", tags=["Upload"])
async def select_excel_sheet(request: Request):
    """특정 시트를 선택하여 Task를 로드합니다. Body: {"sheet_name": "시트명"}"""
    global _tasks_cache

    body = await request.json()
    sheet_name = body.get("sheet_name", "")

    if not _current_excel_path or not _current_excel_path.exists():
        raise HTTPException(404, "업로드된 엑셀 파일이 없습니다.")

    try:
        new_tasks = load_tasks(_current_excel_path, sheet_name=sheet_name)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"시트 파싱 실패: {e}")

    _tasks_cache = new_tasks

    return {
        "message": f"시트 '{sheet_name}' 로드 완료",
        "sheet_name": sheet_name,
        "task_count": len(_tasks_cache),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 헬스체크
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/health", tags=["System"])
async def health():
    env_openai    = os.environ.get("OPENAI_API_KEY", "").strip()
    env_anthropic = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    s = load_settings()
    return {
        "status": "ok",
        "task_count": len(_tasks_cache),
        "api_key_configured": bool(env_openai or s.api_key.strip()),
        "openai_configured": bool(env_openai or s.api_key.strip()),
        "anthropic_configured": bool(env_anthropic or s.anthropic_api_key.strip()),
    }


@app.get("/api/usage", tags=["System"])
async def get_usage_stats():
    """누적 API 토큰 사용량 및 예상 비용을 반환합니다."""
    return get_usage()


@app.delete("/api/usage", tags=["System"])
async def reset_usage_stats(provider: str = Query("all")):
    """사용량을 초기화합니다. provider=all|openai|anthropic"""
    reset_usage(provider)
    return {"ok": True, "reset": provider}


# ─────────────────────────────────────────────────────────────────────────────
# Workflow 엔드포인트
# ─────────────────────────────────────────────────────────────────────────────

_workflow_cache: dict = {}   # 최근 업로드된 워크플로우 저장


@app.post("/api/workflow/upload", tags=["Workflow"])
async def upload_workflow(file: UploadFile = File(...)):
    """hr-workflow-ai에서 내보낸 JSON 파일을 업로드하여 파싱합니다."""
    from workflow_parser import parse_workflow_json, get_workflow_summary

    content = await file.read()
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(400, "유효한 JSON 파일이 아닙니다.")

    parsed = parse_workflow_json(data)
    summary = get_workflow_summary(parsed)

    # 캐시에 저장
    global _workflow_cache
    _workflow_cache = {
        "filename": file.filename,
        "parsed": parsed,
        "summary": summary,
        "raw": data,
    }

    # 워크플로우 JSON도 파일로 저장
    save_path = Path(__file__).parent / "workflow.json"
    save_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "ok": True,
        "filename": file.filename,
        **summary,
    }


@app.get("/api/workflow/summary", tags=["Workflow"])
async def get_workflow():
    """업로드된 워크플로우의 요약 정보를 반환합니다."""
    from workflow_parser import parse_workflow_json, get_workflow_summary

    global _workflow_cache
    if "summary" not in _workflow_cache:
        # 파일에서 로드 시도
        save_path = Path(__file__).parent / "workflow.json"
        if save_path.exists():
            data = json.loads(save_path.read_text(encoding="utf-8"))
            parsed = parse_workflow_json(data)
            summary = get_workflow_summary(parsed)
            _workflow_cache.update({
                "filename": save_path.name,
                "parsed": parsed,
                "summary": summary,
                "raw": data,
            })
        else:
            raise HTTPException(404, "업로드된 워크플로우가 없습니다.")

    return _workflow_cache["summary"]


@app.get("/api/workflow/sheets", tags=["Workflow"])
async def list_workflow_sheets():
    """워크플로우 시트 목록을 반환합니다."""
    if "parsed" not in _workflow_cache:
        raise HTTPException(404, "업로드된 워크플로우가 없습니다. JSON 파일을 먼저 업로드하세요.")

    parsed = _workflow_cache["parsed"]
    return {
        "sheets": [
            {
                "sheet_id": s.sheet_id,
                "name": s.name,
                "lanes": s.lanes,
                "l4_count": len(s.l4_nodes),
                "l5_count": len(s.l5_nodes),
                "total_steps": len(s.execution_order),
            }
            for s in parsed.sheets
        ]
    }


@app.get("/api/workflow/sheets/{sheet_id}", tags=["Workflow"])
async def get_workflow_sheet_detail(sheet_id: str):
    """특정 시트의 상세 정보 (노드, 엣지, 실행 순서)를 반환합니다."""
    if "parsed" not in _workflow_cache:
        raise HTTPException(404, "업로드된 워크플로우가 없습니다. JSON 파일을 먼저 업로드하세요.")

    parsed = _workflow_cache["parsed"]
    sheet = next((s for s in parsed.sheets if s.sheet_id == sheet_id), None)
    if not sheet:
        raise HTTPException(404, f"시트 '{sheet_id}'를 찾을 수 없습니다.")

    return {
        "sheet_id": sheet.sheet_id,
        "name": sheet.name,
        "lanes": sheet.lanes,
        "nodes": [
            {
                "node_id": n.id,
                "level": n.level,
                "task_id": n.task_id,
                "label": n.label,
                "description": n.description,
                "position": {"x": n.position_x, "y": n.position_y},
                "metadata": n.metadata,
            }
            for n in sorted(sheet.nodes.values(), key=lambda n: (n.y, n.x))
        ],
        "edges": [
            {
                "id": e.id,
                "source": e.source,
                "target": e.target,
                "label": e.label,
            }
            for e in sheet.edges
        ],
        "execution_order": [
            {
                "step": s.step_number,
                "nodes": [
                    {
                        "node_id": nid,
                        "task_id": sheet.nodes[nid].task_id if nid in sheet.nodes else "",
                        "label": sheet.nodes[nid].label if nid in sheet.nodes else "",
                        "level": sheet.nodes[nid].level if nid in sheet.nodes else "",
                    }
                    for nid in s.node_ids
                ],
                "is_parallel": s.is_parallel,
            }
            for s in sheet.execution_order
        ],
    }


@app.get("/api/workflow/execution-order/{sheet_id}", tags=["Workflow"])
async def get_execution_order(sheet_id: str):
    """특정 시트의 실행 순서만 간결하게 반환합니다."""
    if "parsed" not in _workflow_cache:
        raise HTTPException(404, "업로드된 워크플로우가 없습니다. JSON 파일을 먼저 업로드하세요.")

    parsed = _workflow_cache["parsed"]
    sheet = next((s for s in parsed.sheets if s.sheet_id == sheet_id), None)
    if not sheet:
        raise HTTPException(404, f"시트 '{sheet_id}'를 찾을 수 없습니다.")

    steps = []
    for s in sheet.execution_order:
        step_info = {
            "step": s.step_number,
            "type": "병렬" if s.is_parallel else "순차",
            "tasks": [],
        }
        for nid in s.node_ids:
            node = sheet.nodes.get(nid)
            if node:
                step_info["tasks"].append({
                    "task_id": node.task_id,
                    "label": node.label,
                    "level": node.level,
                })
        steps.append(step_info)

    return {
        "sheet_id": sheet_id,
        "sheet_name": sheet.name,
        "total_steps": len(steps),
        "parallel_count": sum(1 for s in steps if s["type"] == "병렬"),
        "sequential_count": sum(1 for s in steps if s["type"] == "순차"),
        "steps": steps,
    }


# ─────────────────────────────────────────────────────────────────────────────
# PPT 업로드 + 태스크 매칭
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/workflow/upload-ppt", tags=["Workflow"])
async def upload_ppt_workflow(file: UploadFile = File(...)):
    """PPT 파일을 업로드하여 슬라이드별 노드를 추출하고 태스크와 매칭합니다."""
    from ppt_parser import parse_ppt, match_nodes_to_tasks, ppt_slide_to_react_flow, ppt_to_parsed_workflow

    content = await file.read()
    try:
        parsed = parse_ppt(content)
    except Exception as e:
        raise HTTPException(400, f"PPT 파싱 실패: {e}")

    # 태스크 매칭용 데이터 준비
    task_list = [
        {
            "id": t.id, "name": t.name,
            "l4": t.l4, "l4_id": t.l4_id,
            "l3": t.l3, "l3_id": t.l3_id,
        }
        for t in _tasks_cache
    ]

    slides_result = []
    for slide in parsed.slides:
        # 노드-태스크 매칭
        matches = match_nodes_to_tasks(slide.nodes, task_list)

        # React Flow 변환
        react_flow = ppt_slide_to_react_flow(slide)

        # 매칭 결과를 React Flow 노드에 반영
        match_map = {m["node_id"]: m for m in matches}
        for rf_node in react_flow["nodes"]:
            m = match_map.get(rf_node["id"])
            if m and m["matched_task_id"]:
                rf_node["data"]["id"] = m["matched_task_id"]
                rf_node["data"]["matchedTaskName"] = m["matched_task_name"]
                rf_node["data"]["matchConfidence"] = m["match_confidence"]
                rf_node["data"]["matchedLevel"] = m["matched_level"]

        slides_result.append({
            "slide_index": slide.index,
            "title": slide.title,
            "node_count": len(slide.nodes),
            "edge_count": len(slide.edges),
            "matches": matches,
            "react_flow": react_flow,
        })

    # PPT → ParsedWorkflow 변환 (To-Be 생성에서 사용)
    all_matches = [
        match_nodes_to_tasks(slide.nodes, task_list)
        for slide in parsed.slides
    ]
    ppt_workflow = ppt_to_parsed_workflow(parsed, all_matches)

    # 워크플로우 캐시에 PPT 결과 + 변환된 워크플로우 저장
    global _workflow_cache
    _workflow_cache["ppt"] = {
        "filename": file.filename,
        "parsed": parsed,
        "slides": slides_result,
    }
    # JSON 워크플로우와 동일한 키로 저장 → generate-tobe에서 사용 가능
    _workflow_cache["parsed"] = ppt_workflow

    return {
        "ok": True,
        "filename": file.filename,
        "slide_count": parsed.slide_count,
        "slides": slides_result,
    }


# ─────────────────────────────────────────────────────────────────────────────
# To-Be Workflow 생성
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/workflow/slide-l4-mapping", tags=["Workflow"])
async def save_slide_l4_mapping(request: Request):
    """
    슬라이드별 L4 매핑을 저장합니다.
    Body: { "mappings": { "0": "1.1.1", "1": "1.1.2", ... } }
    key = 슬라이드 인덱스, value = L4 ID
    """
    body = await request.json()
    mappings = body.get("mappings", {})

    global _workflow_cache
    _workflow_cache["slide_l4_mapping"] = mappings

    # PPT 결과가 있으면 매핑 반영하여 ParsedWorkflow 재생성
    if "ppt" in _workflow_cache:
        from ppt_parser import ppt_to_parsed_workflow
        ppt_data = _workflow_cache["ppt"]
        parsed_ppt = ppt_data["parsed"]

        # 매칭 정보 재구성
        slides_result = ppt_data["slides"]
        all_matches = [s.get("matches", []) for s in slides_result]

        ppt_workflow = ppt_to_parsed_workflow(
            parsed_ppt, all_matches, slide_l4_mapping=mappings
        )
        _workflow_cache["parsed"] = ppt_workflow

    return {"ok": True, "mappings": mappings}


@app.post("/api/workflow/generate-tobe", tags=["Workflow"])
async def generate_tobe_workflow(
    sheet_id: str = Query("default", description="As-Is 워크플로우 시트 ID"),
    provider: str = Query("openai", description="분류 결과 제공자 (openai | anthropic)"),
    process_name: str = Query("", description="프로세스 이름 (빈 값이면 시트 이름 사용)"),
):
    """As-Is 워크플로우 + 분류 결과 → To-Be Workflow 초안을 생성합니다 (Claude 기반)."""
    from workflow_parser import parse_workflow_json, get_workflow_summary
    from tobe_generator import generate_tobe, generate_tobe_with_llm

    # 워크플로우 로드
    global _workflow_cache
    if "parsed" not in _workflow_cache:
        save_path = Path(__file__).parent / "workflow.json"
        if save_path.exists():
            data = json.loads(save_path.read_text(encoding="utf-8"))
            parsed = parse_workflow_json(data)
            _workflow_cache["parsed"] = parsed
            _workflow_cache["summary"] = get_workflow_summary(parsed)
            _workflow_cache["raw"] = data
        else:
            raise HTTPException(404, "업로드된 워크플로우가 없습니다. 먼저 워크플로우를 업로드하세요.")

    parsed = _workflow_cache["parsed"]
    sheet = next((s for s in parsed.sheets if s.sheet_id == sheet_id), None)
    if not sheet:
        if parsed.sheets:
            sheet = parsed.sheets[0]
        else:
            raise HTTPException(404, "워크플로우에 시트가 없습니다.")

    # 분류 결과 로드
    results_store = load_results(provider)
    if not results_store:
        raise HTTPException(
            400,
            f"'{provider}' 분류 결과가 없습니다. 먼저 분류를 실행하세요.",
        )

    # 슬라이드-L4 매핑이 있으면 해당 L4의 L5 태스크만 필터링
    slide_l4_mapping = _workflow_cache.get("slide_l4_mapping", {})
    # sheet_id가 "ppt-slide-N" 형식이면 슬라이드 인덱스 추출
    mapped_l4_id = ""
    if sheet_id.startswith("ppt-slide-"):
        slide_idx = sheet_id.replace("ppt-slide-", "")
        mapped_l4_id = slide_l4_mapping.get(slide_idx, "")

    # ClassificationResult → dict 변환
    classification_dict: dict[str, dict] = {}
    for tid, cr in results_store.items():
        task = next((t for t in _tasks_cache if t.id == tid), None)

        # L4 필터: 매핑이 설정되어 있으면 해당 L4의 태스크만 포함
        if mapped_l4_id and task:
            if task.l4_id != mapped_l4_id:
                continue

        classification_dict[tid] = {
            "label": cr.label,
            "reason": cr.reason,
            "hybrid_note": cr.hybrid_note,
            "input_types": cr.input_types,
            "output_types": cr.output_types,
            "task_name": task.name if task else "",
        }

    # To-Be 생성 (Claude LLM 기반)
    tobe = await generate_tobe_with_llm(
        as_is_sheet=sheet,
        classification_results=classification_dict,
        process_name=process_name or sheet.name,
    )

    return {
        "ok": True,
        "summary": tobe.summary,
        "execution_steps": tobe.execution_steps,
        "react_flow": tobe.react_flow,
    }


# ─────────────────────────────────────────────────────────────────────────────
# New Workflow 엔드포인트 (엑셀 → AI 워크플로우 설계 초안)
# ─────────────────────────────────────────────────────────────────────────────

# New Workflow 전용 캐시 (독립 운영) + 자동 복원
_nw_tasks_cache: list[Task] = []
_nw_projects_cache: list[dict] = []  # 과제 엑셀 형식일 때 사용
_nw_excel_path: Path | None = None
_new_workflow_cache: dict = {}
_restore_cache("new_workflow", _new_workflow_cache)


@app.post("/api/new-workflow/upload", tags=["NewWorkflow"])
async def upload_new_workflow_excel(file: UploadFile = File(...)):
    """
    New Workflow 전용 엑셀 업로드.
    과제 엑셀 형식 (2행 병합 헤더) 자동 감지 → 과제 데이터로 파싱.
    L5 Task 형식이면 기존 방식으로 파싱.
    """
    global _nw_tasks_cache, _nw_excel_path
    from excel_reader import list_sheets
    from project_excel_reader import parse_project_excel, projects_to_freeform_params

    if not file.filename or not file.filename.endswith(".xlsx"):
        raise HTTPException(400, ".xlsx 파일만 업로드 가능합니다.")

    save_path = _UPLOAD_DIR / f"nw_{file.filename}"
    try:
        contents = await file.read()
        save_path.write_bytes(contents)
    except Exception as e:
        raise HTTPException(500, f"파일 저장 실패: {e}")

    _nw_excel_path = save_path
    set_current_project(file.filename)

    # 1차: 과제 엑셀 형식 시도 (2행 병합 헤더)
    projects = []
    try:
        projects = parse_project_excel(save_path)
    except Exception:
        pass

    if projects:
        # 과제 형식 감지됨 — 프로젝트 데이터를 별도 저장
        _nw_projects_cache.clear()
        _nw_projects_cache.extend(projects)
        _nw_tasks_cache = []  # L5 Task는 없음

        save_meta(file.filename, task_count=0, project_count=len(projects), source="new_workflow", format="project")

        return {
            "message": "과제 엑셀 업로드 성공",
            "filename": file.filename,
            "format": "project",
            "project_count": len(projects),
            "task_count": 0,
            "projects": [{"no": p.get("project_no", ""), "name": p.get("name", "")} for p in projects],
            "sheets": [],
        }

    # 2차: L5 Task 형식 시도
    try:
        sheets = list_sheets(save_path)
    except Exception as e:
        save_path.unlink(missing_ok=True)
        raise HTTPException(422, f"엑셀 파싱 실패: {e}")

    recommended = next((s for s in sheets if s["recommended"]), None)
    if recommended:
        try:
            _nw_tasks_cache = load_tasks(save_path, sheet_name=recommended["name"])
        except Exception:
            pass

    save_meta(file.filename, task_count=len(_nw_tasks_cache), source="new_workflow", format="l5_tasks")

    return {
        "message": "업로드 성공",
        "filename": file.filename,
        "format": "l5_tasks",
        "project_count": 0,
        "task_count": len(_nw_tasks_cache),
        "sheets": sheets,
    }


@app.post("/api/new-workflow/select-sheet", tags=["NewWorkflow"])
async def select_new_workflow_sheet(request: Request):
    """New Workflow 전용 시트 선택."""
    global _nw_tasks_cache

    body = await request.json()
    sheet_name = body.get("sheet_name", "")

    if not _nw_excel_path or not _nw_excel_path.exists():
        raise HTTPException(404, "업로드된 엑셀 파일이 없습니다.")

    try:
        _nw_tasks_cache = load_tasks(_nw_excel_path, sheet_name=sheet_name)
    except Exception as e:
        raise HTTPException(422, f"시트 파싱 실패: {e}")

    return {
        "message": f"시트 '{sheet_name}' 로드 완료",
        "sheet_name": sheet_name,
        "task_count": len(_nw_tasks_cache),
    }


@app.get("/api/new-workflow/tasks", tags=["NewWorkflow"])
async def get_new_workflow_tasks():
    """New Workflow에 로드된 Task 목록 반환."""
    if not _nw_tasks_cache:
        return {"total": 0, "tasks": []}
    tasks = [
        {
            "id": t.id, "l2": t.l2, "l3": t.l3, "l3_id": t.l3_id,
            "l4": t.l4, "l4_id": t.l4_id, "name": t.name,
            "description": t.description, "performer": t.performer,
        }
        for t in _nw_tasks_cache
    ]
    return {"total": len(tasks), "tasks": tasks}


@app.get("/api/new-workflow/filters", tags=["NewWorkflow"])
async def get_new_workflow_filters():
    """New Workflow Task에서 L3 필터 옵션 반환."""
    l3_set: dict[str, str] = {}
    for t in _nw_tasks_cache:
        if t.l3 and t.l3_id:
            l3_set[t.l3_id] = t.l3
    return {
        "l3_options": [{"id": k, "name": v} for k, v in sorted(l3_set.items(), key=lambda x: _natural_key(x[0]))],
    }


@app.post("/api/new-workflow/generate", tags=["NewWorkflow"])
async def generate_new_workflow(
    process_name: str = Query("", description="프로세스 이름 (비우면 자동 추론)"),
    project_index: int = Query(-1, description="과제 엑셀에서 선택된 과제 인덱스 (0부터)"),
    l3: Optional[str] = Query(None, description="특정 L3 Unit Process로 필터 (비우면 전체)"),
    l4: Optional[str] = Query(None, description="특정 L4 Activity로 필터 (비우면 전체)"),
):
    """
    New Workflow 전용 Task 또는 과제 데이터를 분석하여 AI 워크플로우 설계 초안을 생성합니다.
    과제 엑셀이 업로드된 경우 project_index로 개별 과제를 선택합니다.
    """
    from new_workflow_generator import generate_new_workflow as _gen, result_to_dict
    from new_workflow_generator import generate_workflow_from_freeform, result_to_dict as _rtd

    # 과제 형식이 로드된 경우 → 선택된 과제만 처리
    if _nw_projects_cache:
        from project_excel_reader import projects_to_freeform_params
        if 0 <= project_index < len(_nw_projects_cache):
            selected = [_nw_projects_cache[project_index]]
        else:
            selected = _nw_projects_cache  # fallback: 전체
        params = projects_to_freeform_params(selected)
        if process_name:
            params["process_name"] = process_name

        settings = load_settings()
        anthropic_key = os.getenv("ANTHROPIC_API_KEY", "") or settings.anthropic_api_key
        openai_key = os.getenv("OPENAI_API_KEY", "") or settings.api_key

        result = await generate_workflow_from_freeform(
            **params,
            api_key=anthropic_key,
            model=settings.anthropic_model or "claude-sonnet-4-6",
            openai_api_key=openai_key,
            openai_model=settings.model or "gpt-5.4",
        )
        result_dict = _rtd(result)
        _new_workflow_cache.update(result_dict)
        _persist_cache("new_workflow", _new_workflow_cache)
        return {"ok": True, **result_dict}

    # L5 Task 형식
    source_tasks = _nw_tasks_cache if _nw_tasks_cache else _tasks_cache
    if not source_tasks:
        raise HTTPException(400, "로드된 Task가 없습니다. 먼저 엑셀 파일을 업로드하세요.")

    # 필터 적용
    tasks = source_tasks
    if l3:
        tasks = [t for t in tasks if t.l3 == l3 or t.l3_id == l3]
    if l4:
        tasks = [t for t in tasks if t.l4 == l4 or t.l4_id == l4]

    if not tasks:
        raise HTTPException(400, "필터 조건에 맞는 Task가 없습니다.")

    # 프로세스명 자동 추론
    if not process_name:
        l2_names = list({t.l2 for t in tasks if t.l2})
        process_name = l2_names[0] if l2_names else "HR 프로세스"

    # 설정에서 API 키 로드
    settings = load_settings()
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "") or settings.anthropic_api_key
    openai_key = os.getenv("OPENAI_API_KEY", "") or settings.api_key

    result = await _gen(
        tasks=tasks,
        process_name=process_name,
        api_key=anthropic_key,
        model=settings.anthropic_model or "claude-sonnet-4-6",
        openai_api_key=openai_key,
        openai_model=settings.model or "gpt-5.4",
    )

    result_dict = result_to_dict(result)
    _new_workflow_cache.update(result_dict)
    _persist_cache("new_workflow", _new_workflow_cache)

    return {"ok": True, **result_dict}


@app.post("/api/new-workflow/generate-freeform", tags=["NewWorkflow"])
async def generate_new_workflow_freeform(request: Request):
    """
    자유형식 입력을 받아 AI가 새로운 L5 Task를 정의하고 Workflow를 설계합니다.
    Body: { process_name, inputs, outputs, systems, pain_points, additional_info }
    """
    from new_workflow_generator import generate_workflow_from_freeform, result_to_dict

    body = await request.json()
    process_name = body.get("process_name", "")
    if not process_name:
        raise HTTPException(400, "프로세스/주제명을 입력해 주세요.")

    settings = load_settings()
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "") or settings.anthropic_api_key
    openai_key = os.getenv("OPENAI_API_KEY", "") or settings.api_key

    result = await generate_workflow_from_freeform(
        process_name=process_name,
        inputs=body.get("inputs", ""),
        outputs=body.get("outputs", ""),
        systems=body.get("systems", ""),
        pain_points=body.get("pain_points", ""),
        additional_info=body.get("additional_info", ""),
        api_key=anthropic_key,
        model=settings.anthropic_model or "claude-sonnet-4-6",
        openai_api_key=openai_key,
        openai_model=settings.model or "gpt-5.4",
    )

    result_dict = result_to_dict(result)
    _new_workflow_cache.clear()
    _new_workflow_cache.update(result_dict)
    _persist_cache("new_workflow", _new_workflow_cache)


    return {"ok": True, **result_dict}


@app.post("/api/new-workflow/benchmark", tags=["NewWorkflow"])
async def benchmark_new_workflow():
    """
    현재 Workflow 결과를 기반으로 웹 벤치마킹 검색 후 LLM으로 개선합니다.
    """
    from benchmark_search import search_benchmarks, refine_workflow_with_benchmarks
    from new_workflow_generator import result_to_dict, _parse_freeform_result

    if not _new_workflow_cache:
        raise HTTPException(400, "Workflow 결과가 없습니다. 먼저 1단계를 실행하세요.")

    # 1. 웹 벤치마킹 검색
    benchmark_results = await search_benchmarks(_new_workflow_cache)

    if not benchmark_results:
        raise HTTPException(500, "벤치마킹 검색 결과를 가져오지 못했습니다. 잠시 후 다시 시도해 주세요.")

    # 2. LLM으로 Workflow 개선
    settings = load_settings()
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "") or settings.anthropic_api_key
    openai_key = os.getenv("OPENAI_API_KEY", "") or settings.api_key

    refined_data = await refine_workflow_with_benchmarks(
        workflow_cache=_new_workflow_cache,
        benchmark_results=benchmark_results,
        api_key=anthropic_key,
        model=settings.anthropic_model or "claude-sonnet-4-6",
        openai_api_key=openai_key,
        openai_model=settings.model or "gpt-5.4",
    )

    if "error" in refined_data:
        raise HTTPException(500, refined_data["error"])

    # 벤치마킹 인사이트 저장
    benchmark_insights = refined_data.pop("benchmark_insights", [])
    improvement_summary = refined_data.pop("improvement_summary", "")

    # 개선된 Workflow를 파싱하여 캐시 업데이트
    refined_result = _parse_freeform_result(refined_data)
    refined_dict = result_to_dict(refined_result)

    _new_workflow_cache.clear()
    _new_workflow_cache.update(refined_dict)
    _persist_cache("new_workflow", _new_workflow_cache)

    return {
        "ok": True,
        "benchmark_insights": benchmark_insights,
        "improvement_summary": improvement_summary,
        "search_count": len(benchmark_results),
        **refined_dict,
    }


@app.get("/api/new-workflow/result", tags=["NewWorkflow"])
async def get_new_workflow_result():
    """마지막으로 생성된 New Workflow 결과를 반환합니다."""
    if not _new_workflow_cache:
        raise HTTPException(404, "생성된 New Workflow 결과가 없습니다. 먼저 생성을 실행하세요.")
    return {"ok": True, **_new_workflow_cache}


@app.put("/api/new-workflow/result", tags=["NewWorkflow"])
async def save_edited_workflow(request: Request):
    """3단계에서 편집된 Workflow를 저장합니다."""
    body = await request.json()
    if not body:
        raise HTTPException(400, "저장할 데이터가 없습니다.")
    _new_workflow_cache.clear()
    _new_workflow_cache.update(body)
    _persist_cache("new_workflow", _new_workflow_cache)
    return {"ok": True}


@app.delete("/api/new-workflow/result", tags=["NewWorkflow"])
async def clear_new_workflow_result():
    """New Workflow 결과를 초기화합니다."""
    _new_workflow_cache.clear()
    clear_data("new_workflow")
    return {"ok": True}


@app.get("/api/new-workflow/export-html", tags=["NewWorkflow"])
async def export_new_workflow_as_html():
    """AI Service Flow를 PwC 표준 HTML로 내보냅니다."""
    from html_exporter import export_workflow_html

    if not _new_workflow_cache:
        raise HTTPException(404, "Workflow 결과가 없습니다.")

    html = export_workflow_html(_new_workflow_cache)
    process_name = _new_workflow_cache.get("process_name", "workflow")
    filename = f"AI_Service_Flow_{process_name}.html"
    # 한글 파일명 인코딩
    from urllib.parse import quote
    encoded_filename = quote(filename)

    return StreamingResponse(
        io.BytesIO(html.encode("utf-8")),
        media_type="text/html; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"},
    )


@app.get("/api/new-workflow/export-hr-json", tags=["NewWorkflow"])
async def export_new_workflow_as_hr_json():
    """
    New Workflow 결과를 hr-workflow-ai v2.0 호환 JSON으로 변환하여 다운로드합니다.
    hr-workflow-ai에 직접 Import할 수 있는 형식입니다.
    """
    from new_workflow_generator import (
        result_to_hr_workflow_json,
        NewWorkflowResult,
        AIAgent,
        AssignedTask,
        ExecutionStep as NWExecutionStep,
    )
    import io

    if not _new_workflow_cache:
        raise HTTPException(404, "생성된 New Workflow 결과가 없습니다. 먼저 생성을 실행하세요.")

    # 캐시 dict → NewWorkflowResult 복원
    cache = _new_workflow_cache
    agents = []
    for a in cache.get("agents", []):
        assigned = [
            AssignedTask(
                task_id=t["task_id"],
                task_name=t["task_name"],
                l4=t["l4"],
                l3=t["l3"],
                ai_role=t["ai_role"],
                human_role=t["human_role"],
                input_data=t["input_data"],
                output_data=t["output_data"],
                automation_level=t["automation_level"],
            )
            for t in a.get("assigned_tasks", [])
        ]
        agents.append(AIAgent(
            agent_id=a["agent_id"],
            agent_name=a["agent_name"],
            agent_type=a["agent_type"],
            ai_technique=a["ai_technique"],
            description=a["description"],
            automation_level=a["automation_level"],
            assigned_tasks=assigned,
        ))

    flow = [
        NWExecutionStep(
            step=s["step"],
            step_name=s["step_name"],
            step_type=s["step_type"],
            description=s["description"],
            agent_ids=s["agent_ids"],
            task_ids=s["task_ids"],
        )
        for s in cache.get("execution_flow", [])
    ]

    result = NewWorkflowResult(
        blueprint_summary=cache.get("blueprint_summary", ""),
        process_name=cache.get("process_name", "AI 워크플로우"),
        total_tasks=cache.get("total_tasks", 0),
        full_auto_count=cache.get("full_auto_count", 0),
        human_in_loop_count=cache.get("human_in_loop_count", 0),
        human_supervised_count=cache.get("human_supervised_count", 0),
        agents=agents,
        execution_flow=flow,
    )

    hr_json = result_to_hr_workflow_json(result)
    filename = f"{result.process_name or 'new_workflow'}.json"

    from urllib.parse import quote
    encoded_fn = quote(filename)
    return StreamingResponse(
        io.BytesIO(json.dumps(hr_json, ensure_ascii=False, indent=2).encode("utf-8")),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_fn}"},
    )


# ─────────────────────────────────────────────────────────────────────────────
# Project Management 엔드포인트 (과제 정의서 / 과제 설계서)
# ─────────────────────────────────────────────────────────────────────────────

# 과제 정의서 캐시
_project_definition_cache: dict = {}
_restore_cache("project_definition", _project_definition_cache)


def _build_classification_from_workflow(workflow_cache: dict) -> dict[str, dict]:
    """New Workflow 결과에서 분류 데이터를 합성합니다."""
    classification: dict[str, dict] = {}
    for agent in workflow_cache.get("agents", []):
        for task in agent.get("assigned_tasks", []):
            level = task.get("automation_level", "")
            if "on-the-Loop" in level or "out-of-the-Loop" in level:
                label = "AI"
            elif "in-the-Loop" in level:
                label = "AI + Human"
            else:
                label = "Human"
            classification[task["task_id"]] = {
                "label": label,
                "reason": task.get("ai_role", ""),
                "hybrid_note": task.get("human_role", ""),
                "input_types": ", ".join(task.get("input_data", [])),
                "output_types": ", ".join(task.get("output_data", [])),
                "ai_prerequisites": "",
            }
    return classification


@app.post("/api/project-management/definition/generate", tags=["ProjectManagement"])
async def generate_project_definition(
    provider: str = Query("openai", description="분류 결과 제공자 (openai | anthropic)"),
    source: str = Query("", description="데이터 소스 (new-workflow이면 NW 캐시 사용)"),
    process_name: str = Query("", description="프로세스 이름 (빈 값이면 자동 추론)"),
    author: str = Query("", description="작성자 (빈 값이면 'PwC')"),
    l3: Optional[str] = Query(None, description="특정 L3로 필터"),
    l4: Optional[str] = Query(None, description="특정 L4로 필터"),
):
    """
    분류 결과 + To-Be Workflow 결과를 기반으로 과제 정의서를 자동 생성합니다.
    source=new-workflow이면 New Workflow 캐시에서 데이터를 사용합니다.
    """
    from project_definition_generator import (
        generate_project_definition_with_llm,
        generate_project_definition_fallback,
        project_definition_to_dict,
    )

    # 데이터 소스 선택
    use_nw = source == "new-workflow"
    src_tasks = _nw_tasks_cache if use_nw else _tasks_cache

    if not src_tasks:
        raise HTTPException(400, "로드된 Task가 없습니다. 먼저 엑셀 파일을 업로드하세요.")

    # 필터 적용
    tasks = src_tasks
    if l3:
        tasks = [t for t in tasks if t.l3 == l3 or t.l3_id == l3]
    if l4:
        tasks = [t for t in tasks if t.l4 == l4 or t.l4_id == l4]

    if not tasks:
        raise HTTPException(400, "필터 조건에 맞는 Task가 없습니다.")

    # 분류 결과 로드
    if use_nw:
        if not _new_workflow_cache:
            raise HTTPException(400, "New Workflow 결과가 없습니다. 먼저 생성을 실행하세요.")
        classification_dict = _build_classification_from_workflow(_new_workflow_cache)
    else:
        results_store = load_results(provider)
        if not results_store:
            raise HTTPException(400, f"'{provider}' 분류 결과가 없습니다. 먼저 분류를 실행하세요.")

    # Task → dict 변환 + 분류 결과 매핑
    task_dicts = []
    if not use_nw:
        classification_dict = {}
    for t in tasks:
        td = {
            "id": t.id, "l2": t.l2, "l2_id": t.l2_id,
            "l3": t.l3, "l3_id": t.l3_id,
            "l4": t.l4, "l4_id": t.l4_id,
            "name": t.name, "description": t.description,
            "performer": t.performer,
        }
        # Pain Point 필드 추가
        for attr in ["pain_time", "pain_accuracy", "pain_repetition",
                      "pain_data", "pain_system", "pain_communication", "pain_other"]:
            td[attr] = getattr(t, attr, "")
        task_dicts.append(td)

        if not use_nw:
            cr = results_store.get(t.id)
            if cr:
                classification_dict[t.id] = {
                    "label": cr.label,
                    "reason": cr.reason,
                    "hybrid_note": cr.hybrid_note,
                    "input_types": cr.input_types,
                    "output_types": cr.output_types,
                    "ai_prerequisites": cr.ai_prerequisites,
                }

    # 프로세스명 자동 추론
    if not process_name:
        l2_names = list({t.l2 for t in tasks if t.l2})
        process_name = l2_names[0] if l2_names else "HR 프로세스"

    # To-Be 데이터 (있으면 활용)
    tobe_data = None
    if _new_workflow_cache:
        tobe_data = _new_workflow_cache

    # 설정에서 API 키 로드
    settings = load_settings()
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "") or settings.anthropic_api_key

    try:
        result = await generate_project_definition_with_llm(
            tasks=task_dicts,
            classification_results=classification_dict,
            tobe_data=tobe_data,
            process_name=process_name,
            api_key=anthropic_key,
            model=settings.anthropic_model or "claude-sonnet-4-6",
            author=author,
        )
    except Exception as e:
        print(f"[과제 정의서] LLM 실패, fallback 사용: {e}")
        result = generate_project_definition_fallback(
            tasks=task_dicts,
            classification_results=classification_dict,
            tobe_data=tobe_data,
            process_name=process_name,
            author=author,
        )

    result_dict = project_definition_to_dict(result)
    _project_definition_cache.clear()
    _project_definition_cache.update(result_dict)
    _persist_cache("project_definition", _project_definition_cache)

    return {"ok": True, **result_dict}


@app.get("/api/project-management/definition", tags=["ProjectManagement"])
async def get_project_definition():
    """마지막으로 생성된 과제 정의서를 반환합니다."""
    if not _project_definition_cache:
        raise HTTPException(404, "생성된 과제 정의서가 없습니다. 먼저 생성을 실행하세요.")
    return {"ok": True, **_project_definition_cache}


@app.delete("/api/project-management/definition", tags=["ProjectManagement"])
async def clear_project_definition():
    """과제 정의서 결과를 초기화합니다."""
    _project_definition_cache.clear()
    clear_data("project_definition")
    return {"ok": True}


# ── 과제 설계서 ───────────────────────────────────────────────────────────────

_project_design_cache: dict = {}
_restore_cache("project_design", _project_design_cache)


@app.post("/api/project-management/design/generate", tags=["ProjectManagement"])
async def generate_project_design(
    provider: str = Query("openai", description="분류 결과 제공자 (openai | anthropic)"),
    source: str = Query("", description="데이터 소스 (new-workflow이면 NW 캐시 사용)"),
    process_name: str = Query("", description="프로세스 이름 (빈 값이면 자동 추론)"),
    l3: Optional[str] = Query(None, description="특정 L3로 필터"),
    l4: Optional[str] = Query(None, description="특정 L4로 필터"),
):
    """
    분류 결과 + To-Be Workflow 결과를 기반으로 과제 설계서를 자동 생성합니다.
    source=new-workflow이면 New Workflow 캐시에서 데이터를 사용합니다.
    """
    from project_design_generator import (
        generate_project_design_with_llm,
        generate_project_design_fallback,
        project_design_to_dict,
    )

    use_nw = source == "new-workflow"
    src_tasks = _nw_tasks_cache if use_nw else _tasks_cache

    # New Workflow source면서 Task가 없으면 (과제 엑셀 등) workflow 캐시에서 처리
    if use_nw and not src_tasks and _new_workflow_cache:
        # Workflow 결과에서 Task를 추출
        task_dicts = []
        classification_dict = _build_classification_from_workflow(_new_workflow_cache)
        for agent in _new_workflow_cache.get("agents", []):
            for t in agent.get("assigned_tasks", []):
                task_dicts.append({
                    "id": t.get("task_id", ""), "l2": "", "l3": t.get("l3", ""),
                    "l4": t.get("l4", ""), "l4_id": "", "name": t.get("task_name", ""),
                    "description": t.get("ai_role", ""), "performer": "",
                })
    else:
        if not src_tasks:
            raise HTTPException(400, "로드된 Task가 없습니다. 먼저 엑셀 파일을 업로드하세요.")

        tasks = src_tasks
        if l3:
            tasks = [t for t in tasks if t.l3 == l3 or t.l3_id == l3]
        if l4:
            tasks = [t for t in tasks if t.l4 == l4 or t.l4_id == l4]

        if not tasks:
            raise HTTPException(400, "필터 조건에 맞는 Task가 없습니다.")

        if use_nw:
            if not _new_workflow_cache:
                raise HTTPException(400, "New Workflow 결과가 없습니다.")
            classification_dict = _build_classification_from_workflow(_new_workflow_cache)
        else:
            results_store = load_results(provider)
            if not results_store:
                raise HTTPException(400, f"'{provider}' 분류 결과가 없습니다. 먼저 분류를 실행하세요.")
            classification_dict = {}

        task_dicts = []
        for t in tasks:
            td = {
                "id": t.id, "l2": t.l2, "l3": t.l3, "l4": t.l4,
                "l4_id": t.l4_id, "name": t.name,
                "description": t.description, "performer": t.performer,
            }
            task_dicts.append(td)

            if not use_nw:
                cr = results_store.get(t.id)
                if cr:
                    classification_dict[t.id] = {
                        "label": cr.label,
                        "reason": cr.reason,
                        "hybrid_note": cr.hybrid_note,
                        "input_types": cr.input_types,
                        "output_types": cr.output_types,
                    }

    # 프로세스명 자동 추론
    if not process_name:
        l2_names = list({t.l2 for t in tasks if t.l2})
        process_name = l2_names[0] if l2_names else "HR 프로세스"

    # To-Be 데이터 (있으면 활용)
    tobe_data = None
    if _new_workflow_cache:
        tobe_data = _new_workflow_cache

    # 과제 정의서의 제목 가져오기
    project_title = _project_definition_cache.get("project_title", f"{process_name} AI 자동화")

    # 설정에서 API 키 로드
    settings = load_settings()
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "") or settings.anthropic_api_key

    try:
        result = await generate_project_design_with_llm(
            tasks=task_dicts,
            classification_results=classification_dict,
            tobe_data=tobe_data,
            process_name=process_name,
            project_title=project_title,
            api_key=anthropic_key,
            model=settings.anthropic_model or "claude-sonnet-4-6",
        )
    except Exception as e:
        print(f"[과제 설계서] LLM 실패, fallback 사용: {e}")
        result = generate_project_design_fallback(
            tasks=task_dicts,
            classification_results=classification_dict,
            tobe_data=tobe_data,
            process_name=process_name,
            project_title=project_title,
        )

    result_dict = project_design_to_dict(result)
    _project_design_cache.clear()
    _project_design_cache.update(result_dict)
    _persist_cache("project_design", _project_design_cache)

    return {"ok": True, **result_dict}


@app.get("/api/project-management/design", tags=["ProjectManagement"])
async def get_project_design():
    """마지막으로 생성된 과제 설계서를 반환합니다."""
    if not _project_design_cache:
        raise HTTPException(404, "생성된 과제 설계서가 없습니다. 먼저 생성을 실행하세요.")
    return {"ok": True, **_project_design_cache}


@app.delete("/api/project-management/design", tags=["ProjectManagement"])
async def clear_project_design():
    """과제 설계서 결과를 초기화합니다."""
    _project_design_cache.clear()
    clear_data("project_design")
    return {"ok": True}


@app.get("/api/project-management/export-ppt", tags=["ProjectManagement"])
async def export_project_ppt():
    """과제 정의서 + 설계서를 PPT 템플릿에 채워서 다운로드합니다."""
    from ppt_exporter import export_ppt

    definition = _project_definition_cache if _project_definition_cache else None
    design = _project_design_cache if _project_design_cache else None

    if not definition and not design:
        raise HTTPException(404, "과제 정의서 또는 설계서가 없습니다. 먼저 생성을 실행하세요.")

    ppt_bytes = export_ppt(definition=definition, design=design)

    title = definition.get("project_title", "과제정의서") if definition else "과제정의서"
    filename = f"{title}.pptx"

    return StreamingResponse(
        ppt_bytes,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
