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

# .env 파일 자동 로드 (python-dotenv 없어도 동작하는 fallback 포함)
def _load_dotenv() -> None:
    env_path = Path(__file__).parent / ".env"
    if not env_path.exists():
        return
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path, override=False)
    except ImportError:
        # python-dotenv 미설치 시 직접 파싱
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

# ── 앱 초기화 ────────────────────────────────────────────────────────────────

app = FastAPI(
    title="HR Task 분류 API",
    description="HR As-Is 프로세스의 L5 Task를 AI/인간 분류하는 API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 인메모리 Task 캐시 (파일 업로드 시 로드) ──────────────────────────────────
# 앱 시작 시 자동 로드하지 않음. 사용자가 엑셀 파일을 업로드해야 Task가 로드됩니다.
_tasks_cache: list[Task] = []


# ─────────────────────────────────────────────────────────────────────────────
# Task 엔드포인트
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/tasks", response_model=TaskListResponse, tags=["Tasks"])
async def get_tasks(
    search: Optional[str] = Query(None, description="Task명/설명 검색어"),
    l2: Optional[str] = Query(None, description="L2 필터"),
    l3: Optional[str] = Query(None, description="L3 필터"),
    l4: Optional[str] = Query(None, description="L4 필터"),
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
    """L2/L3/L4 필터 선택지를 반환합니다."""
    l2_set: dict[str, str] = {}
    l3_set: dict[str, str] = {}
    l4_set: dict[str, str] = {}

    for t in _tasks_cache:
        l2_set[t.l2_id] = t.l2
        l3_set[t.l3_id] = t.l3
        l4_set[t.l4_id] = t.l4

    return {
        "l2": [{"id": k, "name": v} for k, v in sorted(l2_set.items())],
        "l3": [{"id": k, "name": v} for k, v in sorted(l3_set.items())],
        "l4": [{"id": k, "name": v} for k, v in sorted(l4_set.items())],
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
    Task를 분류합니다. Server-Sent Events (SSE) 형식으로 진행 상황을 스트리밍합니다.

    각 이벤트 형식:
      data: {"type": "progress", "task_id": "...", "current": N, "total": M, "result": {...}}
      data: {"type": "done", "total": M}
      data: {"type": "error", "message": "..."}
    """
    settings = req.settings or load_settings()

    # 프론트엔드에서 마스킹된 API Key(sk-***...)가 넘어오면 저장된 실제 키로 교체
    if settings.api_key and settings.api_key.startswith("sk-" + "*"):
        stored = load_settings()
        settings.api_key = stored.api_key

    # 분류할 Task 목록 결정
    if req.task_ids:
        id_set = set(req.task_ids)
        tasks = [t for t in _tasks_cache if t.id in id_set]
    else:
        tasks = list(_tasks_cache)

    if not tasks:
        raise HTTPException(status_code=400, detail="분류할 Task가 없습니다.")

    classifier = get_classifier(settings)
    results_store = load_results()
    total = len(tasks)

    async def event_generator():
        current = 0
        try:
            async for result in classifier.classify_stream(tasks, settings):
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

            # 완료 후 저장
            save_results(results_store)
            yield f"data: {json.dumps({'type': 'done', 'total': current}, ensure_ascii=False)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# 결과 엔드포인트
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/results", response_model=ResultsResponse, tags=["Results"])
async def get_results(
    label: Optional[str] = Query(None, description="레이블 필터 (AI 수행 가능|AI + Human|인간 수행 필요|미분류)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
):
    results_store = load_results()
    results = list(results_store.values())

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


@app.put("/api/results/{task_id}", response_model=ClassificationResult, tags=["Results"])
async def update_result(task_id: str, update: ClassificationResultUpdate):
    """분류 결과를 수동으로 수정합니다."""
    results_store = load_results()
    existing = results_store.get(task_id)

    if existing is None:
        existing = ClassificationResult(task_id=task_id)

    existing.label = update.label
    if update.reason is not None:
        existing.reason = update.reason
    existing.manually_edited = True

    upsert_result(existing)
    return existing


@app.delete("/api/results", tags=["Results"])
async def delete_all_results():
    """모든 분류 결과를 초기화합니다."""
    clear_results()
    return {"message": "결과가 초기화되었습니다."}


@app.get("/api/results/stats", response_model=StatsResponse, tags=["Results"])
async def get_stats():
    results_store = load_results()
    total = len(_tasks_cache)
    ai_count     = sum(1 for r in results_store.values() if r.label == "AI 수행 가능")
    hybrid_count = sum(1 for r in results_store.values() if r.label == "AI + Human")
    human_count  = sum(1 for r in results_store.values() if r.label == "인간 수행 필요")
    unclassified_count = total - ai_count - hybrid_count - human_count

    # L3별 집계
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
    # API 키는 마스킹해서 반환
    masked = settings.model_copy()
    if masked.api_key:
        masked.api_key = "sk-" + "*" * 20
    return masked


@app.post("/api/settings", response_model=ClassifierSettings, tags=["Settings"])
async def update_settings(settings: ClassifierSettings):
    # 마스킹된 키가 들어오면 기존 키 유지
    if settings.api_key.startswith("sk-" + "*"):
        existing = load_settings()
        settings.api_key = existing.api_key
    save_settings(settings)
    masked = settings.model_copy()
    if masked.api_key:
        masked.api_key = "sk-" + "*" * 20
    return masked


# ─────────────────────────────────────────────────────────────────────────────
# 엑셀 내보내기
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/export", tags=["Export"])
async def export_results():
    """분류 결과를 엑셀 파일로 다운로드합니다."""
    results_store = load_results()
    task_map = {t.id: t for t in _tasks_cache}

    wb = openpyxl.Workbook()

    # ── 분류결과 시트 ──
    ws = wb.active
    ws.title = "분류결과"

    headers = ["L5_ID", "L2", "L3", "L4", "L5_Name", "L5_Description", "수행주체",
               "분류결과", "적용기준(Knock-out)", "판단근거", "수동수정여부"]
    ws.append(headers)

    header_fill = PatternFill("solid", fgColor="1F4E79")
    # AI 수행 가능 → 연분홍, AI + Human → 연노랑, 인간 수행 필요 → 연초록
    ai_fill     = PatternFill("solid", fgColor="FFE0E0")   # 연분홍
    hybrid_fill = PatternFill("solid", fgColor="FFF9DB")   # 연노랑
    human_fill  = PatternFill("solid", fgColor="D6F5E3")   # 연초록

    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = Font(bold=True, color="FFFFFF")
        cell.alignment = Alignment(horizontal="center")

    for t in _tasks_cache:
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

    # ── 요약 시트 ──
    ws2 = wb.create_sheet("요약")
    total    = len(_tasks_cache)
    ai_cnt   = sum(1 for r in results_store.values() if r.label == "AI 수행 가능")
    hyb_cnt  = sum(1 for r in results_store.values() if r.label == "AI + Human")
    hum_cnt  = sum(1 for r in results_store.values() if r.label == "인간 수행 필요")
    rows = [
        ["항목", "값"],
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

    # 바이트 스트림으로 저장
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=classification_results.xlsx"},
    )


# ─────────────────────────────────────────────────────────────────────────────
# 엑셀 업로드
# ─────────────────────────────────────────────────────────────────────────────

_UPLOAD_DIR = Path(__file__).parent / "uploads"
_UPLOAD_DIR.mkdir(exist_ok=True)

# 현재 로드된 엑셀 파일 경로 추적
_current_excel_path: Path | None = None


@app.get("/api/upload/current", tags=["Upload"])
async def get_current_file():
    """현재 로드된 엑셀 파일 정보를 반환합니다."""
    from excel_reader import _find_excel
    try:
        if _current_excel_path and _current_excel_path.exists():
            path = _current_excel_path
        else:
            # uploads 폴더 먼저, 그 다음 상위 디렉토리 탐색
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
    """
    엑셀 파일을 업로드하고 Task 목록을 새로 로드합니다.
    .xlsx 형식만 허용합니다.
    """
    global _tasks_cache, _current_excel_path

    if not file.filename or not file.filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail=".xlsx 파일만 업로드 가능합니다.")

    save_path = _UPLOAD_DIR / file.filename
    try:
        contents = await file.read()
        save_path.write_bytes(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 저장 실패: {e}")

    # 새 파일로 Task 재로드
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
    # .env 또는 settings.json 어느 쪽에든 API Key가 있으면 configured=True
    env_key = os.environ.get("OPENAI_API_KEY", "").strip()
    settings_key = load_settings().api_key.strip()
    api_key_configured = bool(env_key or settings_key)
    return {
        "status": "ok",
        "task_count": len(_tasks_cache),
        "api_key_configured": api_key_configured,
    }
