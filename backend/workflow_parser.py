"""
workflow_parser.py — As-Is Workflow JSON 파서

hr-workflow-ai에서 내보낸 JSON 파일을 읽어
노드 목록, 엣지 목록, 순서(순차/병렬) 구조를 분석합니다.

JSON 포맷:
  v2.0 (multi-sheet): { version, sheets: [{ id, name, nodes, edges, lanes }] }
  v1.0 (single):      { version, nodes, edges }
"""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ── 데이터 모델 ───────────────────────────────────────────────────────────────

@dataclass
class WorkflowNode:
    """워크플로우 상의 개별 노드 (L2/L3/L4/L5)."""
    id: str
    level: str          # "L2", "L3", "L4", "L5"
    task_id: str        # 원본 프로세스 ID (예: "1.6.1")
    label: str
    description: str = ""
    position_x: float = 0.0
    position_y: float = 0.0
    metadata: dict = field(default_factory=dict)

    @property
    def y(self) -> float:
        return self.position_y

    @property
    def x(self) -> float:
        return self.position_x


@dataclass
class WorkflowEdge:
    """노드 간 연결."""
    id: str
    source: str
    target: str
    label: str = ""
    animated: bool = False
    bidirectional: bool = False   # 양방향 화살표 (협의/상호작용 관계)


@dataclass
class ExecutionStep:
    """실행 순서 상의 하나의 '단계'. 병렬이면 node_ids가 2개 이상."""
    step_number: int
    node_ids: list[str]
    is_parallel: bool = False

    def __repr__(self) -> str:
        if self.is_parallel:
            return f"Step {self.step_number}: [{' || '.join(self.node_ids)}] (병렬)"
        return f"Step {self.step_number}: {self.node_ids[0]}"


@dataclass
class WorkflowSheet:
    """하나의 워크플로우 시트 (= 하나의 프로세스 맵)."""
    sheet_id: str
    name: str
    nodes: dict[str, WorkflowNode] = field(default_factory=dict)
    edges: list[WorkflowEdge] = field(default_factory=list)
    lanes: list[str] = field(default_factory=list)
    lane_heights: list[float] = field(default_factory=list)   # 사용자가 드래그로 조정한 lane 높이 (없으면 빈 리스트)
    swim_height: float = 0.0   # 전체 swim 영역 높이 (선택)
    sheet_type: str = ""    # "swimlane" 등
    execution_order: list[ExecutionStep] = field(default_factory=list)

    @property
    def l4_nodes(self) -> list[WorkflowNode]:
        return sorted(
            [n for n in self.nodes.values() if n.level == "L4"],
            key=lambda n: n.y,
        )

    @property
    def l5_nodes(self) -> list[WorkflowNode]:
        return sorted(
            [n for n in self.nodes.values() if n.level == "L5"],
            key=lambda n: n.y,
        )

    @property
    def decision_nodes(self) -> list[WorkflowNode]:
        return [n for n in self.nodes.values() if n.level == "DECISION"]

    def outgoing_edges(self, node_id: str) -> list[WorkflowEdge]:
        """특정 노드에서 나가는 엣지 목록을 반환합니다."""
        return [e for e in self.edges if e.source == node_id]

    def incoming_edges(self, node_id: str) -> list[WorkflowEdge]:
        """특정 노드로 들어오는 엣지 목록을 반환합니다."""
        return [e for e in self.edges if e.target == node_id]


@dataclass
class ParsedWorkflow:
    """파싱 결과 전체."""
    version: str
    sheets: list[WorkflowSheet] = field(default_factory=list)


# ── 파서 ──────────────────────────────────────────────────────────────────────

def parse_workflow_json(data: dict | str | Path) -> ParsedWorkflow:
    """JSON 데이터(dict), JSON 문자열, 또는 파일 경로에서 워크플로우를 파싱합니다."""
    if isinstance(data, (str, Path)):
        path = Path(data)
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
        else:
            data = json.loads(data)  # JSON 문자열로 시도

    version = data.get("version", "1.0")

    if version.startswith("2"):
        raw_sheets = data.get("sheets", [])
    else:
        # v1.0: 단일 시트
        raw_sheets = [{
            "id": "default",
            "name": "기본",
            "nodes": data.get("nodes", []),
            "edges": data.get("edges", []),
            "lanes": data.get("lanes", []),
        }]

    sheets = []
    for rs in raw_sheets:
        sheet = _parse_sheet(rs)
        sheet.execution_order = _analyze_execution_order(sheet)
        sheets.append(sheet)

    return ParsedWorkflow(version=version, sheets=sheets)


