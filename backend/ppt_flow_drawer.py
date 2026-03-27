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


# ── 색상 (스크린샷 기준 매칭) ──────────────────────────────────────────────────

RED = RGBColor(0x8B, 0x1A, 0x1A)           # Senior AI 테두리 (짙은 빨강)
RED_ARROW = RGBColor(0x8B, 0x1A, 0x1A)     # Senior→HR 직결 화살표
BLUE = RGBColor(0x5B, 0x9B, 0xD5)          # Input 테두리 기본 (하늘색)
BLUE_ARROW = RGBColor(0x5B, 0x9B, 0xD5)    # Input→Senior 화살표 기본
GOLD = RGBColor(0xAA, 0x8E, 0x2A)          # Junior AI 테두리/화살표 (금색)
GOLD_ARROW = RGBColor(0xAA, 0x8E, 0x2A)    # Junior 내부·Junior→HR 화살표
GRAY = RGBColor(0x88, 0x87, 0x80)
GRAY_ARROW = RGBColor(0x9E, 0x9E, 0x9E)    # 보조 화살표
LIGHT_GRAY = RGBColor(0xD3, 0xD1, 0xC7)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
BLACK = RGBColor(0x2C, 0x2C, 0x2A)
RED_BG = RGBColor(0xF8, 0xE0, 0xE0)        # Senior AI 배경 (연분홍)
YELLOW_BG = RGBColor(0xFE, 0xFA, 0xF0)     # Junior AI 배경 (연노랑)
GRAY_BG = RGBColor(0xF5, 0xF5, 0xF3)       # HR 배경
INPUT_BG = RGBColor(0xF5, 0xF4, 0xF1)

# Agent별 구분 파란 계열 팔레트 (최대 7개 Agent)
_AGENT_BLUE_PALETTE = [
    RGBColor(0x2E, 0x75, 0xB6),   # 진한 파랑
    RGBColor(0x00, 0xA6, 0xA0),   # 청록(틸)
    RGBColor(0x5B, 0x9B, 0xD5),   # 하늘색
    RGBColor(0x7B, 0x68, 0xC4),   # 보라-파랑
    RGBColor(0x00, 0x82, 0x7F),   # 짙은 청록
    RGBColor(0x41, 0x72, 0xC4),   # 코발트
    RGBColor(0x2D, 0x8B, 0xBA),   # 세룰리안
]


def _get_agent_color(agent_idx: int) -> RGBColor:
    """Agent 인덱스에 대응하는 파란 계열 색상을 반환합니다."""
    return _AGENT_BLUE_PALETTE[agent_idx % len(_AGENT_BLUE_PALETTE)]


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


def _add_arrow_line(slide, x1, y1, x2, y2, color=BLUE_ARROW, width=Pt(1.5),
                    head_start=False):
    """화살표가 달린 직선을 추가합니다. head_start=True이면 시작점에도 화살표."""
    from lxml import etree
    connector = slide.shapes.add_connector(1, x1, y1, x2, y2)
    connector.line.color.rgb = color
    connector.line.width = width
    ns = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
    ln = connector._element.find(f'.//{ns}ln')
    if ln is not None:
        tailEnd = etree.SubElement(ln, f'{ns}tailEnd')
        tailEnd.set('type', 'triangle')
        tailEnd.set('w', 'med')
        tailEnd.set('len', 'med')
        if head_start:
            headEnd = etree.SubElement(ln, f'{ns}headEnd')
            headEnd.set('type', 'triangle')
            headEnd.set('w', 'med')
            headEnd.set('len', 'med')
    return connector


