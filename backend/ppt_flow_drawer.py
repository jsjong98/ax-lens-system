"""
ppt_flow_drawer.py — PPT에 AI Service Flow를 도형으로 직접 그리기

python-pptx 도형(사각형, 선, 화살표)을 사용하여 수정 가능한 스윔레인을 그립니다.
- draw_service_flow: 전체 AI Service Flow (과제 설계서용)
- draw_minimap: 축소 미니맵 (Agent 정의서용, 특정 Agent 강조)
"""
from __future__ import annotations

from pptx.util import Inches, Pt, Emu, Cm
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE


# ── 색상 ──────────────────────────────────────────────────────────────────────

RED = RGBColor(0xCC, 0x00, 0x00)
BLUE = RGBColor(0x1A, 0x5C, 0xB0)
GRAY = RGBColor(0x88, 0x87, 0x80)
LIGHT_GRAY = RGBColor(0xD3, 0xD1, 0xC7)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
BLACK = RGBColor(0x2C, 0x2C, 0x2A)
RED_BG = RGBColor(0xFF, 0xF5, 0xF5)
YELLOW_BG = RGBColor(0xFE, 0xFA, 0xF0)
GRAY_BG = RGBColor(0xFA, 0xFA, 0xF8)
INPUT_BG = RGBColor(0xF5, 0xF4, 0xF1)


def _add_rect(slide, left, top, width, height, fill=None, border_color=None,
              border_width=Pt(1), border_dash=None, text="", font_size=Pt(8),
              font_color=BLACK, bold=False, align=PP_ALIGN.CENTER):
    """사각형 도형을 추가합니다."""
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill or WHITE

    if border_color:
        shape.line.color.rgb = border_color
        shape.line.width = border_width
        if border_dash:
            shape.line.dash_style = border_dash
    else:
        shape.line.fill.background()

    if text:
        tf = shape.text_frame
        tf.word_wrap = True
        tf.auto_size = None
        p = tf.paragraphs[0]
        p.alignment = align
        run = p.add_run()
        run.text = text
        run.font.size = font_size
        run.font.color.rgb = font_color
        run.font.bold = bold

    return shape


def _add_arrow_line(slide, x1, y1, x2, y2, color=BLUE, width=Pt(1.5)):
    """화살표가 달린 직선을 추가합니다."""
    from lxml import etree
    connector = slide.shapes.add_connector(1, x1, y1, x2, y2)
    connector.line.color.rgb = color
    connector.line.width = width
    # 화살표 헤드 추가 (XML 직접)
    ln = connector._element.find('.//{http://schemas.openxmlformats.org/drawingml/2006/main}ln')
    if ln is not None:
        tailEnd = etree.SubElement(ln, '{http://schemas.openxmlformats.org/drawingml/2006/main}tailEnd')
        tailEnd.set('type', 'triangle')
        tailEnd.set('w', 'med')
        tailEnd.set('len', 'med')
    return connector


def _add_line(slide, x1, y1, x2, y2, color=LIGHT_GRAY, width=Pt(0.5)):
    """단순 선을 추가합니다."""
    shape = slide.shapes.add_connector(1, x1, y1, x2, y2)
    shape.line.color.rgb = color
    shape.line.width = width
    return shape


# ══════════════════════════════════════════════════════════════════════════════
# 미니맵 그리기 (Agent 정의서용)
# ══════════════════════════════════════════════════════════════════════════════

