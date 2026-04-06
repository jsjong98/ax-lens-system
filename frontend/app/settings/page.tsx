"use client";

import { useEffect, useState } from "react";
import { getSettings, saveSettings, type ClassifierSettings } from "@/lib/api";
import { Save, CheckCircle2, AlertCircle, ChevronDown, ChevronUp } from "lucide-react";

// 내장 Knock-out 기준 (읽기 전용 표시용)
const BUILTIN_CRITERIA = [
  {
    stage: "1단계",
    criterion: "1단계: 규제 측면",
    category: "규제 측면",
    subtitle: "AI 기본법 · EU AI Act 법적 제약",
    badgeColor: "",
    badgeStyle: { background: "#EDE9FE", color: "#5B21B6" },
    items: [
      {
        icon: "🚫",
        title: "법적 금지",
        desc: "AI 활용 자체를 불허하는 영역",
        examples: "화상면접 감정 분석, CCTV 얼굴 DB 구축",
      },
      {
        icon: "👁",
        title: "법적 감독 의무 (고위험 AI)",
        desc: "채용·승진·성과 등 개인 권리에 영향을 미치는 고위험 영역에서 인간 최종 감독·확정 의무",
        examples: "최종 합격자 선정, 성과 등급 확정, 승진 대상자 확정",
      },
    ],
  },
  {
    stage: "2단계",
    criterion: "2단계: 확정/승인 업무",
    category: "확정/승인 업무",
    subtitle: "권리·금전·정책 관련 책임귀속성 업무",
    badgeColor: "",
    badgeStyle: { background: "#FEF3C7", color: "#92400E" },
    items: [
      {
        icon: "🏛",
        title: "조직 기준·제도 확정",
        desc: "조직·사업장·전사에 적용되는 기준·제도·정책을 확정",
        examples: "평가 제도 개편안 확정, 보상 정책 확정, 취업규칙 변경",
      },
      {
        icon: "⚠️",
        title: "고영향·비가역 의사결정",
        desc: "법적 분쟁·노사 갈등·평판 훼손 등 복구 비용이 현저히 큰 비가역적 확정",
        examples: "직장 내 괴롭힘 조치 확정, 차별 이슈 결론 확정, 징계 확정",
      },
    ],
  },
  {
    stage: "3단계",
    criterion: "3단계: 상호작용 업무",
    category: "상호작용 업무",
    subtitle: "관계·맥락·윤리·변화 관련 대인 업무",
    badgeColor: "",
    badgeStyle: { background: "#F2DCE0", color: "#A62121" },
    items: [
      {
        icon: "💚",
        title: "공감·심리안전",
        desc: "개인의 심리적 안정 회복을 위한 공감 기반 대인 상호작용",
        examples: "복직 면담, 퇴직 면담, 육아휴직 복직자 면담",
      },
      {
        icon: "🤝",
        title: "협상·중재",
        desc: "상충하는 이해관계의 현장 협상 및 중재",
        examples: "노사 교섭, 처우 협의, 고용조건 협의",
      },
      {
        icon: "⚖️",
        title: "공정성 설득",
        desc: "결정의 정당성을 설명하고 상대의 감정을 조율하여 수용 유도",
        examples: "평가등급 조정 이슈 대응, 승진 누락 이의제기 대응",
      },
      {
        icon: "🌱",
        title: "변화/리더십 정착",
        desc: "비전을 제시하고 정당성을 부여하여 조직 행동 변화 촉진",
        examples: "제도 런칭 설명회, 리더 코칭, 문화 내재화 활동",
      },
      {
        icon: "✨",
        title: "창의적 설계",
        desc: "정해진 규칙이 없는 상황에서 새 제도·구조를 집단 창작",
        examples: "직무/조직/제도 설계 워크숍, 신규 복리후생 기획",
      },
    ],
  },
];