def _parse_sheet(raw: dict) -> WorkflowSheet:
    """개별 시트를 파싱합니다."""
    # laneHeights: [240, 400, 380, ...] — 사용자가 드래그로 조정한 lane 높이
    raw_lane_heights = raw.get("laneHeights") or raw.get("lane_heights") or []
    lane_heights: list[float] = []
    for h in raw_lane_heights:
        try:
            lane_heights.append(float(h))
        except (TypeError, ValueError):
            continue

    sheet = WorkflowSheet(
        sheet_id=raw.get("id", "default"),
        name=raw.get("name", ""),
        lanes=raw.get("lanes", []),
        lane_heights=lane_heights,
        swim_height=float(raw.get("swimHeight") or 0),
        sheet_type=str(raw.get("type") or ""),
    )

    for rn in raw.get("nodes", []):
        node = _parse_node(rn)
        if node:
            sheet.nodes[node.id] = node

    for re_ in raw.get("edges", []):
        edge = _parse_edge(re_)
        if edge:
            sheet.edges.append(edge)

    return sheet


def _parse_node(raw: dict) -> WorkflowNode | None:
    """원시 노드 dict를 WorkflowNode로 변환합니다."""
    node_id = raw.get("id", "")
    if not node_id:
        return None

    data = raw.get("data", {})
    position = raw.get("position", {})

    level = data.get("level", raw.get("type", "L4")).upper()
    if level not in ("L2", "L3", "L4", "L5", "DECISION", "MEMO"):
        level = "L4"

    # 메타데이터 (actors, systems, painPoints 등)
    # LevelNode 렌더링에 필요한 모든 키 + 계층 정보
    meta_keys = (
        "actors", "systems", "painPoints", "inputs", "outputs", "logic",
        "mgrBody", "staffCount", "mainPerson", "avgTime", "freqCount",
        "memo", "role", "inputData", "outputData", "system",
        # 계층 정보 (LevelNode가 표시에 사용)
        "l2Id", "l2Name", "l3Id", "l3Name", "l4Id", "l4Name",
    )
    metadata = {k: data[k] for k in meta_keys if k in data}

    # swimlane 액터 — "그 외:큐벡스" 같은 고유명사 포함
    # hr-workflow-ai는 role 필드에 "HR 담당자 / HR 임원" 또는 "그 외:큐벡스" 형태로 저장
    raw_role = data.get("role", "")
    if raw_role and "role" not in metadata:
        metadata["role"] = raw_role

    return WorkflowNode(
        id=node_id,
        level=level,
        task_id=data.get("id", ""),
        label=data.get("label", ""),
        description=data.get("description", ""),
        position_x=float(position.get("x", 0)),
        position_y=float(position.get("y", 0)),
        metadata=metadata,
    )


def _parse_edge(raw: dict) -> WorkflowEdge | None:
    """원시 엣지 dict를 WorkflowEdge로 변환합니다."""
    edge_id = raw.get("id", "")
    source = raw.get("source", "")
    target = raw.get("target", "")
    if not (edge_id and source and target):
        return None

    # 양방향 화살표 감지:
    # hr-workflow-ai는 markerStart가 있거나 bidirectional: true이면 양방향
    is_bidir = (
        raw.get("bidirectional", False)
        or bool(raw.get("markerStart"))
        or (isinstance(raw.get("data"), dict) and raw["data"].get("bidirectional", False))
    )

    return WorkflowEdge(
        id=edge_id,
        source=source,
        target=target,
        label=raw.get("label", ""),
        animated=raw.get("animated", False),
        bidirectional=is_bidir,
    )


# ── 순서 분석 ─────────────────────────────────────────────────────────────────