def draw_minimap(slide, workflow: dict, highlight_agent_id: str = "",
                 left=Cm(17.5), top=Cm(3.5), total_width=Cm(8), total_height=Cm(7)):
    """
    축소된 AI Service Flow 미니맵을 그립니다.
    highlight_agent_id에 해당하는 Agent만 두꺼운 테두리로 강조합니다.
    """
    agents = workflow.get("agents", [])
    if not agents:
        return

    agent_count = len(agents)
    row_height = total_height / 5
    agent_width = (total_width - Cm(1.5)) / max(agent_count, 1)
    agent_left_start = left + Cm(1.5)

    # ── Input 행 ──
    input_top = top
    # 레이블
    _add_rect(slide, left, input_top, Cm(1.3), row_height,
              fill=WHITE, border_color=LIGHT_GRAY,
              text="Input", font_size=Pt(5), font_color=GRAY)
    # Input 박스들
    for i in range(min(agent_count, 6)):
        box_w = agent_width * 0.8
        box_left = agent_left_start + i * agent_width + (agent_width - box_w) / 2
        _add_rect(slide, box_left, input_top + Cm(0.1), box_w, row_height - Cm(0.2),
                  fill=INPUT_BG, border_color=BLUE, border_width=Pt(0.5))

    # ── Senior AI 행 ──
    senior_top = top + row_height
    _add_rect(slide, left, senior_top, Cm(1.3), row_height,
              fill=WHITE, border_color=LIGHT_GRAY,
              text="Senior\nAI", font_size=Pt(5), font_color=RED)
    _add_rect(slide, agent_left_start, senior_top + Cm(0.1),
              total_width - Cm(1.5), row_height - Cm(0.2),
              fill=RED_BG, border_color=RED, border_width=Pt(1))

    # ── Junior AI 행 ──
    junior_top = top + row_height * 2
    _add_rect(slide, left, junior_top, Cm(1.3), row_height * 2,
              fill=WHITE, border_color=LIGHT_GRAY,
              text="Junior\nAI", font_size=Pt(5), font_color=BLUE)

    for i, agent in enumerate(agents):
        box_left = agent_left_start + i * agent_width + Cm(0.1)
        box_w = agent_width - Cm(0.2)
        is_highlight = agent.get("agent_id") == highlight_agent_id

        _add_rect(slide, box_left, junior_top + Cm(0.1), box_w, row_height * 2 - Cm(0.3),
                  fill=YELLOW_BG if is_highlight else WHITE,
                  border_color=BLUE,
                  border_width=Pt(3) if is_highlight else Pt(0.5),
                  border_dash=7 if not is_highlight else None)  # 7 = dash

        # Agent 번호
        _add_rect(slide, box_left + Cm(0.1), junior_top + Cm(0.2), Cm(0.5), Cm(0.5),
                  fill=BLUE if is_highlight else LIGHT_GRAY,
                  text=str(i + 1), font_size=Pt(5),
                  font_color=WHITE if is_highlight else BLACK, bold=True)

        # Task 박스들 (간략)
        tasks = agent.get("assigned_tasks", [])
        for j in range(min(len(tasks), 3)):
            task_top = junior_top + Cm(0.9) + j * Cm(0.5)
            _add_rect(slide, box_left + Cm(0.15), task_top,
                      box_w - Cm(0.3), Cm(0.4),
                      fill=INPUT_BG, border_color=LIGHT_GRAY, border_width=Pt(0.3))

    # ── HR 행 ──
    hr_top = top + row_height * 4
    _add_rect(slide, left, hr_top, Cm(1.3), row_height,
              fill=WHITE, border_color=LIGHT_GRAY,
              text="HR\n담당자", font_size=Pt(5), font_color=BLACK)

    for i in range(agent_count):
        box_left = agent_left_start + i * agent_width + Cm(0.1)
        box_w = agent_width - Cm(0.2)
        _add_rect(slide, box_left, hr_top + Cm(0.1), box_w, row_height - Cm(0.2),
                  fill=GRAY_BG, border_color=LIGHT_GRAY, border_width=Pt(0.3))

    # ── 연결선 (Senior ↔ Junior) ──
    for i in range(agent_count):
        center_x = agent_left_start + i * agent_width + agent_width / 2
        # Senior → Junior (하향)
        _add_line(slide, center_x - Cm(0.15), senior_top + row_height,
                  center_x - Cm(0.15), junior_top, color=RED, width=Pt(0.7))
        # Junior → Senior (상향)
        _add_line(slide, center_x + Cm(0.15), junior_top,
                  center_x + Cm(0.15), senior_top + row_height, color=BLUE, width=Pt(0.7))


