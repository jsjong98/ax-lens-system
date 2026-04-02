"""
html_exporter.py — AI Service Flow를 PwC 표준 HTML로 내보내기

LLM 생성 Workflow 결과 → 스윔레인 HTML 변환
(Input → Senior AI → Junior AI → HR 담당자)
"""
from __future__ import annotations
import html as _html
from typing import Any


# Agent별 구분 파란 계열 팔레트 (최대 10개 Agent — PPT와 동일)
_AGENT_PALETTE = [
    "#1A3C6E",   # 1  진남색
    "#2E75B6",   # 2  중간 파란
    "#00827F",   # 3  틸
    "#5B9BD5",   # 4  밝은 하늘
    "#4B0082",   # 5  인디고
    "#00A6A0",   # 6  밝은 청록
    "#4172C4",   # 7  코발트
    "#7B68C4",   # 8  퍼플블루
    "#006E90",   # 9  페트롤
    "#87CEEB",   # 10 스카이
]


def _agent_color(idx: int) -> str:
    """Agent 인덱스에 대응하는 파란 계열 색상 hex를 반환."""
    return _AGENT_PALETTE[idx % len(_AGENT_PALETTE)]


_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Malgun Gothic', sans-serif;
       background: #F5F4F1; display: flex; justify-content: center; padding: 28px 16px; }
.slide { background: #fff; width: 100%; max-width: 1400px; padding: 22px 24px 24px; border-radius: 10px;
         box-shadow: 0 2px 16px rgba(0,0,0,0.08); }
