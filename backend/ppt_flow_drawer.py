"""
ppt_flow_drawer.py — PPT에 AI Service Flow를 도형으로 직접 그리기

python-pptx 도형(사각형)만 사용하여 수정 가능한 스윔레인을 그립니다.
※ add_connector는 PPT 복구 오류를 유발하므로 사용하지 않습니다.
- draw_service_flow: 전체 AI Service Flow (과제 설계서용)
- draw_minimap: 축소 미니맵 (Agent 정의서용, 특정 Agent 강조)
"""
from __future__ import annotations

from pptx.util import Pt, Emu, Cm
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE


# ── 색상 ──────────────────────────────────────────────────────────────────────

RED = RGBColor(0x8B, 0x1A, 0x1A)
RED_BG = RGBColor(0xF8, 0xE0, 0xE0)
GOLD = RGBColor(0xAA, 0x8E, 0x2A)
GRAY = RGBColor(0x88, 0x87, 0x80)
GRAY_ARROW = RGBColor(0x9E, 0x9E, 0x9E)
LIGHT_GRAY = RGBColor(0xD3, 0xD1, 0xC7)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
BLACK = RGBColor(0x2C, 0x2C, 0x2A)
YELLOW_BG = RGBColor(0xFE, 0xFA, 0xF0)
GRAY_BG = RGBColor(0xF5, 0xF5, 0xF3)
INPUT_BG = RGBColor(0xF5, 0xF4, 0xF1)

_AGENT_BLUE_PALETTE = [
    RGBColor(0x2E, 0x75, 0xB6),
    RGBColor(0x00, 0xA6, 0xA0),
    RGBColor(0x5B, 0x9B, 0xD5),
    RGBColor(0x7B, 0x68, 0xC4),
    RGBColor(0x00, 0x82, 0x7F),
    RGBColor(0x41, 0x72, 0xC4),
    RGBColor(0x2D, 0x8B, 0xBA),
]


def _agent_color(idx: int) -> RGBColor:
    return _AGENT_BLUE_PALETTE[idx % len(_AGENT_BLUE_PALETTE)]


# ── 기본 도형 헬퍼 (커넥터 사용 안 함) ────────────────────────────────────────

def _add_rect(slide, left, top, width, height, fill=None, border_color=None,
              border_width=Pt(1), border_dash=None, text="", font_size=Pt(8),
              font_color=BLACK, bold=False, align=PP_ALIGN.CENTER):
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


def _draw_vline(slide, x, y1, y2, color=LIGHT_GRAY, width=Pt(1)):
    """세로선을 얇은 사각형으로 그립니다 (커넥터 대신)."""
    top = min(y1, y2)
    h = abs(y2 - y1)
    w = max(int(width), Emu(12700))  # 최소 1pt
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x - w // 2, top, w, h)
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    return shape


def _draw_hline(slide, y, x1, x2, color=LIGHT_GRAY, width=Pt(1)):
    """가로선을 얇은 사각형으로 그립니다."""
    left = min(x1, x2)
    w = abs(x2 - x1)
    h = max(int(width), Emu(12700))
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, y - h // 2, w, h)
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    return shape


