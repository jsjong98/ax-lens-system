"""
ppt_flow_drawer.py — PPT에 AI Service Flow를 도형으로 직접 그리기

python-pptx 도형(사각형)만 사용하여 수정 가능한 스윔레인을 그립니다.
※ python-pptx add_connector 대신 OOXML cxnSp XML을 직접 생성하여 PPT 복구 오류를 방지합니다.
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

# Agent별 구분 색상 — 파란 계열 유지, 명도·채도 차이로 구분
_AGENT_PALETTE = [
    RGBColor(0x1A, 0x3C, 0x6E),   # 1  진남색 (가장 어두움)
    RGBColor(0x2E, 0x75, 0xB6),   # 2  중간 파란
    RGBColor(0x00, 0x82, 0x7F),   # 3  틸 (초록 기운)
    RGBColor(0x5B, 0x9B, 0xD5),   # 4  밝은 하늘
    RGBColor(0x4B, 0x00, 0x82),   # 5  인디고 (보라 기운)
    RGBColor(0x00, 0xA6, 0xA0),   # 6  밝은 청록
    RGBColor(0x41, 0x72, 0xC4),   # 7  코발트
    RGBColor(0x7B, 0x68, 0xC4),   # 8  퍼플블루
    RGBColor(0x00, 0x6E, 0x90),   # 9  페트롤
    RGBColor(0x87, 0xCE, 0xEB),   # 10 스카이 (가장 밝음)
]


def _agent_color(idx: int) -> RGBColor:
    return _AGENT_PALETTE[idx % len(_AGENT_PALETTE)]


# ── 기본 도형 헬퍼 ─────────────────────────────────────────────────────────────

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


# ── 레인 간 연결 색상 (참조 템플릿 기준) ──────────────────────────────────────
CONN_BLUE = RGBColor(0x4D, 0xAC, 0xF1)    # Input→Senior, Senior→Junior
CONN_GOLD = RGBColor(0xB4, 0x8E, 0x04)    # Junior→HR
CONN_RED = RGBColor(0x8B, 0x1A, 0x1A)     # Senior→HR (감독)
CONN_GRAY = RGBColor(0x99, 0x99, 0x99)    # Junior→Senior (피드백)
CONN_WIDTH = 12700                          # 1pt in EMU


def _make_cxnSp(slide, x1, y1, x2, y2, color=CONN_BLUE, width=CONN_WIDTH,
                 head_end=False, tail_end=True, bent=False):
    """참조 템플릿과 동일한 OOXML cxnSp 커넥터를 생성합니다.
    bent=True이면 꺾인 커넥터(bentConnector3)를 사용합니다."""
    from lxml import etree
    from pptx.oxml.ns import qn

    flip_h = x2 < x1
    flip_v = y2 < y1
    off_x = min(x1, x2)
    off_y = min(y1, y2)
    cx = abs(x2 - x1)
    cy = abs(y2 - y1)

    sp_tree = slide.shapes._spTree
    max_id = max(
        (int(el.get('id', '0'))
         for el in sp_tree.iter()
         if el.get('id', '').isdigit()),
        default=0,
    )
    new_id = max_id + 1
    color_hex = str(color)

    cxn = etree.SubElement(sp_tree, qn('p:cxnSp'))

    # nvCxnSpPr
    nv = etree.SubElement(cxn, qn('p:nvCxnSpPr'))
    cNvPr = etree.SubElement(nv, qn('p:cNvPr'))
    cNvPr.set('id', str(new_id))
    cNvPr.set('name', f'Connector {new_id}')
    cNvCxnSpPr = etree.SubElement(nv, qn('p:cNvCxnSpPr'))
    etree.SubElement(cNvCxnSpPr, qn('a:cxnSpLocks'))
    etree.SubElement(nv, qn('p:nvPr'))

    # spPr
    spPr = etree.SubElement(cxn, qn('p:spPr'))

    xfrm = etree.SubElement(spPr, qn('a:xfrm'))
    if flip_h:
        xfrm.set('flipH', '1')
    if flip_v:
        xfrm.set('flipV', '1')

    off = etree.SubElement(xfrm, qn('a:off'))
    off.set('x', str(int(off_x)))
    off.set('y', str(int(off_y)))
    ext = etree.SubElement(xfrm, qn('a:ext'))
    ext.set('cx', str(int(cx)))
    ext.set('cy', str(int(cy)))

    prstGeom = etree.SubElement(spPr, qn('a:prstGeom'))
    if bent:
        prstGeom.set('prst', 'bentConnector3')
        avLst = etree.SubElement(prstGeom, qn('a:avLst'))
        # 꺾임 지점: 50000 = 중간 (0~100000 범위)
        gd = etree.SubElement(avLst, qn('a:gd'))
        gd.set('name', 'adj1')
        gd.set('fmla', 'val 50000')
    else:
        prstGeom.set('prst', 'straightConnector1')
        etree.SubElement(prstGeom, qn('a:avLst'))

    ln = etree.SubElement(spPr, qn('a:ln'))
    ln.set('w', str(int(width)))
    ln.set('cap', 'sq')

    solidFill = etree.SubElement(ln, qn('a:solidFill'))
    srgbClr = etree.SubElement(solidFill, qn('a:srgbClr'))
    srgbClr.set('val', color_hex)

    if tail_end:
        te = etree.SubElement(ln, qn('a:tailEnd'))
        te.set('type', 'triangle')
    if head_end:
        he = etree.SubElement(ln, qn('a:headEnd'))
        he.set('type', 'triangle')

    # p:style (참조 템플릿 동일)
    style = etree.SubElement(cxn, qn('p:style'))
    for ref_tag, ref_idx, clr_val in [
        ('a:lnRef', '1', 'accent1'),
        ('a:fillRef', '0', 'accent1'),
        ('a:effectRef', '0', 'dk1'),
    ]:
        ref = etree.SubElement(style, qn(ref_tag))
        ref.set('idx', ref_idx)
        sc = etree.SubElement(ref, qn('a:schemeClr'))
        sc.set('val', clr_val)
    fontRef = etree.SubElement(style, qn('a:fontRef'))
    fontRef.set('idx', 'minor')
    sc = etree.SubElement(fontRef, qn('a:schemeClr'))
    sc.set('val', 'lt1')


def _arrow_v(slide, x, y1, y2, color=CONN_BLUE, width=CONN_WIDTH):
    """세로 화살표 (y1→y2 방향)."""
    _make_cxnSp(slide, x, y1, x, y2, color=color, width=width, tail_end=True)


def _draw_vline(slide, x, y1, y2, color=CONN_BLUE, width=CONN_WIDTH):
    """세로선 (화살표 머리 없음)."""
    _make_cxnSp(slide, x, y1, x, y2, color=color, width=width, tail_end=False)


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
    for i in range(agent_count):
        color = _agent_color(i)
        bw = agent_col_w * 0.75
        bx = content_left + i * agent_col_w + (agent_col_w - bw) / 2
        _add_rect(slide, bx, input_top + Cm(0.06), bw, input_h - Cm(0.12),
                  fill=WHITE, border_color=color, border_width=Pt(0.5))

    # ── Input→Junior 화살표 (먼저 그려서 Senior 바 뒤로) ──
    for i in range(agent_count):
        cx = content_left + i * agent_col_w + agent_col_w / 2
        c = _agent_color(i)
        _arrow_v(slide, cx, input_top + input_h, junior_top, c)

    # ── Senior AI 행 (화살표 위에 덮음) ──
    _add_rect(slide, left, senior_top, label_w, senior_h,
              fill=WHITE, border_color=LIGHT_GRAY,
              text="Senior\nAI", font_size=Pt(4), font_color=RED)
    _add_rect(slide, content_left, senior_top + Cm(0.04),
              content_w, senior_h - Cm(0.08),
              fill=RED_BG, border_color=RED, border_width=Pt(1.5))

    # ── Senior↔Junior 화살표 ──
    for i in range(agent_count):
        cx = content_left + i * agent_col_w + agent_col_w / 2
        _arrow_v(slide, cx - Cm(0.06), senior_top + senior_h, junior_top, CONN_RED)
        _arrow_v(slide, cx + Cm(0.06), junior_top, senior_top + senior_h, CONN_GRAY)

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
    for i, agent in enumerate(agents):
        has_hr = any(t.get("human_role", "") for t in agent.get("assigned_tasks", []))
        if has_hr:
            bx = content_left + i * agent_col_w + Cm(0.05)
            bw = agent_col_w - Cm(0.1)
            _add_rect(slide, bx, hr_top + Cm(0.05), bw, hr_h - Cm(0.1),
                      fill=GRAY_BG, border_color=GRAY_ARROW, border_width=Pt(0.3))

    # ── Junior→HR 화살표 (금색, HR 있는 경우만) ──
    for i, agent in enumerate(agents):
        cx = content_left + i * agent_col_w + agent_col_w / 2
        has_hr = any(t.get("human_role", "") for t in agent.get("assigned_tasks", []))
        if has_hr:
            _arrow_v(slide, cx, junior_top + junior_h, hr_top, CONN_GOLD)



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

    all_inps = list(dict.fromkeys(i for ai in agent_inputs for i in ai))[:10]
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

    # Agent별 컬럼 중앙 X 좌표 (화살표에 필요)
    agent_cxs: list[int] = []
    for i in range(agent_count):
        cl = content_left + i * agent_col_w
        agent_cxs.append(cl + agent_col_w // 2)

    # ══ 2. Input→Junior 꺾인 화살표 (먼저 그려서 Senior AI 바 뒤로) ══
    for i, agent in enumerate(agents):
        cx = agent_cxs[i]
        c = _agent_color(i)
        inps = agent_inputs[i]
        for inp in inps:
            sx = inp_cx.get(inp)
            if sx is not None:
                _make_cxnSp(slide, sx, r[0] + input_h, cx, r[2],
                            color=c, bent=True)

    # ══ 3. Senior AI 행 (화살표 위에 덮음) ══
    _add_rect(slide, left, r[1], label_w, senior_h,
              fill=WHITE, border_color=LIGHT_GRAY,
              text="Senior\nAI", font_size=Pt(6), font_color=RED)

    pname = workflow.get("process_name", "")
    _add_rect(slide, content_left + Cm(0.15), r[1] + Cm(0.1),
              content_w - Cm(0.3), senior_h - Cm(0.2),
              fill=RED_BG, border_color=RED, border_width=Pt(1.2),
              text=f"{pname} 오케스트레이터", font_size=Pt(6), font_color=RED, bold=True)

    # ══ 4. Senior↔Junior 화살표 (Senior 바 아래에) ══
    for i in range(agent_count):
        cx = agent_cxs[i]
        # Senior AI → Junior AI (빨간)
        _arrow_v(slide, cx - Cm(0.12), r[1] + senior_h, r[2], CONN_RED)
        # Junior AI → Senior AI 피드백 (회색)
        _arrow_v(slide, cx + Cm(0.12), r[2], r[1] + senior_h, CONN_GRAY)

    # ══ 5. Junior AI 행 ══
    _add_rect(slide, left, r[2], label_w, junior_h,
              fill=WHITE, border_color=LIGHT_GRAY,
              text="Junior\nAI", font_size=Pt(6), font_color=GOLD)

    for i, agent in enumerate(agents):
        cl = content_left + i * agent_col_w
        bx = cl + Cm(0.1)
        bw = agent_col_w - Cm(0.2)

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
                _arrow_v(slide, bx + bw / 2, ty - task_gap, ty, CONN_GOLD, Emu(9525))

    # ══ 6. HR 행 ══
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

    # ══ 7. Junior→HR 화살표 (금색, HR 있는 경우만) ══
    for i, agent in enumerate(agents):
        cx = agent_cxs[i]
        has_hr = any(t.get("human_role", "") for t in agent.get("assigned_tasks", []))
        if has_hr:
            _arrow_v(slide, cx, r[2] + junior_h, r[3], CONN_GOLD)
