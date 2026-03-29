"""
ppt_exporter.py — 과제 정의서/설계서 PPT 내보내기

템플릿 PPT를 열어 데이터를 채운 뒤 BytesIO로 반환합니다.
템플릿 구조:
  Slide 1: 표지
  Slide 2: 과제 정의서 (섹션 1~6)
  Slide 3: 과제 설계서 (섹션 7~9)
  Slide 4: 별첨: Agent 정의서 (Agent별 복제)
  Slide 5: Thank You
"""
from __future__ import annotations

import copy
import io
from pathlib import Path
from typing import Any

from pptx import Presentation
from pptx.util import Inches, Pt, Emu, Cm
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from lxml import etree


TEMPLATE_PATH = Path(__file__).parent / "template.pptx"

PWC_RED = RGBColor(0xA6, 0x21, 0x21)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
BLACK = RGBColor(0x00, 0x00, 0x00)
GRAY = RGBColor(0x55, 0x55, 0x55)
DARK = RGBColor(0x33, 0x33, 0x33)


# ── 유틸 ──────────────────────────────────────────────────────────────────────

def _find_shape(slide_or_group, name: str):
    """슬라이드/그룹에서 이름으로 shape 검색 (재귀)."""
    shapes = slide_or_group.shapes if hasattr(slide_or_group, 'shapes') else []
    for shape in shapes:
        if shape.name == name:
            return shape
        if hasattr(shape, 'shapes'):
            found = _find_shape(shape, name)
            if found:
                return found
    return None


def _find_shapes_containing(slide_or_group, text_fragment: str) -> list:
    """텍스트를 포함하는 모든 shape 검색 (재귀)."""
    results = []
    shapes = slide_or_group.shapes if hasattr(slide_or_group, 'shapes') else []
    for shape in shapes:
        if shape.has_text_frame:
            full_text = shape.text_frame.text
            if text_fragment in full_text:
                results.append(shape)
        if hasattr(shape, 'shapes'):
            results.extend(_find_shapes_containing(shape, text_fragment))
    return results


def _set_text(shape, text: str, font_size: Pt | None = None, bold: bool | None = None,
              color: RGBColor | None = None, alignment=None):
    """Shape의 텍스트를 교체합니다. 기존 포맷을 최대한 보존합니다."""
    if not shape or not shape.has_text_frame:
        return
    tf = shape.text_frame
    # 첫 번째 paragraph의 포맷을 보존하면서 텍스트 교체
    if tf.paragraphs:
        para = tf.paragraphs[0]
        # 기존 run 포맷 보존
        if para.runs:
            run = para.runs[0]
            run.text = text
            if font_size is not None:
                run.font.size = font_size
            if bold is not None:
                run.font.bold = bold
            if color is not None:
                run.font.color.rgb = color
        else:
            para.text = text
        # 나머지 paragraph 제거 (XML 직접)
        for extra_para in list(tf.paragraphs)[1:]:
            extra_para._p.getparent().remove(extra_para._p)
        if alignment is not None:
            para.alignment = alignment


def _set_multiline_text(shape, lines: list[str], font_size=Pt(11), bold=False,
                        color=DARK, bullet_char="", line_spacing=1.2):
    """Shape에 여러 줄 텍스트를 설정합니다. 줄 수에 따라 폰트 자동 축소."""
    if not shape or not shape.has_text_frame:
        return
    tf = shape.text_frame
    tf.clear()
    tf.word_wrap = True
    # 줄 수에 따라 폰트 크기 자동 조절
    total_chars = sum(len(l) for l in lines)
    if len(lines) > 10 or total_chars > 300:
        font_size = Pt(6)
    elif len(lines) > 7 or total_chars > 200:
        font_size = Pt(7)
    elif len(lines) > 4 or total_chars > 120:
        font_size = Pt(8)
    elif len(lines) > 2:
        font_size = Pt(9)

    for i, line in enumerate(lines):
        if i == 0:
            para = tf.paragraphs[0]
        else:
            para = tf.add_paragraph()

        # bullet_char 중복 방지: 이미 •로 시작하면 추가하지 않음
        if bullet_char and not line.startswith(bullet_char):
            full_text = f"{bullet_char}{line}"
        else:
            full_text = line
        run = para.add_run()
        run.text = full_text
        run.font.size = font_size
        run.font.bold = bold
        run.font.color.rgb = color

        if line_spacing != 1.0:
            para.line_spacing = line_spacing