def _add_data_label(slide, x, y, text, font_size=Pt(4), font_color=GRAY,
                    bg_color=WHITE, width=Cm(2), height=Cm(0.35)):
    """데이터 흐름 라벨 (화살표 옆에 표시)."""
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = bg_color
    shape.line.fill.background()
    tf = shape.text_frame
    tf.word_wrap = True
    tf.auto_size = None
    tf.margin_left = Pt(1)
    tf.margin_right = Pt(1)
    tf.margin_top = Pt(0)
    tf.margin_bottom = Pt(0)
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    run = p.add_run()
    run.text = text[:25]
    run.font.size = font_size
    run.font.color.rgb = font_color
    run.font.italic = True
    return shape


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
    레인 간 간격을 확보하여 화살표가 정확히 연결됩니다.
    """
    agents = workflow.get("agents", [])
    if not agents:
        return

    agent_count = len(agents)
    label_w = Cm(1.3)
    content_w = total_width - label_w - Cm(0.2)  # 오른쪽 감독라인 공간
    agent_col_w = content_w / max(agent_count, 1)
    content_left = left + label_w

    # 레인 높이 + 레인 간 간격 (화살표 공간)
    input_h  = Cm(0.9)
    gap_is   = Cm(0.4)   # Input→Senior 간격
    senior_h = Cm(0.9)
    gap_sj   = Cm(0.5)   # Senior→Junior 간격
    junior_h = Cm(2.8)
    gap_jh   = Cm(0.4)   # Junior→HR 간격
    hr_h     = Cm(0.9)

    # 각 레인 top 좌표
    input_top  = top
    senior_top = input_top + input_h + gap_is
    junior_top = senior_top + senior_h + gap_sj
    hr_top_y   = junior_top + junior_h + gap_jh

    # ── 레인 배경 ──
    _add_rect(slide, content_left, junior_top, content_w, junior_h,
              fill=YELLOW_BG, border_color=None)

    # ══════════════════════════════════════════════════════════════════
    # 1. Input 행
    # ══════════════════════════════════════════════════════════════════
    _add_rect(slide, left, input_top, label_w, input_h,
              fill=WHITE, border_color=LIGHT_GRAY,
              text="Input", font_size=Pt(5), font_color=GRAY)

    for i in range(min(agent_count, 6)):
        color = _get_agent_color(i)
        box_w = agent_col_w * 0.75
        box_left = content_left + i * agent_col_w + (agent_col_w - box_w) / 2
        _add_rect(slide, box_left, input_top + Cm(0.08), box_w, input_h - Cm(0.16),
                  fill=WHITE, border_color=color, border_width=Pt(0.7))

    # ══════════════════════════════════════════════════════════════════
    # 2. Senior AI 행
    # ══════════════════════════════════════════════════════════════════
    _add_rect(slide, left, senior_top, label_w, senior_h,
              fill=WHITE, border_color=LIGHT_GRAY,
              text="Senior\nAI", font_size=Pt(5), font_color=RED)
    _add_rect(slide, content_left, senior_top + Cm(0.06),
              content_w, senior_h - Cm(0.12),
              fill=RED_BG, border_color=RED, border_width=Pt(0.8))

    # ══════════════════════════════════════════════════════════════════
    # 3. Junior AI 행
    # ══════════════════════════════════════════════════════════════════
    _add_rect(slide, left, junior_top, label_w, junior_h,
              fill=WHITE, border_color=LIGHT_GRAY,
              text="Junior\nAI", font_size=Pt(5), font_color=GOLD)

    for i, agent in enumerate(agents):
        box_left = content_left + i * agent_col_w + Cm(0.08)
        box_w = agent_col_w - Cm(0.16)
        is_highlight = agent.get("agent_id") == highlight_agent_id

        _add_rect(slide, box_left, junior_top + Cm(0.08), box_w, junior_h - Cm(0.16),
                  fill=YELLOW_BG if is_highlight else WHITE,
                  border_color=GOLD,
                  border_width=Pt(2.5) if is_highlight else Pt(0.5))

        # Agent 번호 배지
        _add_rect(slide, box_left + Cm(0.06), junior_top + Cm(0.15), Cm(0.4), Cm(0.4),
                  fill=GOLD if is_highlight else LIGHT_GRAY,
                  text=str(i + 1), font_size=Pt(5),
                  font_color=WHITE if is_highlight else BLACK, bold=True)

        # Task 박스들 (간략)
        tasks = agent.get("assigned_tasks", [])
        max_vis = min(len(tasks), 3)
        task_h_each = Cm(0.35)
        task_gap_each = Cm(0.12)
        for j in range(max_vis):
            t_top = junior_top + Cm(0.7) + j * (task_h_each + task_gap_each)
            _add_rect(slide, box_left + Cm(0.1), t_top,
                      box_w - Cm(0.2), task_h_each,
                      fill=INPUT_BG, border_color=GOLD, border_width=Pt(0.3),
                      border_dash=7)

            # Task 간 화살표
            if j > 0:
                arr_x = box_left + box_w / 2
                _add_arrow_line(slide, arr_x, t_top - task_gap_each,
                                arr_x, t_top,
                                color=GOLD_ARROW, width=Pt(0.4))

    # ══════════════════════════════════════════════════════════════════
    # 4. HR 행
    # ══════════════════════════════════════════════════════════════════
    _add_rect(slide, left, hr_top_y, label_w, hr_h,
              fill=WHITE, border_color=LIGHT_GRAY,
              text="HR\n담당자", font_size=Pt(5), font_color=BLACK)

    for i in range(agent_count):
        box_left = content_left + i * agent_col_w + Cm(0.08)
        box_w = agent_col_w - Cm(0.16)
        _add_rect(slide, box_left, hr_top_y + Cm(0.08), box_w, hr_h - Cm(0.16),
                  fill=GRAY_BG, border_color=GRAY_ARROW, border_width=Pt(0.5))

    # ══════════════════════════════════════════════════════════════════
    # 5. 연결 화살표
    # ══════════════════════════════════════════════════════════════════

    for i in range(agent_count):
        center_x = content_left + i * agent_col_w + agent_col_w / 2
        color = _get_agent_color(i)

        # (A) Input → Senior: Agent 색상 화살표
        _add_arrow_line(slide, center_x, input_top + input_h,
                        center_x, senior_top,
                        color=color, width=Pt(0.5))

        # (B) Senior → Junior: Agent 색상 (지시)
        _add_arrow_line(slide, center_x - Cm(0.08), senior_top + senior_h,
                        center_x - Cm(0.08), junior_top,
                        color=color, width=Pt(0.5))

        # (C) Junior → Senior: 회색 (보고)
        _add_arrow_line(slide, center_x + Cm(0.08), junior_top,
                        center_x + Cm(0.08), senior_top + senior_h,
                        color=GRAY_ARROW, width=Pt(0.5))

        # (D) Junior → HR: 금색
        _add_arrow_line(slide, center_x, junior_top + junior_h,
                        center_x, hr_top_y,
                        color=GOLD_ARROW, width=Pt(0.5))

    # (E) Senior → HR 직결 감독 라인 (짙은 빨강, 오른쪽)
    right_x = content_left + content_w + Cm(0.05)
    _add_line(slide, right_x, senior_top + senior_h / 2,
              right_x, senior_top + senior_h,
              color=RED_ARROW, width=Pt(0.8))
    _add_arrow_line(slide, right_x, senior_top + senior_h,
                    right_x, hr_top_y + Cm(0.08),
                    color=RED_ARROW, width=Pt(0.8))


# ══════════════════════════════════════════════════════════════════════════════
# 전체 AI Service Flow 그리기 (과제 설계서용)
# ══════════════════════════════════════════════════════════════════════════════

def draw_service_flow(slide, workflow: dict,
                      left=Cm(0.5), top=Cm(2.5), total_width=Cm(16), total_height=Cm(12)):
    """
    전체 AI Service Flow를 PPT 도형으로 그립니다.
    데이터 흐름을 화살표 + 라벨로 명확히 표시합니다.
    """
    agents = workflow.get("agents", [])
    if not agents:
        return

    agent_count = len(agents)
    label_w = Cm(1.5)
    content_w = total_width - label_w
    agent_col_w = content_w / max(agent_count, 1)
    content_left = left + label_w

    # 레인 간 간격을 확보하여 화살표+라벨 공간 생성
    gap_input_senior = Cm(0.8)   # Input→Senior 사이 간격
    gap_senior_junior = Cm(1.0)  # Senior→Junior 사이 간격
    gap_junior_hr = Cm(0.8)      # Junior→HR 사이 간격

    input_h = Cm(1.3)
    senior_h = Cm(1.3)
    junior_h = Cm(5.5)
    hr_h = Cm(1.3)

    row_tops = [top]
    row_tops.append(row_tops[0] + input_h + gap_input_senior)      # Senior top
    row_tops.append(row_tops[1] + senior_h + gap_senior_junior)     # Junior top
    row_tops.append(row_tops[2] + junior_h + gap_junior_hr)         # HR top

    # ── 레인 배경 (연한 띠) ──
    _add_rect(slide, content_left, row_tops[0], content_w, input_h,
              fill=RGBColor(0xF8, 0xFA, 0xFF), border_color=None)
    _add_rect(slide, content_left, row_tops[2], content_w, junior_h,
              fill=YELLOW_BG, border_color=None)
    _add_rect(slide, content_left, row_tops[3], content_w, hr_h,
              fill=GRAY_BG, border_color=None)

    # ══════════════════════════════════════════════════════════════════
    # 1. Input 행
    # ══════════════════════════════════════════════════════════════════
    _add_rect(slide, left, row_tops[0], label_w, input_h,
              fill=WHITE, border_color=LIGHT_GRAY,
              text="📥\nInput", font_size=Pt(6), font_color=GRAY)

    # 각 Agent별 대표 Input 수집 + Input→Agent 매핑
    agent_inputs: list[list[str]] = []
    input_to_agent_idx: dict[str, int] = {}  # input_name → 최초 사용 agent index
    for ai, a in enumerate(agents):
        inp_set: list[str] = []
        for t in a.get("assigned_tasks", []):
            for inp in t.get("input_data", []):
                if inp not in inp_set:
                    inp_set.append(inp)
                if inp not in input_to_agent_idx:
                    input_to_agent_idx[inp] = ai
        agent_inputs.append(inp_set)

    # Input 박스 그리기 — Agent별 색상으로 테두리 구분
    all_inputs_flat: list[str] = []
    for a_inp in agent_inputs:
        all_inputs_flat.extend(a_inp)
    unique_inputs = list(dict.fromkeys(all_inputs_flat))[:6]

    input_w_each = content_w / max(len(unique_inputs), 1)
    input_center_map: dict[str, int] = {}   # input_name → center_x
    input_color_map: dict[str, RGBColor] = {}  # input_name → 색상
    for i, inp in enumerate(unique_inputs):
        box_x = content_left + i * input_w_each + Cm(0.1)
        bw = input_w_each - Cm(0.2)
        owner_idx = input_to_agent_idx.get(inp, 0)
        inp_color = _get_agent_color(owner_idx)
        _add_rect(slide, box_x, row_tops[0] + Cm(0.15),
                  bw, input_h - Cm(0.3),
                  fill=WHITE, border_color=inp_color, border_width=Pt(1.2),
                  text=inp[:15], font_size=Pt(5), font_color=BLACK)
        input_center_map[inp] = box_x + bw // 2
        input_color_map[inp] = inp_color

    # ══════════════════════════════════════════════════════════════════
    # 2. Senior AI 행
    # ══════════════════════════════════════════════════════════════════
    _add_rect(slide, left, row_tops[1], label_w, senior_h,
              fill=WHITE, border_color=LIGHT_GRAY,
              text="🤖\nSenior AI", font_size=Pt(6), font_color=RED)

    process_name = workflow.get("process_name", "")
    _add_rect(slide, content_left + Cm(0.2), row_tops[1] + Cm(0.15),
              content_w - Cm(0.4), senior_h - Cm(0.3),
              fill=RED_BG, border_color=RED, border_width=Pt(1.5),
              text=f"{process_name} 오케스트레이터", font_size=Pt(7), font_color=RED, bold=True)

    # ══════════════════════════════════════════════════════════════════
    # 3. Junior AI 행
    # ══════════════════════════════════════════════════════════════════
    _add_rect(slide, left, row_tops[2], label_w, junior_h,
              fill=WHITE, border_color=LIGHT_GRAY,
              text="🔧\nJunior AI", font_size=Pt(6), font_color=GOLD)

    agent_center_xs: list[int] = []  # 각 Agent 컬럼 center_x

    for i, agent in enumerate(agents):
        col_left = content_left + i * agent_col_w
        box_left = col_left + Cm(0.15)
        box_w = agent_col_w - Cm(0.3)
        center_x = col_left + agent_col_w // 2
        agent_center_xs.append(center_x)

        # Agent 외곽 박스 (금색 테두리)
        _add_rect(slide, box_left, row_tops[2] + Cm(0.3), box_w, junior_h - Cm(0.5),
                  fill=YELLOW_BG, border_color=GOLD, border_width=Pt(1.2))

        # Agent 번호 배지
        _add_rect(slide, box_left + Cm(0.1), row_tops[2] + Cm(0.4), Cm(0.5), Cm(0.5),
                  fill=GOLD, text=str(i + 1), font_size=Pt(7), font_color=WHITE, bold=True)

        # Task 박스들 + Task간 화살표
        tasks = agent.get("assigned_tasks", [])
        task_h = Cm(0.6)
        task_gap = Cm(0.3)  # 화살표 공간 확보
        max_tasks = min(len(tasks), int((junior_h - Cm(1.8)) / (task_h + task_gap)))

        for j in range(max_tasks):
            task = tasks[j]
            task_top = row_tops[2] + Cm(1.1) + j * (task_h + task_gap)

            task_fill = INPUT_BG
            task_border = GOLD
            _add_rect(slide, box_left + Cm(0.15), task_top, box_w - Cm(0.3), task_h,
                      fill=task_fill, border_color=task_border, border_width=Pt(0.7),
                      border_dash=7,
                      text=task.get("task_name", "")[:20], font_size=Pt(5), font_color=BLACK)

            # Task 간 연결 화살표 + output→input 데이터 라벨
            if j > 0:
                arrow_x = box_left + box_w // 2
                prev_bottom = task_top - task_gap
                _add_arrow_line(slide, arrow_x, prev_bottom, arrow_x, task_top,
                                color=GOLD_ARROW, width=Pt(0.8))
                # 이전 Task의 output을 라벨로 표시
                prev_task = tasks[j - 1]
                prev_outputs = prev_task.get("output_data", [])
                if prev_outputs:
                    label_text = prev_outputs[0][:15]
                    label_w_size = Cm(1.8) if len(label_text) > 6 else Cm(1.2)
                    _add_data_label(slide, arrow_x + Cm(0.1),
                                    prev_bottom + (task_gap - Cm(0.3)) // 2,
                                    label_text, font_color=GOLD,
                                    width=label_w_size, height=Cm(0.25))

    # ══════════════════════════════════════════════════════════════════
    # 4. HR 행
    # ══════════════════════════════════════════════════════════════════
    _add_rect(slide, left, row_tops[3], label_w, hr_h,
              fill=WHITE, border_color=LIGHT_GRAY,
              text="👤\nHR 담당자", font_size=Pt(6), font_color=BLACK)

    hr_box_infos: list[tuple] = []  # (col_left, box_w, human_role_text)
    for i, agent in enumerate(agents):
        col_left = content_left + i * agent_col_w
        human_tasks = [t for t in agent.get("assigned_tasks", [])
                       if t.get("human_role", "")]
        if human_tasks:
            role_text = human_tasks[0].get("human_role", "검토·확인")[:25]
            _add_rect(slide, col_left + Cm(0.15), row_tops[3] + Cm(0.15),
                      agent_col_w - Cm(0.3), hr_h - Cm(0.3),
                      fill=WHITE, border_color=GRAY_ARROW, border_width=Pt(1),
                      text=role_text, font_size=Pt(5), font_color=BLACK)
            hr_box_infos.append((col_left, agent_col_w, role_text))
        else:
            hr_box_infos.append(None)

    # ══════════════════════════════════════════════════════════════════
    # 5. 연결 화살표 (데이터 흐름)
    # ══════════════════════════════════════════════════════════════════

    for i, agent in enumerate(agents):
        center_x = agent_center_xs[i]
        a_inputs = agent_inputs[i]
        agent_color = _get_agent_color(i)

        # ── (A) Input → Senior: Agent별 색상 화살표 (각 Input마다) ──
        input_bottom = row_tops[0] + input_h
        senior_top_y = row_tops[1]
        drawn_inputs = a_inputs[:3]  # 최대 3개까지 연결
        for inp_idx, inp_name in enumerate(drawn_inputs):
            src_x = input_center_map.get(inp_name)
            if src_x is None:
                continue
            inp_color = input_color_map.get(inp_name, agent_color)
            # 여러 선이 겹치지 않도록 x 오프셋
            x_offset = Cm(0.12) * (inp_idx - len(drawn_inputs) / 2 + 0.5)
            dst_x = center_x + x_offset
            mid_y = input_bottom + gap_input_senior // 2

            # 꺾인 화살표: Input 하단 → 수평 이동 → Senior 상단
            if abs(src_x - dst_x) > Cm(0.3):
                _add_line(slide, src_x, input_bottom, src_x, mid_y,
                          color=inp_color, width=Pt(1))
                _add_line(slide, src_x, mid_y, dst_x, mid_y,
                          color=inp_color, width=Pt(1))
                _add_arrow_line(slide, dst_x, mid_y, dst_x, senior_top_y,
                                color=inp_color, width=Pt(1))
            else:
                _add_arrow_line(slide, src_x, input_bottom, dst_x, senior_top_y,
                                color=inp_color, width=Pt(1))

            # Input 데이터 라벨 (첫 번째만 표시, 나머지는 선만)
            if inp_idx == 0:
                label_text = inp_name[:12]
                _add_data_label(slide, src_x + Cm(0.1),
                                input_bottom + Cm(0.05),
                                label_text, font_color=inp_color,
                                width=Cm(1.5), height=Cm(0.25))

        # ── (B) Senior ↔ Junior: Agent별 색상 쌍방향 화살표 ──
        senior_bottom = row_tops[1] + senior_h
        junior_top = row_tops[2]
        mid_y_sj = senior_bottom + gap_senior_junior // 2

        # Senior → Junior (하향, Agent 색상 = 지시)
        _add_arrow_line(slide, center_x - Cm(0.2), senior_bottom,
                        center_x - Cm(0.2), junior_top + Cm(0.1),
                        color=agent_color, width=Pt(1.2))
        # Junior → Senior (상향, 회색 = 보고)
        _add_arrow_line(slide, center_x + Cm(0.2), junior_top + Cm(0.1),
                        center_x + Cm(0.2), senior_bottom,
                        color=GRAY_ARROW, width=Pt(1.2))

        # 라벨: "지시" / "보고"
        _add_data_label(slide, center_x - Cm(0.2) - Cm(0.8),
                        mid_y_sj - Cm(0.12), "지시",
                        font_color=agent_color, width=Cm(0.7), height=Cm(0.25))
        _add_data_label(slide, center_x + Cm(0.3),
                        mid_y_sj - Cm(0.12), "보고",
                        font_color=GRAY_ARROW, width=Cm(0.7), height=Cm(0.25))

        # ── (C) Junior → HR: 금색 화살표 + output 라벨 ──
        junior_bottom = row_tops[2] + junior_h
        hr_top_y = row_tops[3]
        tasks = agent.get("assigned_tasks", [])
        human_tasks = [t for t in tasks if t.get("human_role", "")]

        if human_tasks:
            # 마지막 Task의 output을 HR로 전달
            last_task = tasks[-1] if tasks else None
            out_data = last_task.get("output_data", ["결과물"]) if last_task else ["결과물"]

            _add_arrow_line(slide, center_x, junior_bottom,
                            center_x, hr_top_y,
                            color=GOLD_ARROW, width=Pt(1.2))

            # output 데이터 라벨
            label_text = out_data[0][:12] if out_data else "결과물"
            _add_data_label(slide, center_x + Cm(0.1),
                            junior_bottom + Cm(0.05),
                            label_text, font_color=GOLD,
                            width=Cm(1.5), height=Cm(0.25))

    # ── (D) Senior → HR 직결 화살표 (감독 라인, 짙은 빨강) ──
    # 맨 오른쪽 Agent 오른편에 Senior에서 HR까지 내려오는 긴 화살표
    if agent_count > 0:
        right_edge_x = content_left + content_w - Cm(0.1)
        _add_arrow_line(slide, right_edge_x, row_tops[1] + senior_h,
                        right_edge_x, row_tops[3] + Cm(0.1),
                        color=RED_ARROW, width=Pt(1.5))
        # 수평선: Senior 오른쪽 끝에서 꺾임
        _add_line(slide, content_left + content_w - Cm(0.5), row_tops[1] + senior_h // 2,
                  right_edge_x, row_tops[1] + senior_h // 2,
                  color=RED_ARROW, width=Pt(1.5))
        _add_line(slide, right_edge_x, row_tops[1] + senior_h // 2,
                  right_edge_x, row_tops[1] + senior_h,
                  color=RED_ARROW, width=Pt(1.5))
        # 라벨
        _add_data_label(slide, right_edge_x - Cm(1.2),
                        row_tops[2] + junior_h // 2,
                        "감독·조율", font_color=RED,
                        width=Cm(1.0), height=Cm(0.25))
