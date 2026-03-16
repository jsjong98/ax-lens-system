"""
ppt_parser.py — PPT 파일에서 워크플로우 노드/엣지를 추출

PPT 슬라이드 내의 도형(사각형, 둥근사각형 등)을 노드로,
연결선(커넥터)을 엣지로 파싱합니다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.util import Emu
from pptx.enum.shapes import MSO_SHAPE_TYPE


# ── 데이터 모델 ───────────────────────────────────────────────────────────────

@dataclass
class PptNode:
    """PPT에서 추출한 노드."""
    id: str
    text: str
    slide_index: int
    left: float      # inches
    top: float        # inches
    width: float      # inches
    height: float     # inches
    shape_type: str = ""
    fill_color: str = ""
    font_color: str = ""

    @property
    def center_x(self) -> float:
        return self.left + self.width / 2

    @property
    def center_y(self) -> float:
        return self.top + self.height / 2


@dataclass
class PptEdge:
    """PPT에서 추출한 연결선."""
    id: str
    source_id: str | None = None
    target_id: str | None = None
    label: str = ""
    slide_index: int = 0


@dataclass
class PptSlide:
    """파싱된 슬라이드."""
    index: int
    title: str = ""
    nodes: list[PptNode] = field(default_factory=list)
    edges: list[PptEdge] = field(default_factory=list)


@dataclass
class ParsedPpt:
    """PPT 파싱 결과 전체."""
    filename: str
    slide_count: int
    slides: list[PptSlide] = field(default_factory=list)


# ── 파서 ──────────────────────────────────────────────────────────────────────

def parse_ppt(source: str | Path | bytes | BytesIO) -> ParsedPpt:
    """PPT 파일을 파싱하여 슬라이드별 노드/엣지를 추출합니다."""
    if isinstance(source, bytes):
        source = BytesIO(source)
    prs = Presentation(source)

    filename = ""
    if isinstance(source, (str, Path)):
        filename = Path(source).name

    slides: list[PptSlide] = []

    for slide_idx, slide in enumerate(prs.slides):
        ppt_slide = PptSlide(index=slide_idx)

        # 슬라이드 제목 추출
        if slide.shapes.title:
            ppt_slide.title = slide.shapes.title.text.strip()

        node_map: dict[int, PptNode] = {}  # shape_id → PptNode

        # 1차: 모든 도형을 순회하여 노드/엣지 분류
        for shape in slide.shapes:
            # 커넥터(연결선)
            if shape.shape_type == MSO_SHAPE_TYPE.FREEFORM or _is_connector(shape):
                edge = _parse_connector(shape, slide_idx, len(ppt_slide.edges))
                if edge:
                    ppt_slide.edges.append(edge)
                continue

            # 그룹 내 도형 처리
            if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
                for child in shape.shapes:
                    node = _parse_shape_as_node(child, slide_idx, len(node_map))
                    if node:
                        node_map[child.shape_id] = node
                continue

            # 일반 도형 → 노드 후보
            node = _parse_shape_as_node(shape, slide_idx, len(node_map))
            if node:
                node_map[shape.shape_id] = node

        ppt_slide.nodes = list(node_map.values())

        # 2차: 커넥터의 source/target을 shape_id → node_id로 매핑
        shape_id_to_node_id = {sid: n.id for sid, n in node_map.items()}
        for edge in ppt_slide.edges:
            if edge.source_id and edge.source_id.isdigit():
                edge.source_id = shape_id_to_node_id.get(int(edge.source_id), edge.source_id)
            if edge.target_id and edge.target_id.isdigit():
                edge.target_id = shape_id_to_node_id.get(int(edge.target_id), edge.target_id)

        # 엣지가 없으면 위치 기반으로 순서를 추론
        if not ppt_slide.edges and len(ppt_slide.nodes) > 1:
            ppt_slide.edges = _infer_edges_from_position(ppt_slide.nodes, slide_idx)

        slides.append(ppt_slide)

    return ParsedPpt(
        filename=filename,
        slide_count=len(slides),
        slides=slides,
    )


def _is_connector(shape: Any) -> bool:
    """도형이 연결선(커넥터)인지 판별합니다."""
    try:
        if hasattr(shape, 'begin_x') and hasattr(shape, 'end_x'):
            return True
        # XML 태그 확인
        tag = shape._element.tag if hasattr(shape, '_element') else ""
        if 'cxnSp' in tag:
            return True
    except Exception:
        pass
    return False


def _parse_connector(shape: Any, slide_idx: int, edge_idx: int) -> PptEdge | None:
    """커넥터 도형에서 엣지 정보를 추출합니다."""
    try:
        edge_id = f"edge-s{slide_idx}-{edge_idx}"

        # 커넥터의 연결 대상 추출
        source_id = None
        target_id = None

        el = shape._element
        # cNvCxnSpPr > stCxn, endCxn 에서 연결 대상 shape ID 추출
        ns = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
              'p': 'http://schemas.openxmlformats.org/presentationml/2006/main',
              'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}

        for cxn_tag in el.iter():
            tag_name = cxn_tag.tag.split('}')[-1] if '}' in cxn_tag.tag else cxn_tag.tag
            if tag_name == 'stCxn':
                source_id = cxn_tag.get('id')
            elif tag_name == 'endCxn':
                target_id = cxn_tag.get('id')

        # 텍스트 라벨 추출
        label = ""
        if hasattr(shape, 'text') and shape.text:
            label = shape.text.strip()

        return PptEdge(
            id=edge_id,
            source_id=source_id,
            target_id=target_id,
            label=label,
            slide_index=slide_idx,
        )
    except Exception:
        return None


def _parse_shape_as_node(shape: Any, slide_idx: int, node_idx: int) -> PptNode | None:
    """일반 도형을 노드로 변환합니다. 텍스트가 없으면 None."""
    try:
        # 텍스트가 없는 도형은 무시
        if not hasattr(shape, 'text') or not shape.text.strip():
            return None

        text = shape.text.strip()

        # 너무 짧거나 슬라이드 번호 등은 무시
        if len(text) < 2:
            return None

        # 위치/크기
        left = _emu_to_inches(shape.left) if shape.left else 0
        top = _emu_to_inches(shape.top) if shape.top else 0
        width = _emu_to_inches(shape.width) if shape.width else 0
        height = _emu_to_inches(shape.height) if shape.height else 0

        # 도형 유형
        shape_type = ""
        try:
            shape_type = str(shape.shape_type)
        except Exception:
            pass

        # 채우기 색상
        fill_color = _extract_fill_color(shape)

        node_id = f"ppt-s{slide_idx}-n{node_idx}"

        return PptNode(
            id=node_id,
            text=text,
            slide_index=slide_idx,
            left=left,
            top=top,
            width=width,
            height=height,
            shape_type=shape_type,
            fill_color=fill_color,
        )
    except Exception:
        return None


def _emu_to_inches(emu: int | None) -> float:
    """EMU(English Metric Unit)를 인치로 변환."""
    if emu is None:
        return 0.0
    return emu / 914400


def _extract_fill_color(shape: Any) -> str:
    """도형의 채우기 색상을 16진수로 추출합니다."""
    try:
        fill = shape.fill
        if fill and fill.type is not None:
            fc = fill.fore_color
            if fc and fc.rgb:
                return str(fc.rgb)
    except Exception:
        pass
    return ""


def _infer_edges_from_position(
    nodes: list[PptNode], slide_idx: int
) -> list[PptEdge]:
    """
    커넥터가 없을 때 노드 위치 기반으로 순서를 추론합니다.
    Y좌표 기준 정렬 후, 같은 Y 레벨(±0.5인치)은 병렬로 묶고
    다른 레벨 간에는 순차 엣지를 생성합니다.
    """
    Y_THRESHOLD = 0.5  # inches

    # Y좌표 기준 레벨 그룹핑
    sorted_nodes = sorted(nodes, key=lambda n: (n.center_y, n.center_x))

    levels: list[list[PptNode]] = []
    current_level: list[PptNode] = [sorted_nodes[0]]
    current_y = sorted_nodes[0].center_y

    for node in sorted_nodes[1:]:
        if abs(node.center_y - current_y) <= Y_THRESHOLD:
            current_level.append(node)
        else:
            levels.append(current_level)
            current_level = [node]
            current_y = node.center_y
    levels.append(current_level)

    # 레벨 간 순차 엣지 생성
    edges: list[PptEdge] = []
    edge_idx = 0
    for i in range(len(levels) - 1):
        for src in levels[i]:
            for tgt in levels[i + 1]:
                edges.append(PptEdge(
                    id=f"inferred-s{slide_idx}-{edge_idx}",
                    source_id=src.id,
                    target_id=tgt.id,
                    slide_index=slide_idx,
                ))
                edge_idx += 1

    return edges


# ── 노드-태스크 매칭 ──────────────────────────────────────────────────────────

def match_nodes_to_tasks(
    nodes: list[PptNode],
    tasks: list[dict],
) -> list[dict]:
    """
    PPT 노드 텍스트를 태스크 목록과 매칭합니다.

    매칭 전략:
      1. 정확한 ID 매칭 (노드 텍스트에 "1.1.1" 같은 ID 포함)
      2. 이름 유사도 매칭 (부분 문자열)
      3. 매칭 안 되면 unmatched

    tasks: [{"id": "1.1.1.1", "name": "...", "l4": "...", "l4_id": "..."}, ...]
    """
    results = []
    for node in nodes:
        best_match = _find_best_match(node.text, tasks)
        results.append({
            "node_id": node.id,
            "node_text": node.text,
            "position": {"x": node.center_x, "y": node.center_y},
            "matched_task_id": best_match["id"] if best_match else None,
            "matched_task_name": best_match["name"] if best_match else None,
            "matched_level": best_match.get("level", "") if best_match else None,
            "match_confidence": best_match["score"] if best_match else 0,
        })

    return results


def _find_best_match(node_text: str, tasks: list[dict]) -> dict | None:
    """노드 텍스트에 가장 잘 매칭되는 태스크를 찾습니다."""
    text = node_text.strip()
    best: dict | None = None
    best_score = 0.0

    for task in tasks:
        score = 0.0
        task_id = task.get("id", "")
        task_name = task.get("name", "")
        task_l4 = task.get("l4", "")
        task_l4_id = task.get("l4_id", "")

        # 1. ID가 텍스트에 포함
        if task_id and task_id in text:
            score = 0.95
        elif task_l4_id and task_l4_id in text:
            score = 0.90

        # 2. 이름 완전 일치
        if not score and task_name and task_name == text:
            score = 0.95
        elif not score and task_l4 and task_l4 == text:
            score = 0.90

        # 3. 이름이 텍스트에 포함 (또는 반대)
        if not score and task_name:
            # 텍스트에서 줄바꿈/공백 정규화
            norm_text = re.sub(r'\s+', ' ', text).strip()
            norm_name = re.sub(r'\s+', ' ', task_name).strip()

            if norm_name in norm_text or norm_text in norm_name:
                # 길이 비율로 매칭 품질 계산
                overlap = len(norm_name) / max(len(norm_text), 1)
                score = min(0.85, 0.5 + overlap * 0.35)

        if not score and task_l4:
            norm_text = re.sub(r'\s+', ' ', text).strip()
            norm_l4 = re.sub(r'\s+', ' ', task_l4).strip()
            if norm_l4 in norm_text or norm_text in norm_l4:
                overlap = len(norm_l4) / max(len(norm_text), 1)
                score = min(0.80, 0.4 + overlap * 0.35)

        if score > best_score:
            best_score = score
            level = "L5" if task.get("id", "").count(".") >= 3 else "L4"
            best = {"id": task_id, "name": task_name, "score": score, "level": level}

    # 최소 임계값
    if best and best_score < 0.4:
        return None

    return best


# ── React Flow 변환 ───────────────────────────────────────────────────────────

def ppt_slide_to_react_flow(
    slide: PptSlide,
    scale: float = 100.0,
) -> dict:
    """PptSlide를 React Flow 호환 nodes/edges JSON으로 변환합니다."""
    nodes = []
    for node in slide.nodes:
        nodes.append({
            "id": node.id,
            "type": "l4",  # 기본값, 매칭 후 업데이트 가능
            "position": {
                "x": node.left * scale,
                "y": node.top * scale,
            },
            "data": {
                "label": node.text,
                "level": "L4",
                "id": "",
                "description": "",
                "source": "ppt",
            },
        })

    edges = []
    for edge in slide.edges:
        if edge.source_id and edge.target_id:
            edges.append({
                "id": edge.id,
                "source": edge.source_id,
                "target": edge.target_id,
                "type": "smoothstep",
                "animated": True,
                "label": edge.label,
                "style": {"stroke": "#a62121", "strokeWidth": 2},
                "markerEnd": {
                    "type": "arrowclosed",
                    "width": 20,
                    "height": 20,
                    "color": "#a62121",
                },
            })

    return {
        "nodes": nodes,
        "edges": edges,
        "slide_title": slide.title,
    }