def _add_text_box(slide, left, top, width, height, text: str,
                  font_size=Pt(11), bold=False, color=DARK, word_wrap=True,
                  alignment=PP_ALIGN.LEFT):
    """슬라이드에 텍스트 박스를 추가합니다."""
    from pptx.util import Emu
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = word_wrap
    para = tf.paragraphs[0]
    para.alignment = alignment
    run = para.add_run()
    run.text = text
    run.font.size = font_size
    run.font.bold = bold
    run.font.color.rgb = color
    return txBox


def _add_multiline_textbox(slide, left, top, width, height, lines: list[str],
                           font_size=Pt(10), color=DARK, bullet="•", line_spacing=1.15):
    """여러 줄 텍스트 박스를 추가합니다."""
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True

    for i, line in enumerate(lines):
        if i == 0:
            para = tf.paragraphs[0]
        else:
            para = tf.add_paragraph()

        if bullet and not line.startswith(bullet):
            full_text = f"{bullet}{line}"
        else:
            full_text = line
        run = para.add_run()
        run.text = full_text
        run.font.size = font_size
        run.font.color.rgb = color
        para.line_spacing = line_spacing

    return txBox


def _add_grouped_textbox(slide, left, top, width, height, items: list[str],
                          font_size=Pt(7), color=DARK, line_spacing=1.0):
    """방법론용 텍스트 박스 — 각 항목 내 줄바꿈(\n)을 지원하며 들여쓰기 적용."""
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    first_para = True

    for item in items:
        sub_lines = item.split("\n")
        for k, sub in enumerate(sub_lines):
            if first_para:
                para = tf.paragraphs[0]
                first_para = False
            else:
                para = tf.add_paragraph()

            run = para.add_run()
            run.text = sub
            # 들여쓰기된 줄은 더 작은 폰트 + 회색
            if k > 0:
                run.font.size = Pt(max(font_size.pt - 1, 5))
                run.font.color.rgb = RGBColor(0x88, 0x87, 0x80)
                para.line_spacing = 0.95
            else:
                run.font.size = font_size
                run.font.color.rgb = color
                para.line_spacing = line_spacing

    return txBox


def _duplicate_slide(prs: Presentation, slide_index: int) -> Any:
    """슬라이드를 복제합니다 (XML 기반)."""
    template_slide = prs.slides[slide_index]
    slide_layout = template_slide.slide_layout

    # 새 슬라이드 추가
    new_slide = prs.slides.add_slide(slide_layout)

    # 기존 슬라이드의 XML을 복사
    for shape in new_slide.shapes:
        sp = shape._element
        sp.getparent().remove(sp)

    for shape in template_slide.shapes:
        el = copy.deepcopy(shape._element)
        new_slide.shapes._spTree.append(el)

    # 배경 복사
    if template_slide.background._element is not None:
        new_slide.background._element.getparent().replace(
            new_slide.background._element,
            copy.deepcopy(template_slide.background._element)
        )

    return new_slide


# ── 슬라이드 1: 표지 ──────────────────────────────────────────────────────────

def _fill_cover_slide(slide, project_title: str):
    """표지 슬라이드의 텍스트를 업데이트합니다."""
    # "AI 과제정의서" 텍스트가 있는 shape 찾기
    subtitle = _find_shape(slide, "Subtitle 3")
    if subtitle and subtitle.has_text_frame:
        for para in subtitle.text_frame.paragraphs:
            if "과제정의서" in para.text:
                for run in para.runs:
                    if "과제정의서" in run.text:
                        run.text = "AI 과제정의서"