def _analyze_execution_order(sheet: WorkflowSheet) -> list[ExecutionStep]:
    """
    엣지 기반 위상 정렬(topological sort)로 실행 순서를 분석합니다.
    같은 "층"에 있는 노드(동일 in-degree 해소 시점)는 병렬로 판정합니다.

    L4 노드만 대상으로 분석합니다 (메인 프로세스 흐름).
    """
    l4_ids = {n.id for n in sheet.nodes.values() if n.level == "L4"}
    if not l4_ids:
        # L4가 없으면 L5 노드로 실행 순서 분석
        l5_ids = {n.id for n in sheet.nodes.values() if n.level == "L5"}
        if l5_ids:
            return _analyze_execution_order_for_level(sheet, l5_ids)
        # L5도 없으면 모든 노드 사용
        all_ids = set(sheet.nodes.keys())
        if all_ids:
            return _analyze_execution_order_for_level(sheet, all_ids)
        return []

    return _analyze_execution_order_for_level(sheet, l4_ids)


def _analyze_execution_order_for_level(
    sheet: WorkflowSheet, target_ids: set[str]
) -> list[ExecutionStep]:
    """특정 레벨의 노드들로 실행 순서를 분석합니다."""
    # 해당 레벨 간 엣지만 추출
    adj: dict[str, list[str]] = defaultdict(list)
    in_degree: dict[str, int] = {nid: 0 for nid in target_ids}

    for edge in sheet.edges:
        if edge.source in target_ids and edge.target in target_ids:
            adj[edge.source].append(edge.target)
            in_degree[edge.target] = in_degree.get(edge.target, 0) + 1

    # 엣지가 없으면 Y좌표 기반 순서로 fallback
    if not any(adj.values()):
        return _fallback_position_order(sheet, target_ids)

    # Kahn's algorithm (BFS 위상 정렬) — 레벨별로 그룹핑
    steps: list[ExecutionStep] = []
    queue = [nid for nid in target_ids if in_degree[nid] == 0]
    step_num = 1

    while queue:
        # 같은 레벨의 노드들 = 병렬 실행 가능
        is_parallel = len(queue) > 1
        steps.append(ExecutionStep(
            step_number=step_num,
            node_ids=sorted(queue, key=lambda x: sheet.nodes[x].x if x in sheet.nodes else 0),
            is_parallel=is_parallel,
        ))

        next_queue = []
        for nid in queue:
            for neighbor in adj[nid]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    next_queue.append(neighbor)

        queue = next_queue
        step_num += 1

    # 엣지에 연결되지 않은 고립 노드 처리
    visited = {nid for step in steps for nid in step.node_ids}
    orphans = target_ids - visited
    if orphans:
        orphan_nodes = sorted(orphans, key=lambda x: sheet.nodes[x].y if x in sheet.nodes else 0)
        steps.append(ExecutionStep(
            step_number=step_num,
            node_ids=orphan_nodes,
            is_parallel=len(orphan_nodes) > 1,
        ))

    return steps


def _fallback_position_order(
    sheet: WorkflowSheet, l4_ids: set[str]
) -> list[ExecutionStep]:
    """
    엣지 정보가 없을 때 Y좌표 기반으로 순서를 추론합니다.
    Y좌표가 비슷한 노드(±50px)는 병렬로 판정합니다.
    """
    Y_THRESHOLD = 50  # 이 범위 안에 있으면 같은 층으로 간주

    l4_sorted = sorted(
        [sheet.nodes[nid] for nid in l4_ids if nid in sheet.nodes],
        key=lambda n: (n.y, n.x),
    )

    if not l4_sorted:
        return []

    steps: list[ExecutionStep] = []
    current_group: list[str] = [l4_sorted[0].id]
    current_y = l4_sorted[0].y

    for node in l4_sorted[1:]:
        if abs(node.y - current_y) <= Y_THRESHOLD:
            current_group.append(node.id)
        else:
            steps.append(ExecutionStep(
                step_number=len(steps) + 1,
                node_ids=current_group,
                is_parallel=len(current_group) > 1,
            ))
            current_group = [node.id]
            current_y = node.y

    steps.append(ExecutionStep(
        step_number=len(steps) + 1,
        node_ids=current_group,
        is_parallel=len(current_group) > 1,
    ))

    return steps


# ── 요약 ──────────────────────────────────────────────────────────────────────

