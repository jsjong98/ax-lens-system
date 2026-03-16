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

from fastapi import FastAPI, HTTPException, Query, UploadFile, File
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
    upsert_result,
)
from usage_store import get_usage, reset_usage

# ── 앱 초기화 ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="HR Task 분류 API",
    description="HR As-Is 프로세스의 L5 Task를 OpenAI / Anthropic으로 분류하는 API",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 인메모리 Task 캐시 ────────────────────────────────────────────────────────
_tasks_cache: list[Task] = []


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
    page_size: int = Query(50, ge=1, le=500),
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
    page_size: int = Query(50, ge=1, le=500),
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
    page_size: int = Query(50, ge=1, le=500),
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
    ai_count     = sum(1 for r in results_store.values() if r.label == "AI 수행 가능")
    hybrid_count = sum(1 for r in results_store.values() if r.label == "AI + Human")
    human_count  = sum(1 for r in results_store.values() if r.label == "인간 수행 필요")
    unclassified_count = total - ai_count - hybrid_count - human_count

    l3_map: dict[str, dict] = {}
    for t in _tasks_cache:
        if t.l3 not in l3_map:
            l3_map[t.l3] = {"l3": t.l3, "total": 0, "ai": 0, "hybrid": 0, "human": 0}
        l3_map[t.l3]["total"] += 1
        r = results_store.get(t.id)
        if r:
            if r.label == "AI 수행 가능":
                l3_map[t.l3]["ai"] += 1
            elif r.label == "AI + Human":
                l3_map[t.l3]["hybrid"] += 1
            elif r.label == "인간 수행 필요":
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
               "분류결과", "적용기준(Knock-out)", "판단근거", "수동수정여부"]
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
        edited    = "Y" if (r and r.manually_edited) else ""
        row = [t.id, t.l2, t.l3, t.l4, t.name, t.description, t.performer[:100],
               label, criterion, reason, edited]
        ws.append(row)

        last_row = ws.max_row
        label_cell = ws.cell(row=last_row, column=8)
        if label == "AI 수행 가능":
            label_cell.fill = ai_fill
        elif label == "AI + Human":
            label_cell.fill = hybrid_fill
        elif label == "인간 수행 필요":
            label_cell.fill = human_fill

    col_widths = [12, 10, 14, 14, 28, 45, 35, 16, 28, 40, 10]
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
    ai_cnt   = sum(1 for r in results_store.values() if r.label == "AI 수행 가능")
    hyb_cnt  = sum(1 for r in results_store.values() if r.label == "AI + Human")
    hum_cnt  = sum(1 for r in results_store.values() if r.label == "인간 수행 필요")
    rows = [
        ["항목", "값"],
        ["모델", provider_label],
        ["전체 Task", total],
        ["AI 수행 가능", ai_cnt],
        ["AI + Human", hyb_cnt],
        ["인간 수행 필요", hum_cnt],
        ["미분류", total - ai_cnt - hyb_cnt - hum_cnt],
        ["AI 수행 가능 비율", f"{ai_cnt/total*100:.1f}%" if total else "0%"],
        ["AI + Human 비율", f"{hyb_cnt/total*100:.1f}%" if total else "0%"],
    ]
    for row in rows:
        ws2.append(row)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    filename = f"classification_{provider}.xlsx"
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
        headers={"Content-Disposition": "attachment; filename=classification_compare.xlsx"},
    )


# ─────────────────────────────────────────────────────────────────────────────
# 엑셀 업로드
# ─────────────────────────────────────────────────────────────────────────────

_UPLOAD_DIR = Path(__file__).parent / "uploads"
_UPLOAD_DIR.mkdir(exist_ok=True)
_current_excel_path: Path | None = None