# ── 슬라이드 2: 과제 정의서 ────────────────────────────────────────────────────

def _fill_definition_slide(slide, definition: dict):
    """과제 정의서 슬라이드에 데이터를 채웁니다."""
    project_number = definition.get("project_number", "")
    project_title = definition.get("project_title", "")
    created_date = definition.get("created_date", "")
    author = definition.get("author", "")

    # 헤더: "■ 과제번호/이름" 뒤에 제목 넣기
    header_shape = _find_shape(slide, "직사각형 7")
    if header_shape:
        _set_text(header_shape, f"■ 과제번호/이름     {project_number}. {project_title}")

    # 그룹 12 안의 입력 필드 텍스트 제거 (기존 "AI 자동화 과제/이름을입력해주세요" 제거)
    group12 = _find_shape(slide, "그룹 12")
    if group12 and hasattr(group12, 'shapes'):
        for sub in group12.shapes:
            if sub.has_text_frame:
                for para in sub.text_frame.paragraphs:
                    for run in para.runs:
                        run.text = ""

    # 작성일/작성자
    date_shape = _find_shape(slide, "직사각형 13")
    if date_shape:
        _set_text(date_shape, f"작성일: {created_date}   |   작성자: {author}")

    # 1. 과제 개요 — "ㅇㅇ" 플레이스홀더 → overview 리스트
    overview = definition.get("overview", [])
    overview_shape = _find_shape(slide, "직사각형 26")
    if overview_shape and overview:
        _set_multiline_text(overview_shape, overview, font_size=Pt(10), bullet_char="•", color=DARK)

    # 2. 매핑 프로세스 테이블
    table_shape = _find_shape(slide, "표 38")
    if table_shape and table_shape.has_table:
        tbl = table_shape.table
        processes = definition.get("mapping_processes", [])

        # 기존 행 삭제 후 데이터 채우기 (헤더행 + 데이터행)
        # 테이블은 5행 2열, 첫 행이 헤더
        for ri in range(1, min(len(processes) + 1, 5)):
            mp = processes[ri - 1] if ri - 1 < len(processes) else {}
            tbl.cell(ri, 0).text = mp.get("no", "")
            tbl.cell(ri, 1).text = mp.get("process_name", "")
            # task_range가 있으면 프로세스명 아래에 추가
            task_range = mp.get("task_range", "")
            if task_range:
                tbl.cell(ri, 1).text = f"{mp.get('process_name', '')}\n{task_range}"

            # 셀 폰트 설정
            for ci in range(2):
                cell = tbl.cell(ri, ci)
                for para in cell.text_frame.paragraphs:
                    for run in para.runs:
                        run.font.size = Pt(9)
                        run.font.color.rgb = DARK

    # 3. 이해관계자
    stakeholder = definition.get("stakeholder", {})
    # 과제 오너
    owner_val = _find_shape(slide, "직사각형 48")
    if owner_val:
        _set_text(owner_val, f": {stakeholder.get('project_owner', '')}")
    # 주관 부서
    dept_val = _find_shape(slide, "직사각형 52")
    if dept_val:
        _set_text(dept_val, f": {stakeholder.get('owner_department', '')}")
    # 협업 부서
    collab_val = _find_shape(slide, "직사각형 54")
    if collab_val:
        depts = stakeholder.get("collaborating_departments", [])
        _set_text(collab_val, f": {', '.join(depts) if depts else '없음'}")
    # 외부 파트너
    partner_val = _find_shape(slide, "직사각형 56")
    if partner_val:
        partners = stakeholder.get("external_partners", [])
        _set_text(partner_val, f": {', '.join(partners) if partners else '없음'}")

    # 4. 현황 및 문제점
    cvi = definition.get("current_vs_improvement", {})
    issues_shape = _find_shape(slide, "직사각형 74")
    if issues_shape:
        issues = cvi.get("current_issues", [])
        _set_multiline_text(issues_shape, issues, font_size=Pt(9), bullet_char="•", color=DARK)

    # 4. 개선 방향
    improve_shape = _find_shape(slide, "직사각형 75")
    if improve_shape:
        directions = cvi.get("improvement_directions", [])
        _set_multiline_text(improve_shape, directions, font_size=Pt(9), bullet_char="•", color=DARK)

    # 5. 기대 효과 — 정량적
    quant_shape = _find_shape(slide, "직사각형 99")
    if quant_shape:
        quants = definition.get("expected_effects", {}).get("quantitative", [])
        _set_multiline_text(quant_shape, quants, font_size=Pt(9), bullet_char="•", color=DARK)

    # 5. 기대 효과 — 정성적
    qual_shape = _find_shape(slide, "직사각형 94")
    if qual_shape:
        quals = definition.get("expected_effects", {}).get("qualitative", [])
        _set_multiline_text(qual_shape, quals, font_size=Pt(9), bullet_char="•", color=DARK)

    # 6. 과제 추진 시 고려사항
    consider_shape = _find_shape(slide, "직사각형 91")
    if consider_shape:
        considerations = definition.get("considerations", [])
        _set_multiline_text(consider_shape, considerations, font_size=Pt(9), bullet_char="•", color=DARK)