export default function SettingsPage() {
  const [form, setForm]           = useState<ClassifierSettings>({
    criteria_prompt: "",
    api_key: "",
    model: "gpt-5.4",
    anthropic_api_key: "",
    anthropic_model: "claude-sonnet-4-6",
    batch_size: 1,
    temperature: 0.0,
  });
  const [saving, setSaving]       = useState(false);
  const [saved, setSaved]         = useState(false);
  const [error, setError]         = useState("");
  const [showBuiltin, setShowBuiltin] = useState(true);
  useEffect(() => {
    getSettings().then(setForm).catch(() => {});
  }, []);

  const handleSave = async () => {
    setSaving(true); setError(""); setSaved(false);
    try {
      const updated = await saveSettings(form);
      setForm(updated);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const set = <K extends keyof ClassifierSettings>(k: K, v: ClassifierSettings[K]) =>
    setForm((prev) => ({ ...prev, [k]: v }));

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">설정</h1>
        <p className="mt-1 text-sm text-gray-500">분류 기준과 API 설정을 관리합니다.</p>
      </div>

      {/* 내장 Knock-out 기준 (읽기 전용) */}
      <section className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
        <button
          onClick={() => setShowBuiltin((v) => !v)}
          className="flex w-full items-center justify-between px-6 py-4 hover:bg-gray-50 transition-colors"
        >
          <div className="flex items-center gap-3">
            <span className="text-base font-semibold text-gray-900">내장 Knock-out 분류 기준</span>
            <span className="rounded-full px-2 py-0.5 text-xs font-medium" style={{ background: "#FFF5F7", color: "#A62121" }}>
              9개 기준 · 3단계 cascade
            </span>
          </div>
          {showBuiltin ? <ChevronUp className="h-4 w-4 text-gray-400" /> : <ChevronDown className="h-4 w-4 text-gray-400" />}
        </button>

        {showBuiltin && (
          <div className="border-t border-gray-100 px-6 pb-6 pt-4 space-y-6">
            {/* 범례 */}
            <div className="flex flex-wrap gap-3 text-xs">
              <div className="flex items-center gap-1.5">
                <span className="h-3 w-3 rounded-full bg-red-500" />
                <span className="text-gray-600">AI (빨간색)</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="h-3 w-3 rounded-full bg-emerald-500" />
                <span className="text-gray-600">Human (초록색)</span>
              </div>
              <div className="ml-4 text-gray-400">
                → 앞 단계에서 해당하면 즉시 "Human" 확정
              </div>
            </div>

            {/* 단계별 기준 */}
            {BUILTIN_CRITERIA.map((stage) => (
              <div key={stage.stage}>
                {/* 단계 헤더 */}
                <div className="flex items-center gap-2 mb-3">
                  <span className="rounded bg-gray-800 px-2 py-0.5 text-xs font-bold text-white">
                    {stage.stage}
                  </span>
                  <span className="font-semibold text-gray-800">{stage.category}</span>
                  <span className="rounded-full px-2 py-0.5 text-xs font-medium" style={stage.badgeStyle}>
                    {stage.subtitle}
                  </span>
                  {/* criterion 태그 (출력 시 실제 사용되는 값) */}
                  <code className="ml-auto rounded px-2 py-0.5 text-[10px]" style={{ background: "#FFF5F7", color: "#A62121", border: "1px solid #F2A0AF" }}>
                    criterion: &quot;{stage.criterion}&quot;
                  </code>
                </div>
                {/* 세부 기준 목록 */}
                <div className="space-y-1.5 pl-2">
                  {stage.items.map((item) => (
                    <div key={item.title} className="rounded-lg border border-gray-100 bg-gray-50 px-4 py-3">
                      <p className="text-sm font-medium text-gray-800">
                        {item.icon} {item.title}
                      </p>
                      <p className="mt-0.5 text-xs text-gray-500">{item.desc}</p>
                      <p className="mt-1 text-xs text-gray-400">예: {item.examples}</p>
                    </div>
                  ))}
                </div>
              </div>
            ))}

            <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-xs text-emerald-800">
              <span className="font-semibold">통과 (AI)</span>: 위 9개 기준 모두 해당 없으면 →
              자동화 가능한 규칙 기반 업무로 분류
            </div>
          </div>
        )}
      </section>

      {/* 추가 기준 */}
      <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm space-y-4">
        <div>
          <h2 className="text-base font-semibold text-gray-900">추가 분류 기준 (선택)</h2>
          <p className="text-xs text-gray-500 mt-0.5">
            내장 기준 외에 프로젝트 맞춤 기준을 추가할 수 있습니다.
            비워두면 내장 기준만 적용됩니다.
          </p>
        </div>
        <textarea
          value={form.criteria_prompt}
          onChange={(e) => set("criteria_prompt", e.target.value)}
          rows={8}
          placeholder={"예시:\n- 추가 기준: 그룹 공동 인사 발령 시 최종 확정은 인간 수행\n- 특정 업무 예외: ..."}
          className="w-full rounded-lg border border-gray-300 px-4 py-3 text-sm font-mono leading-relaxed focus:outline-none resize-y"
          onFocus={(e) => { e.currentTarget.style.borderColor = "#A62121"; e.currentTarget.style.boxShadow = "0 0 0 1px #A62121"; }}
          onBlur={(e) => { e.currentTarget.style.borderColor = ""; e.currentTarget.style.boxShadow = ""; }}
        />
      </section>

      {/* API 설정 */}
      <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm space-y-6">
        <div>
          <h2 className="text-base font-semibold text-gray-900">API 설정</h2>
          <p className="text-xs text-gray-500 mt-0.5">두 API를 모두 설정하면 분류 실행 시 제공자를 선택할 수 있습니다.</p>
        </div>

        {/* O 모델 */}
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <span className="rounded px-2 py-0.5 text-xs font-bold text-white" style={{ backgroundColor: "#10a37f" }}>O 모델</span>
            <span className="text-sm font-medium text-gray-700">API Key</span>
          </div>
          <div className="space-y-1.5">
            <label className="block text-xs font-medium text-gray-600">API Key</label>
            <input
              type="password"
              value={form.api_key}
              onChange={(e) => set("api_key", e.target.value)}
              placeholder="sk-..."
              className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm font-mono focus:outline-none"
              onFocus={(e) => { e.currentTarget.style.borderColor = "#10a37f"; e.currentTarget.style.boxShadow = "0 0 0 1px #10a37f"; }}
              onBlur={(e) => { e.currentTarget.style.borderColor = ""; e.currentTarget.style.boxShadow = ""; }}
            />
            <p className="text-xs text-gray-400">또는 <code className="bg-gray-100 rounded px-1">backend/.env</code>에 O 모델 API Key를 설정</p>
          </div>
        </div>

        <div className="border-t border-gray-100" />

        {/* A 모델 */}
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <span className="rounded px-2 py-0.5 text-xs font-bold text-white" style={{ backgroundColor: "#c96442" }}>A 모델</span>
            <span className="text-sm font-medium text-gray-700">API Key</span>
          </div>
          <div className="space-y-1.5">
            <label className="block text-xs font-medium text-gray-600">API Key</label>
            <input
              type="password"
              value={form.anthropic_api_key}
              onChange={(e) => set("anthropic_api_key", e.target.value)}
              placeholder="sk-ant-..."
              className="w-full rounded-lg border border-gray-300 px-4 py-2.5 text-sm font-mono focus:outline-none"
              onFocus={(e) => { e.currentTarget.style.borderColor = "#c96442"; e.currentTarget.style.boxShadow = "0 0 0 1px #c96442"; }}
              onBlur={(e) => { e.currentTarget.style.borderColor = ""; e.currentTarget.style.boxShadow = ""; }}
            />
            <p className="text-xs text-gray-400">또는 <code className="bg-gray-100 rounded px-1">backend/.env</code>에 A 모델 API Key를 설정</p>
          </div>
        </div>

      </section>

      {/* 분석 설정 */}
      <section className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm space-y-5">
        <div>
          <h2 className="text-base font-semibold text-gray-900">분석 설정</h2>
        </div>

        <div className="space-y-1.5">
          <label className="block text-sm font-medium text-gray-700">
            배치 크기 <span className="text-gray-400 font-normal">— 한 번에 분류할 Task 수 ({form.batch_size}개)</span>
          </label>
          <input type="range" min={1} max={20} step={1} value={form.batch_size}
            onChange={(e) => set("batch_size", Number(e.target.value))}
            className="w-full" style={{ accentColor: "#A62121" }} />
          <div className="flex justify-between text-xs text-gray-400">
            <span>1개 (안정적)</span><span>20개 (빠름)</span>
          </div>
        </div>
      </section>

      {/* 저장 */}
      <div className="flex items-center gap-3">
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 rounded-lg px-5 py-2.5 text-sm font-medium text-white shadow-sm disabled:opacity-50 transition-colors"
          style={{ backgroundColor: "#A62121" }}
          onMouseEnter={(e) => { if (!saving) (e.currentTarget as HTMLElement).style.backgroundColor = "#8A1B1B"; }}
          onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.backgroundColor = "#A62121"; }}
        >
          <Save className="h-4 w-4" />
          {saving ? "저장 중..." : "설정 저장"}
        </button>
        {saved && (
          <div className="flex items-center gap-1.5 text-sm text-emerald-600">
            <CheckCircle2 className="h-4 w-4" />저장되었습니다.
          </div>
        )}
        {error && (
          <div className="flex items-center gap-1.5 text-sm text-red-600">
            <AlertCircle className="h-4 w-4" />{error}
          </div>
        )}
      </div>

      <section className="rounded-xl border border-gray-100 bg-gray-50 p-5 text-xs text-gray-600 space-y-1">
        <p className="font-semibold text-gray-700">참고: backend/.env 파일 설정 예시</p>
        <p>• O 모델: <code className="bg-gray-200 rounded px-1">OPENAI_API_KEY=sk-...</code></p>
        <p>• A 모델: <code className="bg-gray-200 rounded px-1">ANTHROPIC_API_KEY=sk-ant-...</code></p>
        <p className="text-gray-400">앱 시작 시 자동으로 로드됩니다. 위 필드에 직접 입력해도 동일하게 동작합니다.</p>
      </section>
    </div>
  );
}