@app.get("/api/upload/current", tags=["Upload"])
async def get_current_file():
    from excel_reader import _find_excel
    try:
        if _current_excel_path and _current_excel_path.exists():
            path = _current_excel_path
        else:
            try:
                path = _find_excel(_UPLOAD_DIR)
            except FileNotFoundError:
                path = _find_excel(Path(__file__).parent)
        return {
            "filename": path.name,
            "size_kb": round(path.stat().st_size / 1024, 1),
            "task_count": len(_tasks_cache),
        }
    except FileNotFoundError:
        return {"filename": None, "size_kb": 0, "task_count": 0}


@app.post("/api/upload", tags=["Upload"])
async def upload_excel(file: UploadFile = File(...)):
    global _tasks_cache, _current_excel_path

    if not file.filename or not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail=".xlsx 파일만 업로드 가능합니다.")

    save_path = _UPLOAD_DIR / file.filename
    try:
        contents = await file.read()
        save_path.write_bytes(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 저장 실패: {e}")

    try:
        new_tasks = load_tasks(save_path)
    except Exception as e:
        save_path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=f"엑셀 파싱 실패: {e}")

    _tasks_cache = new_tasks
    _current_excel_path = save_path

    return {
        "message": "업로드 성공",
        "filename": file.filename,
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

    if not _workflow_cache:
        # 파일에서 로드 시도
        save_path = Path(__file__).parent / "workflow.json"
        if save_path.exists():
            data = json.loads(save_path.read_text(encoding="utf-8"))
            parsed = parse_workflow_json(data)
            summary = get_workflow_summary(parsed)
            global _workflow_cache
            _workflow_cache = {
                "filename": save_path.name,
                "parsed": parsed,
                "summary": summary,
                "raw": data,
            }
        else:
            raise HTTPException(404, "업로드된 워크플로우가 없습니다.")

    return _workflow_cache["summary"]


@app.get("/api/workflow/sheets", tags=["Workflow"])
async def list_workflow_sheets():
    """워크플로우 시트 목록을 반환합니다."""
    if not _workflow_cache:
        raise HTTPException(404, "업로드된 워크플로우가 없습니다.")

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
    if not _workflow_cache:
        raise HTTPException(404, "업로드된 워크플로우가 없습니다.")

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
    if not _workflow_cache:
        raise HTTPException(404, "업로드된 워크플로우가 없습니다.")

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
    from ppt_parser import parse_ppt, match_nodes_to_tasks, ppt_slide_to_react_flow

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

    # 워크플로우 캐시에 PPT 결과도 저장
    global _workflow_cache
    _workflow_cache["ppt"] = {
        "filename": file.filename,
        "parsed": parsed,
        "slides": slides_result,
    }

    return {
        "ok": True,
        "filename": file.filename,
        "slide_count": parsed.slide_count,
        "slides": slides_result,
    }


# ─────────────────────────────────────────────────────────────────────────────
# To-Be Workflow 생성
# ─────────────────────────────────────────────────────────────────────────────

@app.post("/api/workflow/generate-tobe", tags=["Workflow"])
async def generate_tobe_workflow(
    sheet_id: str = Query("default", description="As-Is 워크플로우 시트 ID"),
    provider: str = Query("openai", description="분류 결과 제공자 (openai | anthropic)"),
    process_name: str = Query("", description="프로세스 이름 (빈 값이면 시트 이름 사용)"),
):
    """As-Is 워크플로우 + 분류 결과 → To-Be Workflow 초안을 생성합니다."""
    from workflow_parser import parse_workflow_json, get_workflow_summary
    from tobe_generator import generate_tobe

    # 워크플로우 로드
    if not _workflow_cache:
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
        # 첫 번째 시트로 fallback
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

    # ClassificationResult → dict 변환
    classification_dict: dict[str, dict] = {}
    for tid, cr in results_store.items():
        # 태스크 이름도 포함 (매칭용)
        task = next((t for t in _tasks_cache if t.id == tid), None)
        classification_dict[tid] = {
            "label": cr.label,
            "reason": cr.reason,
            "hybrid_note": cr.hybrid_note,
            "input_types": cr.input_types,
            "output_types": cr.output_types,
            "task_name": task.name if task else "",
        }

    # To-Be 생성
    tobe = generate_tobe(
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