# ── 슬라이드 3: 과제 설계서 ────────────────────────────────────────────────────

def _fill_design_slide(slide, design: dict, definition: dict | None = None):
    """과제 설계서 슬라이드에 데이터를 채웁니다."""
    project_number = ""
    project_title = design.get("project_title", "")
    created_date = ""
    author = ""

    if definition:
        project_number = definition.get("project_number", "")
        created_date = definition.get("created_date", "")
        author = definition.get("author", "")

    # 헤더
    header_shape = _find_shape(slide, "직사각형 164")
    if header_shape:
        _set_text(header_shape, f"■ 과제번호/이름     {project_number}. {project_title}")

    title_input = _find_shape(slide, "직사각형 166")
    if title_input:
        _set_text(title_input, f"{project_number}. {project_title}")

    date_shape = _find_shape(slide, "직사각형 168")
    if date_shape:
        _set_text(date_shape, f"작성일: {created_date}   |   작성자: {author}")

    # 8. AI 기술 유형 — 기술 이름 (공통 기술 통합)
    tech_names_shape = _find_shape(slide, "직사각형 37")
    if tech_names_shape:
        tech_names_raw = design.get("ai_tech_info", {}).get("tech_names", [])
        # 공통 기술 키워드 추출 후 중복 통합
        seen_base = set()
        tech_names_merged: list[str] = []
        for tn in tech_names_raw:
            # "LLM + RAG", "LLM + Rule Engine" → 기본 기술(LLM)은 이미 있으면 조합만 추가
            base = tn.split("+")[0].split("·")[0].strip() if "+" in tn or "·" in tn else tn.strip()
            if base not in seen_base:
                seen_base.add(base)
            tech_names_merged.append(tn)
        # 최대 6개로 제한
        if len(tech_names_merged) > 6:
            tech_names_merged = tech_names_merged[:5] + [f"... 외 {len(tech_names_merged)-5}개"]
        _set_multiline_text(tech_names_shape, tech_names_merged, font_size=Pt(8), bullet_char="•", color=DARK)

    # 9. Input / Output
    io_data = design.get("input_output", {})

    # 내부 Input
    int_shapes = _find_shapes_containing(slide, "ㅇㅇ")
    # 그룹 1 내부의 ㅇㅇ shape들 — 직사각형 88, 89, 90
    io_88 = _find_shape(slide, "직사각형 88")
    if io_88:
        internals = io_data.get("input_internal", [])
        _set_multiline_text(io_88, internals, font_size=Pt(8), bullet_char="•", color=DARK)

    io_89 = _find_shape(slide, "직사각형 89")
    if io_89:
        externals = io_data.get("input_external", [])
        _set_multiline_text(io_89, externals, font_size=Pt(8), bullet_char="•", color=DARK)

    io_90 = _find_shape(slide, "직사각형 90")
    if io_90:
        outputs = io_data.get("output", [])
        _set_multiline_text(io_90, outputs, font_size=Pt(8), bullet_char="•", color=DARK)


