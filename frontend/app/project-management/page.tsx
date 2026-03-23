"use client";

import { useState, useEffect, useCallback } from "react";
import {
  generateProjectDefinition,
  getProjectDefinition,
  generateProjectDesign,
  getProjectDesign,
  getFilterOptions,
  downloadProjectPpt,
  type ProjectDefinitionResult,
  type ProjectDesignResult,
  type ProviderType,
  type FilterOptions,
} from "@/lib/api";

/* ── 색상 ─────────────────────────────────────────────────── */
const PWC = {
  primary: "#A62121",
  primaryLight: "#D95578",
  bg: "#FFF5F7",
};

/* ── Actor별 색상 ─────────────────────────────────────────── */
const ACTOR_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  "Input":       { bg: "#F3F4F6", border: "#D1D5DB", text: "#374151" },
  "Senior AI":   { bg: "#FEF2F2", border: "#A62121", text: "#A62121" },
  "Junior AI":   { bg: "#FFFBEB", border: "#D97706", text: "#92400E" },
  "HR 담당자":   { bg: "#F0F9FF", border: "#0284C7", text: "#0C4A6E" },
};

type TabType = "definition" | "design";

export default function ProjectManagementPage() {
  const [activeTab, setActiveTab] = useState<TabType>("definition");

  // 공통 설정
  const [provider, setProvider] = useState<ProviderType>("openai");
  const [processName, setProcessName] = useState("");
  const [author, setAuthor] = useState("");
  const [filters, setFilters] = useState<FilterOptions | null>(null);
  const [selectedL3, setSelectedL3] = useState("");
  const [selectedL4, setSelectedL4] = useState("");

  // 과제 정의서
  const [defResult, setDefResult] = useState<ProjectDefinitionResult | null>(null);
  const [defLoading, setDefLoading] = useState(false);
  const [defError, setDefError] = useState<string | null>(null);

  // 과제 설계서
  const [designResult, setDesignResult] = useState<ProjectDesignResult | null>(null);
  const [designLoading, setDesignLoading] = useState(false);
  const [designError, setDesignError] = useState<string | null>(null);

  // 초기 로드
  useEffect(() => {
    getFilterOptions().then(setFilters).catch(() => {});
    getProjectDefinition().then(setDefResult).catch(() => {});
    getProjectDesign().then(setDesignResult).catch(() => {});
  }, []);

  /* ── 과제 정의서 생성 ─────────────────────────────────────── */
  const handleGenerateDefinition = useCallback(async () => {
    setDefLoading(true);
    setDefError(null);
    try {
      const res = await generateProjectDefinition({
        provider,
        process_name: processName || undefined,
        author: author || undefined,
        l3: selectedL3 || undefined,
        l4: selectedL4 || undefined,
      });
      setDefResult(res);
    } catch (e: unknown) {
      setDefError(e instanceof Error ? e.message : "생성 실패");
    } finally {
      setDefLoading(false);
    }
  }, [provider, processName, author, selectedL3, selectedL4]);

  /* ── 과제 설계서 생성 ─────────────────────────────────────── */
  const handleGenerateDesign = useCallback(async () => {
    setDesignLoading(true);
    setDesignError(null);
    try {
      const res = await generateProjectDesign({
        provider,
        process_name: processName || undefined,
        l3: selectedL3 || undefined,
        l4: selectedL4 || undefined,
      });
      setDesignResult(res);
    } catch (e: unknown) {
      setDesignError(e instanceof Error ? e.message : "생성 실패");
    } finally {
      setDesignLoading(false);
    }
  }, [provider, processName, selectedL3, selectedL4]);

  const loading = activeTab === "definition" ? defLoading : designLoading;
  const error = activeTab === "definition" ? defError : designError;
  const handleGenerate = activeTab === "definition" ? handleGenerateDefinition : handleGenerateDesign;

  return (
    <div className="space-y-6">
      {/* 헤더 */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Project Management</h1>
        <p className="mt-1 text-sm text-gray-500">
          분류 결과와 To-Be Workflow를 기반으로 과제 정의서 / 설계서를 자동 생성합니다.
        </p>
      </div>

      {/* 탭 */}
      <div className="flex gap-1 border-b">
        {[
          { key: "definition" as TabType, label: "과제 정의서" },
          { key: "design" as TabType, label: "과제 설계서" },
        ].map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`px-5 py-2.5 text-sm font-semibold border-b-2 transition-colors ${
              activeTab === key
                ? "border-red-700 text-red-700"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
            style={activeTab === key ? { borderColor: PWC.primary, color: PWC.primary } : undefined}
          >
            {label}
          </button>
        ))}
      </div>

      {/* 설정 패널 */}
      <div className="rounded-xl border bg-white p-6 shadow-sm space-y-4">
        <h2 className="text-lg font-semibold text-gray-800">생성 설정</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">분류 결과 Provider</label>
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value as ProviderType)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-red-400 focus:ring-1 focus:ring-red-400 outline-none"
            >
              <option value="openai">OpenAI</option>
              <option value="anthropic">Anthropic</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">프로세스명 (선택)</label>
            <input
              type="text"
              value={processName}
              onChange={(e) => setProcessName(e.target.value)}
              placeholder="비우면 자동 추론"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-red-400 focus:ring-1 focus:ring-red-400 outline-none"
            />
          </div>

          {activeTab === "definition" && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">작성자 (선택)</label>
              <input
                type="text"
                value={author}
                onChange={(e) => setAuthor(e.target.value)}
                placeholder="예: PwC 홍길동"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-red-400 focus:ring-1 focus:ring-red-400 outline-none"
              />
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">L3 필터 (선택)</label>
            <select
              value={selectedL3}
              onChange={(e) => setSelectedL3(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-red-400 focus:ring-1 focus:ring-red-400 outline-none"
            >
              <option value="">전체</option>
              {filters?.l3.map((item) => (
                <option key={item.id} value={item.name}>{item.name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">L4 필터 (선택)</label>
            <select
              value={selectedL4}
              onChange={(e) => setSelectedL4(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-red-400 focus:ring-1 focus:ring-red-400 outline-none"
            >
              <option value="">전체</option>
              {filters?.l4.map((item) => (
                <option key={item.id} value={item.name}>{item.name}</option>
              ))}
            </select>
          </div>
        </div>

        {/* 생성 버튼 */}
        <div className="flex items-center gap-3 pt-2">
          <button
            onClick={handleGenerate}
            disabled={loading}
            className="rounded-lg px-6 py-2.5 text-sm font-semibold text-white shadow-sm transition-all disabled:opacity-50"
            style={{ backgroundColor: PWC.primary }}
          >
            {loading ? (
              <span className="flex items-center gap-2">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                생성 중...
              </span>
            ) : activeTab === "definition" ? "과제 정의서 생성" : "과제 설계서 생성"}
          </button>

          {/* PPT 다운로드 버튼 */}
          {(defResult || designResult) && (
            <button
              onClick={async () => {
                try { await downloadProjectPpt(); }
                catch (e: unknown) { alert(e instanceof Error ? e.message : "PPT 다운로드 실패"); }
              }}
              className="rounded-lg px-5 py-2.5 text-sm font-semibold border shadow-sm transition-all hover:bg-gray-50"
              style={{ borderColor: PWC.primary, color: PWC.primary }}
            >
              PPT 다운로드
            </button>
          )}

          {error && <span className="text-sm text-red-600">{error}</span>}
        </div>
      </div>

      {/* ── 과제 정의서 결과 ──────────────────────────────────── */}
      {activeTab === "definition" && defResult && (
        <div className="rounded-xl border bg-white shadow-sm overflow-hidden">
          <div className="px-6 py-4" style={{ backgroundColor: PWC.primary }}>
            <h2 className="text-xl font-bold text-white">
              {defResult.project_number ? `${defResult.project_number}. ` : ""}
              {defResult.project_title}
            </h2>
            <div className="mt-1 flex gap-4 text-sm text-red-200">
              {defResult.created_date && <span>작성일: {defResult.created_date}</span>}
              {defResult.author && <span>작성자: {defResult.author}</span>}
            </div>
          </div>

          <Section number="1" title="과제 개요 (주요 과제 내용)">
            <ul className="space-y-2">
              {defResult.overview.map((item, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                  <span className="mt-1 text-gray-400">-</span>
                  {item}
                </li>
              ))}
            </ul>
          </Section>

          <Section number="2" title="매핑 프로세스 (To-Be 기준)">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b" style={{ backgroundColor: PWC.bg }}>
                  <th className="px-4 py-2 text-left font-semibold text-gray-700 w-28">No.</th>
                  <th className="px-4 py-2 text-left font-semibold text-gray-700">프로세스</th>
                </tr>
              </thead>
              <tbody>
                {defResult.mapping_processes.map((mp, i) => (
                  <tr key={i} className="border-b last:border-b-0 hover:bg-gray-50">
                    <td className="px-4 py-2 text-gray-600 font-mono align-top">{mp.no}</td>
                    <td className="px-4 py-2 text-gray-800">
                      <div>{mp.process_name}</div>
                      {mp.task_range && <div className="text-xs text-gray-500 mt-0.5">{mp.task_range}</div>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Section>

          <Section number="3" title="이해관계자">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <InfoCard label="과제 오너(이름)" value={defResult.stakeholder.project_owner} />
              <InfoCard label="주관 부서" value={defResult.stakeholder.owner_department} />
              <InfoCard label="협업 부서"
                value={defResult.stakeholder.collaborating_departments.length > 0
                  ? defResult.stakeholder.collaborating_departments.join(", ") : "없음"} />
              <InfoCard label="외부 파트너"
                value={defResult.stakeholder.external_partners.length > 0
                  ? defResult.stakeholder.external_partners.join(", ") : "없음"} />
            </div>
          </Section>

          <Section number="4" title="현황 및 문제점 vs. 개선 방향">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div>
                <h4 className="text-sm font-semibold text-red-700 mb-3 flex items-center gap-1.5">
                  <span className="inline-block w-2 h-2 rounded-full bg-red-500" />
                  현황 및 문제점
                </h4>
                <ul className="space-y-2">
                  {defResult.current_vs_improvement.current_issues.map((issue, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                      <span className="mt-0.5 text-red-400 flex-shrink-0">&rarr;</span>
                      {issue}
                    </li>
                  ))}
                </ul>
              </div>
              <div>
                <h4 className="text-sm font-semibold text-green-700 mb-3 flex items-center gap-1.5">
                  <span className="inline-block w-2 h-2 rounded-full bg-green-500" />
                  개선 방향
                </h4>
                <ul className="space-y-2">
                  {defResult.current_vs_improvement.improvement_directions.map((dir, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                      <span className="mt-0.5 text-green-400 flex-shrink-0">&rarr;</span>
                      {dir}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </Section>

          <Section number="5" title="기대 효과">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="rounded-lg border p-4" style={{ backgroundColor: "#F0F9FF" }}>
                <h4 className="text-sm font-semibold text-blue-700 mb-3">정량적 효과</h4>
                <ul className="space-y-2">
                  {defResult.expected_effects.quantitative.map((eff, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                      <span className="mt-0.5 text-blue-500 font-bold flex-shrink-0">-</span>
                      {eff}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="rounded-lg border p-4" style={{ backgroundColor: "#F5F3FF" }}>
                <h4 className="text-sm font-semibold text-purple-700 mb-3">정성적 효과</h4>
                <ul className="space-y-2">
                  {defResult.expected_effects.qualitative.map((eff, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                      <span className="mt-0.5 text-purple-500 font-bold flex-shrink-0">-</span>
                      {eff}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </Section>

          <Section number="6" title="과제 추진 시 고려사항">
            <ul className="space-y-2">
              {defResult.considerations.map((item, i) => (
                <li key={i} className="flex items-start gap-3 text-sm text-gray-700">
                  <span className="mt-0.5 text-gray-400 flex-shrink-0">-</span>
                  {item}
                </li>
              ))}
            </ul>
          </Section>
        </div>
      )}

      {/* ── 과제 설계서 결과 ──────────────────────────────────── */}
      {activeTab === "design" && designResult && (
        <div className="space-y-6">
          {/* 7. AI Service Flow */}
          <div className="rounded-xl border bg-white shadow-sm overflow-hidden">
            <div className="px-6 py-4" style={{ backgroundColor: PWC.primary }}>
              <h2 className="text-xl font-bold text-white">{designResult.project_title}</h2>
            </div>

            <Section number="7" title="AI Service Flow">
              {/* 수행 주체 범례 */}
              <div className="flex gap-3 mb-5 text-xs">
                <span className="text-gray-500">수행 주체 :</span>
                {Object.entries(ACTOR_COLORS).map(([actor, colors]) => (
                  <span key={actor} className="px-2 py-0.5 rounded font-semibold"
                    style={{ backgroundColor: colors.bg, border: `1px solid ${colors.border}`, color: colors.text }}>
                    {actor}
                  </span>
                ))}
              </div>

              {/* Input 데이터 */}
              {designResult.ai_service_flow.inputs.length > 0 && (
                <div className="mb-5">
                  <div className="text-xs font-semibold text-gray-500 mb-2">Input 데이터</div>
                  <div className="flex flex-wrap gap-2">
                    {designResult.ai_service_flow.inputs.map((inp, i) => (
                      <span key={i} className="px-3 py-1.5 rounded-lg border text-sm"
                        style={{ backgroundColor: ACTOR_COLORS["Input"].bg, borderColor: ACTOR_COLORS["Input"].border }}>
                        {inp}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Flow Steps */}
              <div className="space-y-3">
                {designResult.ai_service_flow.steps.map((step, i) => {
                  const colors = ACTOR_COLORS[step.actor] || ACTOR_COLORS["Input"];
                  return (
                    <div key={i} className="flex items-start gap-3">
                      {/* 순서 번호 */}
                      <div className="flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-white"
                        style={{ backgroundColor: PWC.primary }}>
                        {step.step_order}
                      </div>
                      {/* 카드 */}
                      <div className="flex-1 rounded-lg border p-3"
                        style={{ backgroundColor: colors.bg, borderColor: colors.border }}>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="px-2 py-0.5 rounded text-xs font-bold"
                            style={{ backgroundColor: colors.border, color: "white" }}>
                            {step.actor}
                          </span>
                          <span className="text-sm font-semibold" style={{ color: colors.text }}>
                            {step.step_name}
                          </span>
                        </div>
                        {step.description && (
                          <p className="text-xs text-gray-600 mt-1">{step.description}</p>
                        )}
                        {step.sub_steps.length > 0 && (
                          <div className="flex flex-wrap gap-1.5 mt-2">
                            {step.sub_steps.map((sub, j) => (
                              <span key={j} className="px-2 py-0.5 bg-white rounded border text-xs text-gray-600">
                                {sub}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </Section>

            {/* 8. AI 기술 유형 */}
            <Section number="8" title="AI 기술 유형">
              <div className="space-y-4">
                {designResult.ai_tech_info.tech_types.map((tt, i) => (
                  <div key={i}>
                    <div className="text-sm font-semibold text-gray-700 mb-2">
                      {i + 1}) {tt.category}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {tt.sub_types.map((st, j) => {
                        const isChecked = tt.checked.includes(st);
                        return (
                          <span key={j}
                            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-sm ${
                              isChecked
                                ? "bg-red-50 border-red-300 text-red-800 font-semibold"
                                : "bg-gray-50 border-gray-200 text-gray-400"
                            }`}
                          >
                            <span className={`inline-block w-4 h-4 rounded border text-center leading-4 text-xs ${
                              isChecked
                                ? "bg-red-600 border-red-600 text-white"
                                : "bg-white border-gray-300"
                            }`}>
                              {isChecked ? "\u2713" : ""}
                            </span>
                            {st}
                          </span>
                        );
                      })}
                    </div>
                  </div>
                ))}

                {/* 기술 이름 */}
                {designResult.ai_tech_info.tech_names.length > 0 && (
                  <div className="mt-4 pt-4 border-t">
                    <div className="text-sm font-semibold text-gray-700 mb-2">[ 기술 이름 ]</div>
                    <ul className="space-y-1">
                      {designResult.ai_tech_info.tech_names.map((name, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
                          <span className="mt-0.5 text-gray-400">&#8226;</span>
                          {name}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </Section>

            {/* 9. Input / Output */}
            <Section number="9" title="Input / Output">
              <div className="space-y-4">
                {/* Input 테이블 */}
                <table className="w-full text-sm border">
                  <tbody>
                    <tr className="border-b">
                      <td rowSpan={2} className="px-4 py-3 font-semibold text-gray-700 w-24 border-r align-middle"
                        style={{ backgroundColor: PWC.bg }}>
                        Input
                      </td>
                      <td className="px-4 py-2 font-semibold text-gray-600 w-16 border-r"
                        style={{ backgroundColor: "#F9FAFB" }}>
                        내부
                      </td>
                      <td className="px-4 py-2 text-gray-700">
                        <ul className="space-y-1">
                          {designResult.input_output.input_internal.map((item, i) => (
                            <li key={i} className="flex items-start gap-1.5">
                              <span className="mt-0.5 text-gray-400">&#8226;</span>{item}
                            </li>
                          ))}
                        </ul>
                      </td>
                    </tr>
                    <tr className="border-b">
                      <td className="px-4 py-2 font-semibold text-gray-600 border-r"
                        style={{ backgroundColor: "#F9FAFB" }}>
                        외부
                      </td>
                      <td className="px-4 py-2 text-gray-700">
                        <ul className="space-y-1">
                          {designResult.input_output.input_external.map((item, i) => (
                            <li key={i} className="flex items-start gap-1.5">
                              <span className="mt-0.5 text-gray-400">&#8226;</span>{item}
                            </li>
                          ))}
                        </ul>
                      </td>
                    </tr>
                    <tr>
                      <td className="px-4 py-3 font-semibold text-gray-700 border-r"
                        style={{ backgroundColor: PWC.bg }}>
                        Output
                      </td>
                      <td colSpan={2} className="px-4 py-2 text-gray-700">
                        <ul className="space-y-1">
                          {designResult.input_output.output.map((item, i) => (
                            <li key={i} className="flex items-start gap-1.5">
                              <span className="mt-0.5 text-gray-400">&#8226;</span>{item}
                            </li>
                          ))}
                        </ul>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </Section>

            {/* 별첨: Agent 정의서 */}
            {designResult.agent_definitions.length > 0 && (
              <Section number="+" title="별첨: Agent 정의서">
                <p className="text-xs text-gray-500 mb-4">AGENT 별로 1장씩 생성</p>
                <div className="space-y-8">
                  {designResult.agent_definitions.map((agent, i) => {
                    const colors = ACTOR_COLORS[agent.agent_type] || ACTOR_COLORS["Junior AI"];
                    return (
                      <div key={i} className="rounded-xl border-2 overflow-hidden" style={{ borderColor: colors.border }}>
                        {/* Agent 헤더 */}
                        <div className="px-5 py-3 flex items-center justify-between"
                          style={{ backgroundColor: colors.bg }}>
                          <div className="flex items-center gap-2">
                            <span className="px-2 py-0.5 rounded text-xs font-bold text-white"
                              style={{ backgroundColor: colors.border }}>
                              {agent.agent_type}
                            </span>
                            <span className="text-base font-bold" style={{ color: colors.text }}>
                              {agent.agent_name}
                            </span>
                          </div>
                        </div>

                        <div className="p-5 space-y-5">
                          {/* 1. Agent 개요 */}
                          <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                            <div>
                              <h4 className="text-sm font-bold text-gray-800 mb-3 flex items-center gap-2">
                                <span className="w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold text-white"
                                  style={{ backgroundColor: PWC.primary }}>1</span>
                                Agent 개요
                              </h4>
                              <div className="space-y-3">
                                <div className="flex gap-2 text-sm">
                                  <span className="text-gray-500 flex-shrink-0">Agent 명 :</span>
                                  <span className="font-semibold text-gray-800">{agent.agent_name}</span>
                                </div>
                                <div className="flex gap-2 text-sm">
                                  <span className="text-gray-500 flex-shrink-0">Agent 유형 :</span>
                                  <div className="flex items-center gap-1.5">
                                    <span className="w-3 h-3 rounded-full" style={{
                                      backgroundColor: agent.agent_type === "Senior AI" ? PWC.primary : "transparent",
                                      border: `2px solid ${colors.border}`,
                                    }} />
                                    <span className="font-semibold text-gray-800">{agent.agent_type}</span>
                                  </div>
                                </div>
                                <div>
                                  <div className="text-sm text-gray-500 mb-1.5">Agent 역할 :</div>
                                  <div className="rounded-lg border border-gray-200 p-3">
                                    <ul className="space-y-1.5">
                                      {agent.roles.map((role, j) => (
                                        <li key={j} className="flex items-start gap-2 text-sm text-gray-700">
                                          <span className="mt-0.5 text-gray-400 flex-shrink-0">&rarr;</span>
                                          {role}
                                        </li>
                                      ))}
                                    </ul>
                                  </div>
                                </div>
                              </div>
                            </div>

                            {/* 2. Service Flow 미니맵 */}
                            <div>
                              <h4 className="text-sm font-bold text-gray-800 mb-3 flex items-center gap-2">
                                <span className="w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold text-white"
                                  style={{ backgroundColor: PWC.primary }}>2</span>
                                Service Flow 미니맵
                              </h4>
                              <div className="rounded-lg border border-gray-200 p-3">
                                <div className="space-y-1.5">
                                  {designResult.ai_service_flow.steps.map((step, j) => {
                                    const isActive = agent.flow_step_orders.includes(step.step_order);
                                    const stepColors = ACTOR_COLORS[step.actor] || ACTOR_COLORS["Input"];
                                    return (
                                      <div key={j} className={`flex items-center gap-2 px-2 py-1 rounded text-xs ${
                                        isActive ? "ring-2 ring-offset-1" : "opacity-40"
                                      }`}
                                        style={{
                                          backgroundColor: isActive ? stepColors.bg : "#F9FAFB",
                                          ...(isActive ? { ringColor: stepColors.border } as React.CSSProperties : {}),
                                          border: isActive ? `1.5px solid ${stepColors.border}` : "1px solid #E5E7EB",
                                        }}>
                                        <span className="w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-bold text-white flex-shrink-0"
                                          style={{ backgroundColor: isActive ? stepColors.border : "#9CA3AF" }}>
                                          {step.step_order}
                                        </span>
                                        <span className={`font-medium ${isActive ? "" : "text-gray-400"}`}
                                          style={isActive ? { color: stepColors.text } : undefined}>
                                          {step.step_name}
                                        </span>
                                        <span className="ml-auto text-[10px] px-1.5 py-0.5 rounded"
                                          style={{ backgroundColor: isActive ? stepColors.border : "#D1D5DB", color: "white" }}>
                                          {step.actor}
                                        </span>
                                      </div>
                                    );
                                  })}
                                </div>
                              </div>
                            </div>
                          </div>

                          {/* 3. 처리 로직 */}
                          <div>
                            <h4 className="text-sm font-bold text-gray-800 mb-3 flex items-center gap-2">
                              <span className="w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold text-white"
                                style={{ backgroundColor: PWC.primary }}>3</span>
                              처리 로직
                            </h4>
                            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                              {/* Input */}
                              <div className="rounded-lg border p-4" style={{ backgroundColor: "#FFF7ED" }}>
                                <div className="text-xs font-bold text-orange-700 mb-2 flex items-center gap-1">
                                  <span className="w-1.5 h-4 rounded-sm" style={{ backgroundColor: "#EA580C" }} />
                                  Input
                                </div>
                                <ul className="space-y-1.5">
                                  {agent.input_data.map((item, j) => (
                                    <li key={j} className="flex items-start gap-1.5 text-xs text-gray-700">
                                      <span className="mt-0.5 text-orange-400 font-bold flex-shrink-0">&rarr;</span>
                                      {item}
                                    </li>
                                  ))}
                                </ul>
                              </div>

                              {/* 방법론 및 주요 기술 */}
                              <div className="rounded-lg border p-4" style={{ backgroundColor: PWC.bg }}>
                                <div className="text-xs font-bold mb-2 flex items-center gap-1" style={{ color: PWC.primary }}>
                                  <span className="w-1.5 h-4 rounded-sm" style={{ backgroundColor: PWC.primary }} />
                                  방법론 및 주요 기술
                                </div>
                                <div className="space-y-2.5">
                                  {agent.processing_steps.map((ps, j) => (
                                    <div key={j} className="text-xs">
                                      <div className="flex items-start gap-1.5">
                                        <span className="w-4 h-4 rounded-full flex items-center justify-center text-[10px] font-bold text-white flex-shrink-0 mt-0.5"
                                          style={{ backgroundColor: PWC.primary }}>
                                          {ps.step_number}
                                        </span>
                                        <div>
                                          <div className="font-semibold text-gray-800">{ps.step_name}</div>
                                          <div className="text-gray-500 mt-0.5">
                                            {ps.method} &rarr; {ps.result}
                                          </div>
                                        </div>
                                      </div>
                                    </div>
                                  ))}
                                </div>
                              </div>

                              {/* Output */}
                              <div className="rounded-lg border p-4" style={{ backgroundColor: "#F0FDF4" }}>
                                <div className="text-xs font-bold text-green-700 mb-2 flex items-center gap-1">
                                  <span className="w-1.5 h-4 rounded-sm bg-green-600" />
                                  Output
                                </div>
                                <ul className="space-y-1.5">
                                  {agent.output_data.map((item, j) => (
                                    <li key={j} className="flex items-start gap-1.5 text-xs text-gray-700">
                                      <span className="mt-0.5 text-green-400 font-bold flex-shrink-0">&rarr;</span>
                                      {item}
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </Section>
            )}
          </div>
        </div>
      )}
    </div>
  );
}


/* ── 공통 컴포넌트 ──────────────────────────────────────────── */

function Section({ number, title, children }: {
  number: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="px-6 py-5 border-b last:border-b-0">
      <h3 className="text-base font-semibold text-gray-800 mb-4">
        <span
          className="inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold text-white mr-2"
          style={{ backgroundColor: "#A62121" }}
        >
          {number}
        </span>
        {title}
      </h3>
      {children}
    </div>
  );
}

function InfoCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-gray-200 p-3">
      <div className="text-xs font-medium text-gray-500 mb-1">{label}</div>
      <div className="text-sm font-semibold text-gray-800">{value || "-"}</div>
    </div>
  );
}