def _draw_arrow_down(slide, x, y, color=LIGHT_GRAY, size=Cm(0.15)):
    """아래 방향 화살표 머리 (▼ 다이아몬드로 대체, 회전 없이 안정적)."""
    shape = slide.shapes.add_shape(
        MSO_SHAPE.DIAMOND, x - size, y - size // 2, size * 2, size)
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    return shape


def _draw_arrow_up(slide, x, y, color=LIGHT_GRAY, size=Cm(0.15)):
    """위 방향 화살표 머리 (▲ 다이아몬드로 대체)."""
    shape = slide.shapes.add_shape(
        MSO_SHAPE.DIAMOND, x - size, y - size // 2, size * 2, size)
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    return shape


def _arrow_v(slide, x, y1, y2, color=LIGHT_GRAY, width=Pt(1)):
    """세로 화살표 (선 + 화살표 머리). y1→y2 방향."""
    _draw_vline(slide, x, y1, y2, color, width)
    if y2 > y1:
        _draw_arrow_down(slide, x, y2, color, size=Cm(0.1))
    else:
        _draw_arrow_up(slide, x, y1, color, size=Cm(0.1))


# ══════════════════════════════════════════════════════════════════════════════
# 미니맵 그리기 (Agent 정의서용)
# 템플릿 그룹132: L=24.4cm, T=3.7cm, W=7.8cm, H=5.7cm
# ══════════════════════════════════════════════════════════════════════════════

def draw_minimap(slide, workflow: dict, highlight_agent_id: str = "",
                 left=Cm(24.4), top=Cm(3.7), total_width=Cm(7.8), total_height=Cm(5.7)):
    agents = workflow.get("agents", [])
    if not agents:
        return

    agent_count = len(agents)
    label_w = Cm(1.0)
    content_w = total_width - label_w
    agent_col_w = content_w / max(agent_count, 1)
    content_left = left + label_w

    # 레인 높이 배분
    input_h  = Cm(0.7)
    gap1     = Cm(0.25)
    senior_h = Cm(0.7)
    gap2     = Cm(0.3)
    junior_h = Cm(2.2)
    gap3     = Cm(0.25)
    hr_h     = Cm(0.7)

    input_top  = top + Cm(0.15)
    senior_top = input_top + input_h + gap1
    junior_top = senior_top + senior_h + gap2
    hr_top     = junior_top + junior_h + gap3

    # ── Input 행 ──
    _add_rect(slide, left, input_top, label_w, input_h,
              fill=WHITE, border_color=LIGHT_GRAY,
              text="Input", font_size=Pt(4), font_color=GRAY)
    for i in range(min(agent_count, 6)):
        color = _agent_color(i)
        bw = agent_col_w * 0.75
        bx = content_left + i * agent_col_w + (agent_col_w - bw) / 2
        _add_rect(slide, bx, input_top + Cm(0.06), bw, input_h - Cm(0.12),
                  fill=WHITE, border_color=color, border_width=Pt(0.5))

    # ── Senior AI 행 ──
    _add_rect(slide, left, senior_top, label_w, senior_h,
              fill=WHITE, border_color=LIGHT_GRAY,
              text="Senior\nAI", font_size=Pt(4), font_color=RED)
    _add_rect(slide, content_left, senior_top + Cm(0.04),
              content_w, senior_h - Cm(0.08),
              fill=RED_BG, border_color=RED, border_width=Pt(0.7))

    # ── Junior AI 행 ──
    _add_rect(slide, left, junior_top, label_w, junior_h,
              fill=WHITE, border_color=LIGHT_GRAY,
              text="Junior\nAI", font_size=Pt(4), font_color=GOLD)

    for i, agent in enumerate(agents):
        bx = content_left + i * agent_col_w + Cm(0.05)
        bw = agent_col_w - Cm(0.1)
        is_hl = agent.get("agent_id") == highlight_agent_id

        _add_rect(slide, bx, junior_top + Cm(0.05), bw, junior_h - Cm(0.1),
                  fill=YELLOW_BG if is_hl else WHITE,
                  border_color=GOLD,
                  border_width=Pt(2) if is_hl else Pt(0.4))

        # 번호 배지
        _add_rect(slide, bx + Cm(0.04), junior_top + Cm(0.1), Cm(0.3), Cm(0.3),
                  fill=GOLD if is_hl else LIGHT_GRAY,
                  text=str(i + 1), font_size=Pt(4),
                  font_color=WHITE if is_hl else BLACK, bold=True)

        # Task 박스
        tasks = agent.get("assigned_tasks", [])
        for j in range(min(len(tasks), 3)):
            ty = junior_top + Cm(0.5) + j * Cm(0.4)
            _add_rect(slide, bx + Cm(0.06), ty,
                      bw - Cm(0.12), Cm(0.3),
                      fill=INPUT_BG, border_color=GOLD, border_width=Pt(0.2),
                      border_dash=7)

    # ── HR 행 ──
    _add_rect(slide, left, hr_top, label_w, hr_h,
              fill=WHITE, border_color=LIGHT_GRAY,
              text="HR\n담당자", font_size=Pt(4), font_color=BLACK)
    for i in range(agent_count):
        bx = content_left + i * agent_col_w + Cm(0.05)
        bw = agent_col_w - Cm(0.1)
        _add_rect(slide, bx, hr_top + Cm(0.05), bw, hr_h - Cm(0.1),
                  fill=GRAY_BG, border_color=GRAY_ARROW, border_width=Pt(0.3))

    # ── 연결선 ──
    for i in range(agent_count):
        cx = content_left + i * agent_col_w + agent_col_w / 2
        c = _agent_color(i)
        # Input → Senior
        _arrow_v(slide, cx, input_top + input_h, senior_top, c, Pt(0.5))
        # Senior → Junior
        _arrow_v(slide, cx - Cm(0.06), senior_top + senior_h, junior_top, c, Pt(0.5))
        # Junior → Senior
        _arrow_v(slide, cx + Cm(0.06), junior_top, senior_top + senior_h, GRAY_ARROW, Pt(0.5))
        # Junior → HR
        _arrow_v(slide, cx, junior_top + junior_h, hr_top, GOLD, Pt(0.5))

    # Senior → HR 감독 (오른쪽)
    rx = content_left + content_w - Cm(0.05)
    _draw_vline(slide, rx, senior_top + senior_h, hr_top, RED, Pt(0.7))
    _draw_arrow_down(slide, rx, hr_top, RED, Cm(0.08))


# ══════════════════════════════════════════════════════════════════════════════
# 전체 AI Service Flow 그리기 (과제 설계서용)
# 템플릿 영역: L=1.0cm, T=3.7cm, W=18.3cm, H=13.5cm
# ══════════════════════════════════════════════════════════════════════════════

def draw_service_flow(slide, workflow: dict,
                      left=Cm(1.0), top=Cm(3.7), total_width=Cm(18.3), total_height=Cm(13.5)):
    agents = workflow.get("agents", [])
    if not agents:
        return

    agent_count = len(agents)
    label_w = Cm(1.2)
    content_w = total_width - label_w
    agent_col_w = content_w / max(agent_count, 1)
    content_left = left + label_w

    # 레인 높이 (전체 13.5cm에 맞춤)
    input_h  = Cm(1.2)
    gap_is   = Cm(0.5)
    senior_h = Cm(1.2)
    gap_sj   = Cm(0.6)
    junior_h = Cm(7.5)
    gap_jh   = Cm(0.5)
    hr_h     = Cm(1.2)
    # 합계: 1.2+0.5+1.2+0.6+7.5+0.5+1.2 = 12.7cm < 13.5cm ✓

    r = [top]
    r.append(r[0] + input_h + gap_is)
    r.append(r[1] + senior_h + gap_sj)
    r.append(r[2] + junior_h + gap_jh)

    # ── 레인 배경 ──
    _add_rect(slide, content_left, r[2], content_w, junior_h,
              fill=YELLOW_BG, border_color=None)

    # ══ 1. Input 행 ══
    _add_rect(slide, left, r[0], label_w, input_h,
              fill=WHITE, border_color=LIGHT_GRAY,
              text="Input", font_size=Pt(6), font_color=GRAY)

    # Agent별 Input 수집
    agent_inputs: list[list[str]] = []
    input_owner: dict[str, int] = {}
    for ai, a in enumerate(agents):
        inps: list[str] = []
        for t in a.get("assigned_tasks", []):
            for inp in t.get("input_data", []):
                if inp not in inps:
                    inps.append(inp)
                if inp not in input_owner:
                    input_owner[inp] = ai
        agent_inputs.append(inps)

    all_inps = list(dict.fromkeys(i for ai in agent_inputs for i in ai))[:6]
    inp_w = content_w / max(len(all_inps), 1)
    inp_cx: dict[str, int] = {}

    for i, inp in enumerate(all_inps):
        bx = content_left + i * inp_w + Cm(0.08)
        bw = inp_w - Cm(0.16)
        oi = input_owner.get(inp, 0)
        c = _agent_color(oi)
        _add_rect(slide, bx, r[0] + Cm(0.1), bw, input_h - Cm(0.2),
                  fill=WHITE, border_color=c, border_width=Pt(1),
                  text=inp[:15], font_size=Pt(5), font_color=BLACK)
        inp_cx[inp] = bx + bw // 2

    # ══ 2. Senior AI 행 ══
    _add_rect(slide, left, r[1], label_w, senior_h,
              fill=WHITE, border_color=LIGHT_GRAY,
              text="Senior\nAI", font_size=Pt(6), font_color=RED)

    pname = workflow.get("process_name", "")
    _add_rect(slide, content_left + Cm(0.15), r[1] + Cm(0.1),
              content_w - Cm(0.3), senior_h - Cm(0.2),
              fill=RED_BG, border_color=RED, border_width=Pt(1.2),
              text=f"{pname} 오케스트레이터", font_size=Pt(6), font_color=RED, bold=True)

    # ══ 3. Junior AI 행 ══
    _add_rect(slide, left, r[2], label_w, junior_h,
              fill=WHITE, border_color=LIGHT_GRAY,
              text="Junior\nAI", font_size=Pt(6), font_color=GOLD)

    agent_cxs: list[int] = []
    for i, agent in enumerate(agents):
        cl = content_left + i * agent_col_w
        bx = cl + Cm(0.1)
        bw = agent_col_w - Cm(0.2)
        cx = cl + agent_col_w // 2
        agent_cxs.append(cx)

        _add_rect(slide, bx, r[2] + Cm(0.2), bw, junior_h - Cm(0.3),
                  fill=YELLOW_BG, border_color=GOLD, border_width=Pt(1))

        # 번호
        _add_rect(slide, bx + Cm(0.06), r[2] + Cm(0.28), Cm(0.4), Cm(0.4),
                  fill=GOLD, text=str(i + 1), font_size=Pt(6), font_color=WHITE, bold=True)

        # Task 박스
        tasks = agent.get("assigned_tasks", [])
        task_h = Cm(0.5)
        task_gap = Cm(0.2)
        max_t = min(len(tasks), int((junior_h - Cm(1.2)) / (task_h + task_gap)))

        for j in range(max_t):
            t = tasks[j]
            ty = r[2] + Cm(0.85) + j * (task_h + task_gap)
            _add_rect(slide, bx + Cm(0.1), ty, bw - Cm(0.2), task_h,
                      fill=INPUT_BG, border_color=GOLD, border_width=Pt(0.5),
                      border_dash=7,
                      text=t.get("task_name", "")[:18], font_size=Pt(4.5), font_color=BLACK)
            if j > 0:
                _arrow_v(slide, bx + bw / 2, ty - task_gap, ty, GOLD, Pt(0.5))

    # ══ 4. HR 행 ══
    _add_rect(slide, left, r[3], label_w, hr_h,
              fill=WHITE, border_color=LIGHT_GRAY,
              text="HR\n담당자", font_size=Pt(6), font_color=BLACK)

    for i, agent in enumerate(agents):
        cl = content_left + i * agent_col_w
        human_tasks = [t for t in agent.get("assigned_tasks", []) if t.get("human_role", "")]
        if human_tasks:
            _add_rect(slide, cl + Cm(0.1), r[3] + Cm(0.1),
                      agent_col_w - Cm(0.2), hr_h - Cm(0.2),
                      fill=WHITE, border_color=GRAY_ARROW, border_width=Pt(0.7),
                      text=human_tasks[0].get("human_role", "검토")[:18],
                      font_size=Pt(4.5), font_color=BLACK)

    # ══ 5. 연결 화살표 ══
    for i in range(agent_count):
        cx = agent_cxs[i]
        c = _agent_color(i)

        # (A) Input → Senior: 첫 Input만 직선
        inps = agent_inputs[i]
        if inps:
            sx = inp_cx.get(inps[0], cx)
            # 직선 연결 (간결)
            _arrow_v(slide, sx, r[0] + input_h, r[1], c, Pt(0.7))

        # (B) Senior ↔ Junior
        _arrow_v(slide, cx - Cm(0.12), r[1] + senior_h, r[2], c, Pt(0.7))
        _arrow_v(slide, cx + Cm(0.12), r[2], r[1] + senior_h, GRAY_ARROW, Pt(0.7))

        # (C) Junior → HR
        _arrow_v(slide, cx, r[2] + junior_h, r[3], GOLD, Pt(0.7))

    # (D) Senior → HR 감독선 (오른쪽 끝)
    if agent_count > 0:
        rx = content_left + content_w - Cm(0.08)
        _draw_vline(slide, rx, r[1] + senior_h, r[3], RED, Pt(1))
        _draw_arrow_down(slide, rx, r[3], RED, Cm(0.1))