# ── 슬라이드 4: Agent 정의서 ──────────────────────────────────────────────────

def _fill_agent_slide(slide, agent: dict, design: dict, definition: dict | None = None):
    """Agent 정의서 슬라이드에 데이터를 채웁니다."""
    created_date = definition.get("created_date", "") if definition else ""
    author = definition.get("author", "") if definition else ""

    # 작성일/작성자
    date_shape = _find_shape(slide, "직사각형 168")
    if date_shape:
        _set_text(date_shape, f"작성일: {created_date}   |   작성자: {author}")

    # Agent 명
    name_shape = _find_shape(slide, "직사각형 5")
    if name_shape:
        _set_text(name_shape, agent.get("agent_name", ""))

    # Agent 유형 — Senior AI / Junior AI 표시
    agent_type = agent.get("agent_type", "Junior AI")
    # 그룹 18 내의 Senior AI / Junior AI 표시를 변경
    # Senior AI 선택 시 Senior 앞에 ● 표시
    senior_shapes = _find_shapes_containing(slide, "Senior AI")
    for s in senior_shapes:
        if s.has_text_frame and s.text_frame.paragraphs:
            para = s.text_frame.paragraphs[0]
            if para.runs:
                if agent_type == "Senior AI":
                    para.runs[0].text = "● Senior AI"
                else:
                    para.runs[0].text = "○ Senior AI"

    junior_shapes = _find_shapes_containing(slide, "Junior AI")
    for s in junior_shapes:
        if s.has_text_frame and s.text_frame.paragraphs:
            para = s.text_frame.paragraphs[0]
            if para.runs:
                if agent_type == "Junior AI":
                    para.runs[0].text = "● Junior AI"
                else:
                    para.runs[0].text = "○ Junior AI"

    # Agent 역할
    roles = agent.get("roles", [])
    role_shape = _find_shape(slide, "직사각형 17")
    if role_shape:
        _set_multiline_text(role_shape, roles, font_size=Pt(9), bullet_char="•", color=DARK)

    # 처리 로직 — Input / 방법론 / Output
    input_data = agent.get("input_data", [])
    processing_steps = agent.get("processing_steps", [])
    output_data = agent.get("output_data", [])

    # ── 유사 항목 그룹핑 ──
    # "XXX 데이터 (세부1, 세부2)" → 괄호 앞 키워드를 기준으로 묶기
    # 괄호 없는 항목도 공통 접미사(데이터, 결과, 리포트 등)로 그룹핑
    import re as _re

    def _group_items(items: list[str], max_groups: int = 5) -> list[str]:
        """유사 항목을 큰 chunk로 묶어 '대분류 (세부1, 세부2)' 형태로 반환."""
        if len(items) <= max_groups:
            # 항목이 적으면 괄호 안 세부만 짧게 줄여서 반환
            return [_shorten(s, 35) for s in items]

        # 1단계: 괄호가 있는 항목은 괄호 앞을 카테고리로 추출
        groups: dict[str, list[str]] = {}
        ungrouped: list[str] = []

        for item in items:
            s = str(item)
            # "AAA (BBB, CCC)" → category="AAA", detail="BBB, CCC"
            m = _re.match(r'^(.+?)\s*\((.+)\)\s*$', s)
            if m:
                cat = m.group(1).strip()
                detail = m.group(2).strip()
                groups.setdefault(cat, []).append(detail)
            else:
                # 공통 키워드로 그룹핑 시도 (데이터, 결과, 리포트, 목록 등)
                matched = False
                for keyword in ["데이터", "결과", "리포트", "보고서", "목록", "현황",
                                "분석", "전략", "지시", "브리핑", "요약"]:
                    if keyword in s:
                        groups.setdefault(keyword, []).append(s)
                        matched = True
                        break
                if not matched:
                    ungrouped.append(s)

        # 2단계: 그룹을 "카테고리 (세부1, 세부2)" 형태로 조합
        result: list[str] = []
        for cat, details in groups.items():
            if len(details) == 1:
                # 그룹에 1개면 괄호 안에 원래 있던 세부만
                combined = f"{cat} ({details[0][:25]})"
            else:
                # 여러 개 → 짧은 세부만 나열
                short_details = [_shorten(d, 12) for d in details[:4]]
                suffix = f" 외 {len(details)-4}건" if len(details) > 4 else ""
                combined = f"{cat} ({', '.join(short_details)}{suffix})"
            result.append(_shorten(combined, 45))

        # 미분류 항목 추가
        for u in ungrouped[:max(1, max_groups - len(result))]:
            result.append(_shorten(u, 35))
        if len(ungrouped) > max(1, max_groups - len(groups)):
            remaining = len(ungrouped) - max(1, max_groups - len(groups))
            result.append(f"... 외 {remaining}건")

        return result[:max_groups]

    def _shorten(s: str, max_len: int = 35) -> str:
        """문자열을 최대 길이로 자르고 생략 표시."""
        s = str(s).strip()
        return s[:max_len-1] + "…" if len(s) > max_len else s

    # 항목 수에 따른 폰트 크기 (더 공격적으로 축소)
    def _auto_font(count: int, base: int = 8) -> Pt:
        if count > 8: return Pt(5)
        if count > 6: return Pt(5.5)
        if count > 4: return Pt(6)
        if count > 3: return Pt(7)
        return Pt(base)

    # 처리 로직 영역 좌표 (템플릿 Slide 3 기준)
    # Input 그룹(id=48):  L=1.8cm → 내용 L=3.5cm, T=12.3cm, W=5.8cm, H=5.0cm
    # 방법론 그룹(id=46): L=11.0cm → 내용 L=13.0cm, T=12.3cm, W=7.5cm, H=5.0cm
    # Output 그룹(id=47): L=22.3cm → 내용 L=24.2cm, T=12.3cm, W=7.5cm, H=5.0cm

    # Input — 그룹핑 적용
    if input_data:
        items = _group_items(input_data, max_groups=5)
        _add_multiline_textbox(
            slide, left=Cm(3.5), top=Cm(12.3),
            width=Cm(5.8), height=Cm(5.0),
            lines=items, font_size=_auto_font(len(items)), bullet="•",
            line_spacing=1.05,
        )

    # 방법론 — "번호. 이름 [기법] → 산출물" 한 줄 형태
    if processing_steps:
        method_lines = []
        for idx, ps in enumerate(processing_steps[:5], 1):
            name = _shorten(str(ps.get("step_name", "")), 22)
            method = _shorten(str(ps.get("method", "")), 15)
            result_text = _shorten(str(ps.get("result", "")), 15)
            line = f"{idx}. {name}"
            if method:
                line += f" [{method}]"
            if result_text:
                line += f" → {result_text}"
            method_lines.append(line)
        if len(processing_steps) > 5:
            method_lines.append(f"... 외 {len(processing_steps)-5}단계")

        _add_multiline_textbox(
            slide, left=Cm(13.0), top=Cm(12.3),
            width=Cm(7.5), height=Cm(5.0),
            lines=method_lines,
            font_size=_auto_font(len(method_lines), base=7), bullet="",
            line_spacing=1.1,
        )

    # Output — 그룹핑 적용
    if output_data:
        items = _group_items(output_data, max_groups=5)
        _add_multiline_textbox(
            slide, left=Cm(24.2), top=Cm(12.3),
            width=Cm(7.5), height=Cm(5.0),
            lines=items, font_size=_auto_font(len(items)), bullet="•",
            line_spacing=1.05,
        )