def get_workflow_summary(parsed: ParsedWorkflow) -> dict[str, Any]:
    """파싱된 워크플로우의 요약 정보를 반환합니다."""
    summaries = []
    for sheet in parsed.sheets:
        l4_nodes = sheet.l4_nodes
        l5_nodes = sheet.l5_nodes
        decision_nodes = sheet.decision_nodes

        # L4→L5 매핑 (엣지 기반)
        l4_to_l5: dict[str, list[str]] = defaultdict(list)
        for edge in sheet.edges:
            src = sheet.nodes.get(edge.source)
            tgt = sheet.nodes.get(edge.target)
            if src and tgt and src.level == "L4" and tgt.level == "L5":
                l4_to_l5[src.id].append(tgt.id)

        # 병렬 스텝 수
        parallel_steps = [s for s in sheet.execution_order if s.is_parallel]

        # L4별 분기(Decision) 정보 구성
        def _get_branches(node_id: str, visited: set | None = None) -> list[dict]:
            """노드 → Decision 노드 → 분기 조건 + 다음 노드를 재귀적으로 수집."""
            if visited is None:
                visited = set()
            if node_id in visited:
                return []
            visited.add(node_id)
            branches = []
            for e in sheet.outgoing_edges(node_id):
                tgt = sheet.nodes.get(e.target)
                if not tgt:
                    continue
                if tgt.level == "DECISION":
                    # Decision 노드에서 나가는 엣지 = 분기 조건
                    decision_branches = []
                    for de in sheet.outgoing_edges(tgt.id):
                        dtgt = sheet.nodes.get(de.target)
                        decision_branches.append({
                            "condition": de.label or "(조건 없음)",
                            "target_node_id": de.target,
                            "target_label": dtgt.label if dtgt else de.target,
                            "target_level": dtgt.level if dtgt else "",
                        })
                    branches.append({
                        "type": "decision",
                        "decision_node_id": tgt.id,
                        "decision_label": tgt.label or "분기",
                        "branches": decision_branches,
                    })
                elif e.label:
                    # 라벨 있는 일반 엣지
                    branches.append({
                        "type": "edge",
                        "condition": e.label,
                        "target_node_id": e.target,
                        "target_label": tgt.label,
                        "target_level": tgt.level,
                    })
            return branches

        summaries.append({
            "sheet_id": sheet.sheet_id,
            "sheet_name": sheet.name,
            "lanes": sheet.lanes,
            "total_nodes": len(sheet.nodes),
            "l4_count": len(l4_nodes),
            "l5_count": len(l5_nodes),
            "decision_count": len(decision_nodes),
            "edge_count": len(sheet.edges),
            "total_steps": len(sheet.execution_order),
            "parallel_steps": len(parallel_steps),
            "sequential_steps": len(sheet.execution_order) - len(parallel_steps),
            "execution_order": [
                {
                    "step": s.step_number,
                    "nodes": [
                        {
                            "node_id": nid,
                            "task_id": sheet.nodes[nid].task_id if nid in sheet.nodes else "",
                            "label": sheet.nodes[nid].label if nid in sheet.nodes else "",
                        }
                        for nid in s.node_ids
                    ],
                    "is_parallel": s.is_parallel,
                }
                for s in sheet.execution_order
            ],
            "l4_details": [
                {
                    "node_id": n.id,
                    "task_id": n.task_id,
                    "label": n.label,
                    "description": n.description,
                    "child_l5_count": len(l4_to_l5.get(n.id, [])),
                    "child_l5s": [
                        {
                            "node_id": l5id,
                            "task_id": sheet.nodes[l5id].task_id if l5id in sheet.nodes else "",
                            "label": sheet.nodes[l5id].label if l5id in sheet.nodes else "",
                        }
                        for l5id in l4_to_l5.get(n.id, [])
                    ],
                    "branches": _get_branches(n.id),
                }
                for n in l4_nodes
            ],
            "decision_nodes": [
                {
                    "node_id": n.id,
                    "label": n.label or "분기",
                    "description": n.description,
                    "incoming": [
                        {
                            "from_node_id": e.source,
                            "from_label": sheet.nodes[e.source].label if e.source in sheet.nodes else e.source,
                            "condition": e.label,
                        }
                        for e in sheet.incoming_edges(n.id)
                    ],
                    "outgoing": [
                        {
                            "condition": e.label or "(조건 없음)",
                            "to_node_id": e.target,
                            "to_label": sheet.nodes[e.target].label if e.target in sheet.nodes else e.target,
                        }
                        for e in sheet.outgoing_edges(n.id)
                    ],
                }
                for n in decision_nodes
            ],
        })

    return {
        "version": parsed.version,
        "sheet_count": len(parsed.sheets),
        "sheets": summaries,
    }