.title-row { display: flex; justify-content: flex-end; margin-bottom: 16px; }
.legend { display: flex; gap: 8px; flex-wrap: wrap; }
.leg-btn { font-size: 11px; font-weight: 600; padding: 4px 12px; border-radius: 5px; }
.leg-senior { border: 1.5px solid #8B1A1A; color: #8B1A1A; background: #fff; }
.leg-junior { border: 1.5px solid #AA8E2A; color: #AA8E2A; background: #fff; }
.leg-human  { border: 1.5px solid #B4B2A9; color: #5F5E5A; background: #fff; }
.flow-outer { border: 0.5px solid #D3D1C7; border-radius: 10px; overflow: hidden; }
.row { display: grid; grid-template-columns: 56px 1fr; border-bottom: 0.5px solid #D3D1C7; }
.row:last-child { border-bottom: none; }
.row-label { display: flex; flex-direction: column; align-items: center; justify-content: center;
             gap: 3px; padding: 8px 4px; border-right: 0.5px solid #D3D1C7; background: #fff; }
.row-icon { font-size: 18px; }
.row-name { font-size: 9px; font-weight: 700; text-align: center; line-height: 1.3; }
.name-input { color: #5F5E5A; } .name-senior { color: #8B1A1A; }
.name-junior { color: #AA8E2A; } .name-human  { color: #2C2C2A; }
.row-content { padding: 10px 12px; }
.bg-input  .row-content { background: #F8FAFF; }
.bg-senior .row-content { background: #FDF4F4; }
.bg-junior .row-content { background: #FEFAF0; }
.bg-human  .row-content { background: #FAFAF8; }
.input-boxes { display: flex; gap: 8px; flex-wrap: wrap; }
.ibox { flex: 1; min-width: 100px; border-radius: 7px; padding: 8px 6px 6px;
        border: 1.5px solid #5B9BD5; background: #fff; text-align: center; position: relative; }
.ibox-t { font-size: 9.5px; font-weight: 600; color: #2C2C2A; margin-bottom: 3px; }
.ibox-s { font-size: 8px; color: #888780; }
.ibox-lbl { font-size: 7px; font-style: italic; margin-top: 3px; }
.senior-box { border: 1.5px solid #8B1A1A; border-radius: 8px; background: #F8E0E0; padding: 10px 16px; text-align: center; }
.s-title { font-size: 13px; font-weight: 700; color: #8B1A1A; margin-bottom: 4px; }
.s-sub   { font-size: 9px; color: #888780; }
.agents-grid { display: grid; gap: 10px; }
.agent-col { display: flex; flex-direction: column; }
.conn { display: flex; justify-content: space-between; align-items: flex-end; padding: 2px 8px 0; }
.cs { display: flex; flex-direction: column; align-items: center; gap: 2px; }
.lbl-down { font-size: 7px; font-weight: 600; text-align: center; line-height: 1.3; }
.lbl-up   { font-size: 7px; color: #9E9E9E; font-weight: 600; text-align: center; line-height: 1.3; }
.ard { display: flex; flex-direction: column; align-items: center; }
.ard .ln { width: 1.5px; height: 18px; }
.ard .hd { width: 0; height: 0; border-left: 4px solid transparent; border-right: 4px solid transparent; }
.aru { display: flex; flex-direction: column-reverse; align-items: center; }
.aru .ln { width: 1.5px; height: 18px; background: #9E9E9E; }
.aru .hd { width: 0; height: 0; border-left: 4px solid transparent; border-right: 4px solid transparent; border-bottom: 6px solid #9E9E9E; }
.bot-arr { display: flex; flex-direction: column; align-items: center; padding-top: 5px; gap: 2px; }
.ardb { display: flex; flex-direction: column; align-items: center; }
.ardb .ln { width: 1.5px; height: 16px; background: #B48E04; }
.ardb .hd { width: 0; height: 0; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 6px solid #B48E04; }
.bot-lbl { font-size: 7.5px; font-weight: 600; color: #B48E04; font-style: italic; }
.agent-box { border-radius: 8px; padding: 10px; background: #FEFAF0; flex: 1; }
.ah { display: flex; align-items: center; gap: 7px; margin-bottom: 9px; }
.an { width: 20px; height: 20px; border-radius: 50%; background: #AA8E2A; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 700; color: #fff; flex-shrink: 0; }
.aname { font-size: 11px; font-weight: 700; color: #2C2C2A; }
.ah-sub { font-size: 8px; color: #888780; margin-left: 2px; }
.bl { display: flex; flex-direction: column; gap: 6px; }
.b { border-radius: 6px; padding: 6px 8px 5px; border: 0.7px dashed #AA8E2A; background: #F5F4F1; text-align: center; }
.b.hf { background: #FAEEDA; border: 0.7px dashed #BA7517; }
.bt { font-size: 9px; font-weight: 600; color: #2C2C2A; margin-bottom: 3px; }
.bs { font-size: 8px; color: #888780; margin-bottom: 3px; }
.bbr { display: flex; justify-content: center; gap: 4px; flex-wrap: wrap; }
.badge { font-size: 7.5px; font-weight: 500; padding: 1px 7px; border-radius: 8px; white-space: nowrap; }
.bg  { background: #FAEEDA; color: #633806; border: 0.5px solid #BA7517; }
.bp  { background: #E1F5EE; color: #085041; border: 0.5px solid #1D9E75; }
.br  { background: #F1EFE8; color: #5F5E5A; border: 0.5px solid #888780; }
.bra { background: #E8F4FF; color: #0C447C; border: 0.5px solid #378ADD; }
.bh  { background: #FCEBEB; color: #A32D2D; border: 0.5px solid #F09595; }
.bo  { background: #EEEDFE; color: #3C3489; border: 0.5px solid #7F77DD; }
.hr-box { border-radius: 7px; padding: 9px 8px; border: 0.5px solid #D3D1C7; background: #fff; text-align: center; }
.hr-m { font-size: 9px; font-weight: 600; color: #2C2C2A; margin-bottom: 3px; }
.hr-s { font-size: 8px; color: #888780; }
.task-arrow { display: flex; flex-direction: column; align-items: center; padding: 2px 0; }
.task-arrow .ln { width: 1px; height: 8px; background: #AA8E2A; }
.task-arrow .hd { width: 0; height: 0; border-left: 3px solid transparent; border-right: 3px solid transparent; border-top: 4px solid #AA8E2A; }
.task-arrow-lbl { font-size: 6.5px; color: #AA8E2A; font-style: italic; }
.oversight-line { position: relative; }
.oversight-bar { position: absolute; right: -8px; top: 0; bottom: 0; width: 3px; background: #8B1A1A; border-radius: 2px; }
.oversight-lbl { position: absolute; right: -50px; top: 50%; transform: translateY(-50%) rotate(90deg); font-size: 7px; color: #8B1A1A; font-weight: 600; white-space: nowrap; }
"""

BADGE_MAP = {
    "LLM": "bg", "RAG": "bra", "RPA": "bra", "Rule-based": "br", "Rule": "br",
    "Tabular": "bp", "OCR": "bo", "ML": "bo", "최적화": "bo", "API": "bra",
    "Template": "br", "Chatbot": "bg",
}


def _badge_html(technique: str) -> str:
    """AI 기법 문자열에서 뱃지 HTML 생성."""
    parts = [t.strip() for t in technique.replace("+", ",").replace("·", ",").split(",") if t.strip()]
    badges = []
    for p in parts:
        cls = BADGE_MAP.get(p, "br")
        badges.append(f'<span class="badge {cls}">{p}</span>')
    return " ".join(badges)


def _has_human(task: dict) -> bool:
    """Task에 Human 확인이 필요한지 판단."""
    level = task.get("automation_level", "")
    return "in-the-Loop" in level or "Supervised" in level


def export_workflow_html(workflow: dict) -> str:
    """Workflow 결과를 PwC 표준 AI Service Flow HTML로 변환합니다."""
    process_name = workflow.get("process_name", "AI Workflow")
    agents = workflow.get("agents", [])
    summary = workflow.get("blueprint_summary", "")

    # Input 수집 + Input→Agent 매핑 (첫 사용 Agent 기준 색상 결정)
    all_inputs: list[str] = []
    seen_inputs: set[str] = set()
    input_to_agent_idx: dict[str, int] = {}
    for ai, agent in enumerate(agents):
        for task in agent.get("assigned_tasks", []):
            for inp in task.get("input_data", []):
                if inp and inp not in seen_inputs:
                    seen_inputs.add(inp)
                    all_inputs.append(inp)
                    input_to_agent_idx[inp] = ai

    # Human Task 수집
    human_tasks: list[dict] = []
    for agent in agents:
        for task in agent.get("assigned_tasks", []):
            if _has_human(task):
                human_tasks.append({
                    "name": task.get("human_role", "") or f"{task.get('task_name', '')} 검토",
                    "desc": task.get("human_role", "최종 확인"),
                    "agent_idx": agents.index(agent),
                })

    agent_count = len(agents)
    grid_cols = f"repeat({max(agent_count, 1)}, 1fr)"

    # ── HTML 조립 ──

    # Input 행 — Agent별 색상으로 테두리 구분 + 데이터 흐름 라벨
    input_boxes = ""
    for inp in all_inputs[:6]:
        owner_idx = input_to_agent_idx.get(inp, 0)
        color = _agent_color(owner_idx)
        owner_name = agents[owner_idx].get("agent_name", f"Agent {owner_idx+1}") if owner_idx < len(agents) else ""
        input_boxes += (
            f'<div class="ibox" style="border-color:{color};">'
            f'<div class="ibox-t">{_html.escape(inp)}</div>'
            f'<div class="ibox-lbl" style="color:{color};">→ {_html.escape(owner_name)}</div>'
            f'</div>\n'
        )

    # Senior AI 행
    agent_names = [a.get("agent_name", f"Agent {i+1}") for i, a in enumerate(agents)]
    steps = []
    for i, name in enumerate(agent_names):
        steps.append(f"Agent {i+1}")
    if len(steps) >= 2:
        parallel = "·".join(steps[:2]) + " 병렬 기동"
        rest = " → ".join(f"{s} 결과 수령" for s in steps[:2])
        if len(steps) > 2:
            orchestrator_desc = f"({parallel} → {rest} → {steps[2]} 기동 → 최종 결과 수령)"
        else:
            orchestrator_desc = f"({parallel} → {rest} → HR 담당자 전달)"
    else:
        orchestrator_desc = f"({steps[0]} 기동 → 결과 수령 → HR 담당자 전달)"

    # Junior AI 행
    circled = "①②③④⑤⑥⑦⑧⑨⑩"

    # 커넥터 행 — Senior→Junior: RED (#8B1A1A), Junior→Senior: GRAY (#9E9E9E)
    connectors_html = ""
    for i, agent in enumerate(agents):
        num = circled[i] if i < len(circled) else str(i + 1)

        parallel = " (병렬)" if i > 0 and i < len(agents) - 1 else ""
        sequential = " (순차)" if i == len(agents) - 1 and len(agents) > 1 else ""

        connectors_html += f"""
          <div class="conn">
            <div class="cs">
              <span class="lbl-down" style="color:#8B1A1A;">{num} {_html.escape(agent.get('agent_name', ''))}<br>지시{parallel}{sequential}</span>
              <div class="ard"><div class="ln" style="background:#8B1A1A;"></div><div class="hd" style="border-top-color:#8B1A1A;"></div></div>
            </div>
            <div class="cs">
              <div class="aru"><div class="ln"></div><div class="hd"></div></div>
              <span class="lbl-up">{_html.escape(agent.get('agent_name', ''))}<br>결과 반환</span>
            </div>
          </div>"""

    # 에이전트 박스 행 — 금색 테두리 + Task간 화살표에 데이터 라벨
    agents_html = ""
    for i, agent in enumerate(agents):
        color = _agent_color(i)
        tasks_list = agent.get("assigned_tasks", [])
        tasks_html = ""
        has_human_task = False

        for j, task in enumerate(tasks_list):
            is_human = _has_human(task)
            if is_human:
                has_human_task = True
            hf_cls = ' hf' if is_human else ''
            technique = agent.get("ai_technique", "")
            badges = _badge_html(technique)
            if is_human:
                human_role = task.get("human_role", "Human 확인")
                badges += f' <span class="badge bh">{_html.escape(human_role[:15])}</span>'

            task_name = task.get("task_name", "")
            ai_role = task.get("ai_role", "")

            # Task간 화살표 + output 데이터 라벨
            if j > 0:
                prev_outputs = tasks_list[j-1].get("output_data", [])
                lbl = prev_outputs[0][:15] if prev_outputs else ""
                tasks_html += f"""
                <div class="task-arrow">
                  <div class="ln"></div><div class="hd"></div>
                  {f'<div class="task-arrow-lbl">{_html.escape(lbl)}</div>' if lbl else ''}
                </div>"""

            tasks_html += f"""
                <div class="b{hf_cls}">
                  <div class="bt">{_html.escape(task_name)}</div>
                  <div class="bs">{_html.escape(ai_role)}</div>
                  <div class="bbr">{badges}</div>
                </div>"""

        # L4 서브타이틀
        l4_sub = ""
        first_task = (agent.get("assigned_tasks") or [{}])[0] if agent.get("assigned_tasks") else {}
        l4_val = first_task.get("l4", "")
        if l4_val:
            l4_sub = f'<div class="ah-sub">L4: {_html.escape(l4_val)}</div>'

        # Junior→HR 화살표 + output 데이터 라벨
        arrow_html = ""
        if has_human_task:
            last_outputs = tasks_list[-1].get("output_data", ["결과물"]) if tasks_list else ["결과물"]
            out_label = last_outputs[0][:15] if last_outputs else "결과물"
            arrow_html = f"""
            <div class="bot-arr">
              <span class="bot-lbl">{_html.escape(out_label)}</span>
              <div class="ardb"><div class="ln"></div><div class="hd"></div></div>
            </div>"""

        agents_html += f"""
          <div class="agent-col">
            <div class="agent-box" style="border: 1.5px solid #AA8E2A;">
              <div class="ah">
                <div class="an">{i+1}</div>
                <div>
                  <div class="aname">{_html.escape(agent.get('agent_name', ''))}</div>
                  {l4_sub}
                </div>
              </div>
              <div class="bl">{tasks_html}
              </div>
            </div>{arrow_html}
          </div>"""

    # HR 담당자 행
    hr_html = ""
    for i in range(agent_count):
        agent_humans = [h for h in human_tasks if h["agent_idx"] == i]
        if agent_humans:
            names = ", ".join(_html.escape(h["name"]) for h in agent_humans)
            descs = ", ".join(_html.escape(h["desc"]) for h in agent_humans)
            hr_html += f"""
          <div class="hr-box">
            <div class="hr-m">{names}</div>
            <div class="hr-s">{descs}</div>
          </div>"""
        else:
            hr_html += "<div></div>"

    # 범례에 Agent별 색상 표시
    legend_agents = ""
    for i, a in enumerate(agents):
        color = _agent_color(i)
        name = a.get("agent_name", f"Agent {i+1}")
        legend_agents += f'<div class="leg-btn" style="border-color:{color};color:{color};">{_html.escape(name)}</div>'

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>AI Service Flow — {_html.escape(process_name)}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="slide">
  <div class="title-row">
    <div class="legend">
      <div class="leg-btn leg-senior">Senior AI</div>
      <div class="leg-btn leg-junior">Junior AI</div>
      <div class="leg-btn leg-human">사람</div>
      {legend_agents}
    </div>
  </div>
  <div class="flow-outer">

    <!-- INPUT -->
    <div class="row bg-input">
      <div class="row-label"><div class="row-icon">📥</div><div class="row-name name-input">Input</div></div>
      <div class="row-content">
        <div class="input-boxes">{input_boxes}</div>
      </div>
    </div>

    <!-- SENIOR AI -->
    <div class="row bg-senior">
      <div class="row-label"><div class="row-icon">🤖</div><div class="row-name name-senior">Senior<br>AI</div></div>
      <div class="row-content">
        <div class="senior-box">
          <div class="s-title">{process_name} 오케스트레이터</div>
          <div class="s-sub">{orchestrator_desc}</div>
        </div>
      </div>
    </div>

    <!-- JUNIOR AI -->
    <div class="row bg-junior">
      <div class="row-label"><div class="row-icon">🔧</div><div class="row-name name-junior">Junior<br>AI</div></div>
      <div class="row-content">
        <div class="agents-grid" style="grid-template-columns: {grid_cols};">
          {connectors_html}
        </div>
        <div class="agents-grid" style="grid-template-columns: {grid_cols}; margin-top: 4px;">
          {agents_html}
        </div>
      </div>
    </div>

    <!-- HR 담당자 (Senior AI → HR 감독: RED) -->
    <div class="row bg-human">
      <div class="row-label"><div class="row-icon">👤</div><div class="row-name name-human">HR<br>담당자</div></div>
      <div class="row-content">
        <div class="oversight-line">
          <div class="agents-grid" style="grid-template-columns: {grid_cols};">
            {hr_html}
          </div>{'<div class="oversight-bar"></div><div class="oversight-lbl">Senior AI 감독</div>' if human_tasks else ''}
        </div>
      </div>
    </div>

  </div>
</div>
</body>
</html>"""
