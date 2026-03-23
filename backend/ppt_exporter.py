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
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from lxml import etree


TEMPLATE_PATH = Path(__file__).parent.parent / "PwC_두산_AI 기반 HR 업무혁신_과제정의서_v1.0_템플릿.pptx"

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
    """Shape에 여러 줄 텍스트를 설정합니다."""
    if not shape or not shape.has_text_frame:
        return
    tf = shape.text_frame
    tf.clear()
    tf.word_wrap = True

    for i, line in enumerate(lines):
        if i == 0:
            para = tf.paragraphs[0]
        else:
            para = tf.add_paragraph()

        full_text = f"{bullet_char} {line}" if bullet_char else line
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

        full_text = f"{bullet} {line}" if bullet else line
        run = para.add_run()
        run.text = full_text
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

    # 헤더: 과제번호/이름
    header_shape = _find_shape(slide, "직사각형 7")
    if header_shape:
        title_text = f"■ 과제번호/이름     {project_number}. {project_title}"
        _set_text(header_shape, title_text)

    # 과제번호/이름 입력 영역
    title_input = _find_shape(slide, "직사각형 9")
    if title_input:
        _set_text(title_input, f"{project_number}. {project_title}")

    # 작성일/작성자
    date_shape = _find_shape(slide, "직사각형 13")
    if date_shape:
        _set_text(date_shape, f"작성일: {created_date}   |   작성자: {author}")

    # 1. 과제 개요 — "ㅇㅇ" 플레이스홀더 → overview 리스트
    overview = definition.get("overview", [])
    overview_shape = _find_shape(slide, "직사각형 26")
    if overview_shape and overview:
        overview_text = "\n".join(f"• {item}" for item in overview)
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

    # 8. AI 기술 유형 — 기술 이름
    tech_names_shape = _find_shape(slide, "직사각형 37")
    if tech_names_shape:
        tech_names = design.get("ai_tech_info", {}).get("tech_names", [])
        _set_multiline_text(tech_names_shape, tech_names, font_size=Pt(9), bullet_char="•", color=DARK)

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
    # Input 영역 (그룹 47 내부에 텍스트 추가)
    input_data = agent.get("input_data", [])
    processing_steps = agent.get("processing_steps", [])
    output_data = agent.get("output_data", [])

    # Input 텍스트 박스 — 그룹 47 근처에 추가 (left=655656, top=4303065 근처)
    if input_data:
        _add_multiline_textbox(
            slide,
            left=Emu(700000), top=Emu(4700000),
            width=Emu(2700000), height=Emu(1500000),
            lines=input_data, font_size=Pt(8), bullet="•",
        )

    # 방법론 및 주요 기술 — 그룹 45 근처
    if processing_steps:
        method_lines = []
        for ps in processing_steps:
            step_num = ps.get("step_number", "")
            step_name = ps.get("step_name", "")
            method = ps.get("method", "")
            result = ps.get("result", "")
            method_lines.append(f"{step_num}  {step_name}")
            method_lines.append(f"    {method} → {result}")

        _add_multiline_textbox(
            slide,
            left=Emu(4050000), top=Emu(4700000),
            width=Emu(3500000), height=Emu(1500000),
            lines=method_lines, font_size=Pt(7.5), bullet="",
        )

    # Output — 그룹 46 근처
    if output_data:
        _add_multiline_textbox(
            slide,
            left=Emu(8100000), top=Emu(4700000),
            width=Emu(3500000), height=Emu(1500000),
            lines=output_data, font_size=Pt(8), bullet="•",
        )


# ── 메인 함수 ─────────────────────────────────────────────────────────────────

def export_ppt(
    definition: dict | None = None,
    design: dict | None = None,
) -> io.BytesIO:
    """과제 정의서/설계서를 PPT로 내보냅니다."""
    prs = Presentation(str(TEMPLATE_PATH))

    # Slide 1: 표지
    if definition:
        _fill_cover_slide(prs.slides[0], definition.get("project_title", ""))

    # Slide 2: 과제 정의서
    if definition:
        _fill_definition_slide(prs.slides[1], definition)

    # Slide 3: 과제 설계서
    if design:
        _fill_design_slide(prs.slides[2], design, definition)

    # Slide 4+: Agent 정의서
    agents = design.get("agent_definitions", []) if design else []

    if agents:
        # 첫 번째 Agent는 기존 슬라이드 4에 채움
        _fill_agent_slide(prs.slides[3], agents[0], design, definition)

        # 나머지 Agent는 슬라이드 복제
        for agent in agents[1:]:
            new_slide = _duplicate_slide(prs, 3)
            _fill_agent_slide(new_slide, agent, design, definition)

        # 슬라이드 순서 정리: Thank You 슬라이드를 맨 뒤로
        # (복제된 슬라이드가 맨 뒤에 추가되므로, Thank You 슬라이드를 이동)
        # Thank You는 원래 index 4였지만, 복제 후에는 위치가 바뀜
        # → python-pptx에서 슬라이드 순서 변경은 XML 조작 필요
        _move_slide_to_end(prs, 4)  # Thank You 슬라이드를 맨 뒤로
    elif not agents:
        # Agent가 없으면 슬라이드 4를 빈 상태로 유지
        pass

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
