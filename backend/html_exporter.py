"""
html_exporter.py — AI Service Flow를 PwC 표준 HTML로 내보내기

LLM 생성 Workflow 결과 → 스윔레인 HTML 변환
(Input → Senior AI → Junior AI → HR 담당자)
"""
from __future__ import annotations
from typing import Any


_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Malgun Gothic', sans-serif;
       background: #F5F4F1; display: flex; justify-content: center; padding: 28px 16px; }
.slide { background: #fff; width: 960px; padding: 22px 24px 24px; border-radius: 10px;
         box-shadow: 0 2px 16px rgba(0,0,0,0.08); }
.title-row { display: flex; justify-content: flex-end; margin-bottom: 16px; }
.legend { display: flex; gap: 8px; }
.leg-btn { font-size: 11px; font-weight: 600; padding: 4px 12px; border-radius: 5px; }
.leg-senior { border: 1.5px solid #CC0000; color: #CC0000; background: #fff; }
.leg-junior { border: 1.5px solid #1A5CB0; color: #1A5CB0; background: #fff; }
.leg-human  { border: 1.5px solid #B4B2A9; color: #5F5E5A; background: #fff; }
.flow-outer { border: 0.5px solid #D3D1C7; border-radius: 10px; overflow: hidden; }
.row { display: grid; grid-template-columns: 56px 1fr; border-bottom: 0.5px solid #D3D1C7; }
.row:last-child { border-bottom: none; }
.row-label { display: flex; flex-direction: column; align-items: center; justify-content: center;
             gap: 3px; padding: 8px 4px; border-right: 0.5px solid #D3D1C7; background: #fff; }
.row-icon { font-size: 18px; }
.row-name { font-size: 9px; font-weight: 700; text-align: center; line-height: 1.3; }
.name-input { color: #5F5E5A; } .name-senior { color: #CC0000; }
.name-junior { color: #1A5CB0; } .name-human  { color: #2C2C2A; }
.row-content { padding: 10px 12px; }
.bg-input  .row-content { background: #FAFAF8; }
.bg-senior .row-content { background: #FDF4F4; }
.bg-junior .row-content { background: #FEFAF0; }
.bg-human  .row-content { background: #FAFAF8; }
.input-boxes { display: flex; gap: 8px; flex-wrap: wrap; }
.ibox { flex: 1; min-width: 100px; border-radius: 7px; padding: 8px 6px 6px; border: 0.5px solid #D3D1C7; background: #F5F4F1; text-align: center; }
.ibox-t { font-size: 9.5px; font-weight: 600; color: #2C2C2A; margin-bottom: 3px; }
.ibox-s { font-size: 8px; color: #888780; }
.senior-box { border: 1.5px solid #CC0000; border-radius: 8px; background: #FFF5F5; padding: 10px 16px; text-align: center; }
.s-title { font-size: 13px; font-weight: 700; color: #CC0000; margin-bottom: 4px; }
.s-sub   { font-size: 9px; color: #888780; }
.agents-grid { display: grid; gap: 10px; }
.agent-col { display: flex; flex-direction: column; }
.conn { display: flex; justify-content: space-between; align-items: flex-end; padding: 2px 8px 0; }
.cs { display: flex; flex-direction: column; align-items: center; gap: 2px; }
.lbl-r { font-size: 7px; color: #CC0000; font-weight: 600; text-align: center; line-height: 1.3; }
.lbl-b { font-size: 7px; color: #1A5CB0; font-weight: 600; text-align: center; line-height: 1.3; }
.ard { display: flex; flex-direction: column; align-items: center; }
.ard .ln { width: 1.5px; height: 18px; background: #CC0000; }
.ard .hd { width: 0; height: 0; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 6px solid #CC0000; }
.aru { display: flex; flex-direction: column-reverse; align-items: center; }
.aru .ln { width: 1.5px; height: 18px; background: #1A5CB0; }
.aru .hd { width: 0; height: 0; border-left: 4px solid transparent; border-right: 4px solid transparent; border-bottom: 6px solid #1A5CB0; }
.bot-arr { display: flex; flex-direction: column; align-items: center; padding-top: 5px; gap: 2px; }
.ardb { display: flex; flex-direction: column; align-items: center; }
.ardb .ln { width: 1.5px; height: 16px; background: #1A5CB0; }
.ardb .hd { width: 0; height: 0; border-left: 4px solid transparent; border-right: 4px solid transparent; border-top: 6px solid #1A5CB0; }
.agent-box { border-radius: 8px; padding: 10px; background: #fff; border: 1.5px dashed #1A5CB0; flex: 1; }
.ah { display: flex; align-items: center; gap: 7px; margin-bottom: 9px; }
.an { width: 20px; height: 20px; border-radius: 50%; background: #1A5CB0; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 700; color: #fff; flex-shrink: 0; }
.aname { font-size: 11px; font-weight: 700; color: #2C2C2A; }
.bl { display: flex; flex-direction: column; gap: 6px; }
.b { border-radius: 6px; padding: 6px 8px 5px; border: 0.5px solid #D3D1C7; background: #F5F4F1; text-align: center; }
.b.hf { background: #FAEEDA; border: 0.5px dashed #BA7517; }
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
.hr-box { border-radius: 7px; padding: 9px 8px; border: 0.5px solid #D3D1C7; background: #F5F4F1; text-align: center; }
.hr-m { font-size: 9px; font-weight: 600; color: #2C2C2A; margin-bottom: 3px; }
.hr-s { font-size: 8px; color: #888780; }
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
    return level != "Full-Auto"


def export_workflow_html(workflow: dict) -> str:
    """Workflow 결과를 PwC 표준 AI Service Flow HTML로 변환합니다."""
    process_name = workflow.get("process_name", "AI Workflow")
    agents = workflow.get("agents", [])
    summary = workflow.get("blueprint_summary", "")

    # Input 수집 (모든 에이전트의 input_data에서)
    all_inputs: list[str] = []
    seen_inputs: set[str] = set()
    for agent in agents:
        for task in agent.get("assigned_tasks", []):
            for inp in task.get("input_data", []):
                if inp and inp not in seen_inputs:
                    seen_inputs.add(inp)
                    all_inputs.append(inp)

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

    # Input 행
    input_boxes = ""
    for inp in all_inputs[:6]:
        input_boxes += f'<div class="ibox"><div class="ibox-t">{inp}</div></div>\n'

    # Senior AI 행
    agent_names = [a.get("agent_name", f"Agent {i+1}") for i, a in enumerate(agents)]
    orchestrator_desc = ""
    for i, name in enumerate(agent_names):
        orchestrator_desc += f"Agent {i+1} "
    orchestrator_desc = f"({orchestrator_desc.strip()} 기동 → 결과 수령 → HR 담당자 전달)"

    # Junior AI 행 — 커넥터 + 에이전트 박스
    connectors_html = ""
    agents_html = ""

    for i, agent in enumerate(agents):
        # 커넥터
        connectors_html += f"""
        <div class="conn">
          <div class="cs">
            <span class="lbl-r">{'①②③④⑤⑥⑦'[i]} {agent.get('agent_name', '')}<br>지시</span>
            <div class="ard"><div class="ln"></div><div class="hd"></div></div>
          </div>
          <div class="cs">
            <div class="aru"><div class="ln"></div><div class="hd"></div></div>
            <span class="lbl-b">결과 반환</span>
          </div>
        </div>"""

        # 에이전트 박스
        tasks_html = ""
        has_human_task = False
        for task in agent.get("assigned_tasks", []):
            is_human = _has_human(task)
            if is_human:
                has_human_task = True
            hf_cls = ' hf' if is_human else ''
            technique = agent.get("ai_technique", "")
            badges = _badge_html(technique)
            if is_human:
                badges += ' <span class="badge bh">Human 확인</span>'

            tasks_html += f"""
                <div class="b{hf_cls}">
                  <div class="bt">{task.get('task_id', '')} {task.get('task_name', '')}</div>
                  <div class="bs">{task.get('ai_role', '')}</div>
                  <div class="bbr">{badges}</div>
                </div>"""

        arrow_html = ""
        if has_human_task:
            arrow_html = f"""
            <div class="bot-arr">
              <span style="font-size:7.5px;color:#1A5CB0;font-weight:600;">{agent.get('agent_name', '')} 결과 HR 담당자 확인</span>
              <div class="ardb"><div class="ln"></div><div class="hd"></div></div>
            </div>"""

        agents_html += f"""
          <div class="agent-col">
            <div class="agent-box">
              <div class="ah"><div class="an">{i+1}</div><div class="aname">{agent.get('agent_name', '')}</div></div>
              <div class="bl">{tasks_html}
              </div>
            </div>{arrow_html}
          </div>"""

    # HR 담당자 행
    hr_html = ""
    for i in range(agent_count):
        agent_humans = [h for h in human_tasks if h["agent_idx"] == i]
        if agent_humans:
            for h in agent_humans[:1]:  # 에이전트당 1개만
                hr_html += f"""
          <div class="hr-box">
            <div class="hr-m">{h['name']}</div>
            <div class="hr-s">{h['desc']}</div>
          </div>"""
        else:
            hr_html += "<div></div>"

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<title>AI Service Flow — {process_name}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="slide">
  <div class="title-row">
    <div class="legend">
      <div class="leg-btn leg-senior">Senior AI</div>
      <div class="leg-btn leg-junior">Junior AI</div>
      <div class="leg-btn leg-human">사람</div>
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
      <div class="row-label"><div class="row-icon">🤖</div><div class="row-name name-junior">Junior<br>AI</div></div>
      <div class="row-content">
        <div class="agents-grid" style="grid-template-columns: {grid_cols};">
          {connectors_html}
        </div>
        <div class="agents-grid" style="grid-template-columns: {grid_cols}; margin-top: 4px;">
          {agents_html}
        </div>
      </div>
    </div>

    <!-- HR 담당자 -->
    <div class="row bg-human">
      <div class="row-label"><div class="row-icon">👤</div><div class="row-name name-human">HR<br>담당자</div></div>
      <div class="row-content">
        <div class="agents-grid" style="grid-template-columns: {grid_cols};">
          {hr_html}
        </div>
      </div>
    </div>

  </div>
</div>
</body>
</html>"""