# ── 메인 함수 ─────────────────────────────────────────────────────────────────

def _remove_shapes_by_ids(slide, shape_ids: list[int]):
    """슬라이드에서 특정 shape_id의 도형을 제거합니다."""
    spTree = slide.shapes._spTree
    for shape in list(slide.shapes):
        if shape.shape_id in shape_ids:
            sp = shape._element
            spTree.remove(sp)
            print(f"[ppt_exporter] 도형 제거: id={shape.shape_id} name={shape.name}")


def _insert_workflow_shapes(slide, workflow_cache: dict | None):
    """AI Service Flow를 PPT 도형으로 직접 그립니다 (수정 가능)."""
    if not workflow_cache:
        return
    try:
        # 기존 AI Service Flow 배경 도형 제거 (그룹 127)
        _remove_shapes_by_ids(slide, [128])

        from ppt_flow_drawer import draw_service_flow
        draw_service_flow(slide, workflow_cache)
        print("[ppt_exporter] AI Service Flow 도형 삽입 완료")
    except Exception as e:
        print(f"[ppt_exporter] AI Service Flow 도형 삽입 실패: {e}")


def export_ppt(
    definition: dict | None = None,
    design: dict | None = None,
    workflow: dict | None = None,
) -> io.BytesIO:
    """과제 정의서/설계서를 PPT로 내보냅니다. 표지/Thank You 슬라이드는 제거."""
    prs = Presentation(str(TEMPLATE_PATH))

    # 삭제할 슬라이드 인덱스 (역순으로 삭제)
    slides_to_remove = []

    # Slide 0: 표지 → 제거 대상
    slides_to_remove.append(0)

    # Slide 1: 과제 정의서
    if definition:
        _fill_definition_slide(prs.slides[1], definition)

    # Slide 2: 과제 설계서
    if design:
        _fill_design_slide(prs.slides[2], design, definition)
    # AI Service Flow 도형 그리기
    if workflow:
        _insert_workflow_shapes(prs.slides[2], workflow)

    # Slide 3+: Agent 정의서
    agents = design.get("agent_definitions", []) if design else []

    if agents:
        # 1) 먼저 필요한 슬라이드 수만큼 복제 (빈 상태에서 복제)
        agent_slides = [prs.slides[3]]  # 첫 번째는 원본
        for _ in agents[1:]:
            agent_slides.append(_duplicate_slide(prs, 3))

        # 2) 그 다음 각 슬라이드에 개별 Agent 데이터 채우기
        for slide, agent in zip(agent_slides, agents):
            _remove_shapes_by_ids(slide, [133])  # 기존 미니맵 배경 제거
            _fill_agent_slide(slide, agent, design, definition)
            if workflow:
                try:
                    from ppt_flow_drawer import draw_minimap
                    draw_minimap(slide, workflow, highlight_agent_id=agent.get("agent_id", ""))
                except Exception as e:
                    print(f"[ppt_exporter] 미니맵 실패: {e}")

    # Thank You 슬라이드 (마지막) → 제거 대상
    thank_you_idx = 4 if not agents else 4  # 복제 전 기준
    slides_to_remove.append(thank_you_idx)

    # 슬라이드 제거 (역순)
    for idx in sorted(slides_to_remove, reverse=True):
        if idx < len(prs.slides):
            rId = prs.slides._sldIdLst[idx].get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id', '')
            sldId = prs.slides._sldIdLst[idx]
            prs.slides._sldIdLst.remove(sldId)

    # BytesIO로 저장
    output = io.BytesIO()
    prs.save(output)
    output.seek(0)
    return output


def _move_slide_to_end(prs: Presentation, slide_index: int):
    """슬라이드를 맨 뒤로 이동합니다 (XML 기반)."""
    slides_el = prs.slides._sldIdLst
    slide_ids = list(slides_el)
    if slide_index < len(slide_ids):
        target = slide_ids[slide_index]
        slides_el.remove(target)
        slides_el.append(target)