# ══════════════════════════════════════════════════════════════════════════════
# 전체 AI Service Flow 그리기 (과제 설계서용)
# ══════════════════════════════════════════════════════════════════════════════

def draw_service_flow(slide, workflow: dict,
                      left=Cm(0.5), top=Cm(2.5), total_width=Cm(16), total_height=Cm(12)):
    """
    전체 AI Service Flow를 PPT 도형으로 그립니다.
    수정 가능한 도형으로 구성됩니다.
    """
    agents = workflow.get("agents", [])
    if not agents:
        return

    agent_count = len(agents)
    label_w = Cm(1.5)
    content_w = total_width - label_w
    agent_col_w = content_w / max(agent_count, 1)
    content_left = left + label_w

    row_heights = [Cm(1.5), Cm(1.5), Cm(6), Cm(1.5)]  # Input, Senior, Junior, HR
    row_tops = [top]
    for h in row_heights[:-1]:
        row_tops.append(row_tops[-1] + h)

    # ── Input 행 ──
    _add_rect(slide, left, row_tops[0], label_w, row_heights[0],
              fill=WHITE, border_color=LIGHT_GRAY,
              text="📥\nInput", font_size=Pt(6), font_color=GRAY)

    all_inputs = set()
    for a in agents:
        for t in a.get("assigned_tasks", []):
            for inp in t.get("input_data", []):
                all_inputs.add(inp)
    inputs_list = list(all_inputs)[:6]

    for i, inp in enumerate(inputs_list):
        iw = content_w / max(len(inputs_list), 1)
        _add_rect(slide, content_left + i * iw + Cm(0.1), row_tops[0] + Cm(0.2),
                  iw - Cm(0.2), row_heights[0] - Cm(0.4),
                  fill=INPUT_BG, border_color=LIGHT_GRAY,
                  text=inp, font_size=Pt(5), font_color=BLACK)

    # ── Senior AI 행 ──
    _add_rect(slide, left, row_tops[1], label_w, row_heights[1],
              fill=WHITE, border_color=LIGHT_GRAY,
              text="🤖\nSenior AI", font_size=Pt(6), font_color=RED)

    process_name = workflow.get("process_name", "")
    _add_rect(slide, content_left + Cm(0.2), row_tops[1] + Cm(0.2),
              content_w - Cm(0.4), row_heights[1] - Cm(0.4),
              fill=RED_BG, border_color=RED, border_width=Pt(1.5),
              text=f"{process_name} 오케스트레이터", font_size=Pt(7), font_color=RED, bold=True)

    # ── Junior AI 행 ──
    _add_rect(slide, left, row_tops[2], label_w, row_heights[2],
              fill=WHITE, border_color=LIGHT_GRAY,
              text="🤖\nJunior AI", font_size=Pt(6), font_color=BLUE)

    for i, agent in enumerate(agents):
        col_left = content_left + i * agent_col_w
        box_left = col_left + Cm(0.15)
        box_w = agent_col_w - Cm(0.3)

        # Agent 박스
        _add_rect(slide, box_left, row_tops[2] + Cm(0.3), box_w, row_heights[2] - Cm(0.5),
                  fill=WHITE, border_color=BLUE, border_width=Pt(1), border_dash=7)

        # Agent 번호 + 이름
        _add_rect(slide, box_left + Cm(0.1), row_tops[2] + Cm(0.4), Cm(0.5), Cm(0.5),
                  fill=BLUE, text=str(i + 1), font_size=Pt(6), font_color=WHITE, bold=True)
        _add_rect(slide, box_left + Cm(0.7), row_tops[2] + Cm(0.4), box_w - Cm(0.9), Cm(0.5),
                  fill=WHITE, text=agent.get("agent_name", ""),
                  font_size=Pt(5), font_color=BLACK, bold=True, align=PP_ALIGN.LEFT)

        # Task 박스들 + Task간 화살표
        tasks = agent.get("assigned_tasks", [])
        task_h = Cm(0.6)
        task_gap = Cm(0.15)
        max_tasks = min(len(tasks), int((row_heights[2] - Cm(1.5)) / (task_h + task_gap)))

        for j in range(max_tasks):
            task = tasks[j]
            is_human = task.get("automation_level", "") != "Human-on-the-Loop"
            task_top = row_tops[2] + Cm(1.1) + j * (task_h + task_gap)

            task_fill = RGBColor(0xFA, 0xEE, 0xDA) if is_human else INPUT_BG
            task_border = RGBColor(0xBA, 0x75, 0x17) if is_human else LIGHT_GRAY

            _add_rect(slide, box_left + Cm(0.15), task_top, box_w - Cm(0.3), task_h,
                      fill=task_fill, border_color=task_border, border_width=Pt(0.5),
                      text=task.get("task_name", "")[:20], font_size=Pt(5), font_color=BLACK)

            # Task 간 화살표 (이전 Task → 현재 Task)
            if j > 0:
                arrow_x = box_left + box_w / 2
                prev_bottom = task_top - task_gap
                _add_arrow_line(slide, arrow_x, prev_bottom, arrow_x, task_top,
                               color=LIGHT_GRAY, width=Pt(0.7))

        # ── 연결선: Input → Senior (꺾임) ──
        center_x = col_left + agent_col_w / 2
        # Input 박스 하단 → Senior 상단
        if i < len(inputs_list):
            input_bottom_y = row_tops[0] + row_heights[0]
            senior_top_y = row_tops[1]
            _add_line(slide, center_x, input_bottom_y, center_x, senior_top_y,
                      color=RGBColor(0x5B, 0x9B, 0xD5), width=Pt(0.7))

        # ── 연결선: Senior → Junior (화살표) ──
        _add_arrow_line(slide, center_x - Cm(0.15), row_tops[1] + row_heights[1],
                        center_x - Cm(0.15), row_tops[2] + Cm(0.1),
                        color=RED, width=Pt(1))
        # Junior → Senior (화살표)
        _add_arrow_line(slide, center_x + Cm(0.15), row_tops[2] + Cm(0.1),
                        center_x + Cm(0.15), row_tops[1] + row_heights[1],
                        color=BLUE, width=Pt(1))

        # ── 연결선: Junior → HR (화살표, Human 확인 필요한 경우) ──
        has_human = any(t.get("automation_level", "") != "Human-on-the-Loop"
                        for t in tasks)
        if has_human:
            _add_arrow_line(slide, center_x, row_tops[2] + row_heights[2],
                            center_x, row_tops[3] + Cm(0.1),
                            color=BLUE, width=Pt(1))

    # ── HR 행 ──
    _add_rect(slide, left, row_tops[3], label_w, row_heights[3],
              fill=WHITE, border_color=LIGHT_GRAY,
              text="👤\nHR 담당자", font_size=Pt(6), font_color=BLACK)

    for i, agent in enumerate(agents):
        col_left = content_left + i * agent_col_w
        human_tasks = [t for t in agent.get("assigned_tasks", [])
                       if t.get("automation_level", "") != "Human-on-the-Loop"]
        if human_tasks:
            _add_rect(slide, col_left + Cm(0.15), row_tops[3] + Cm(0.2),
                      agent_col_w - Cm(0.3), row_heights[3] - Cm(0.4),
                      fill=GRAY_BG, border_color=LIGHT_GRAY,
                      text=human_tasks[0].get("human_role", "검토·확인")[:20],
                      font_size=Pt(5), font_color=BLACK)
