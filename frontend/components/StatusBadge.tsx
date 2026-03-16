import type { LabelType } from "@/lib/api";

interface Props {
  label: LabelType;
  size?: "sm" | "md";
}

type BadgeStyle = {
  bg: string; text: string; dotColor: string; borderColor: string; display: string;
};

const STYLES: Record<LabelType, BadgeStyle> = {
  "AI 수행 가능": {
    bg: "#FFF5F7",
    text: "#A62121",
    dotColor: "#A62121",
    borderColor: "#F2A0AF",
    display: "AI 수행 가능",
  },
  "AI + Human": {
    bg: "#FFF7ED",
    text: "#C2410C",
    dotColor: "#EA580C",
    borderColor: "#FDBA74",
    display: "AI + Human",
  },
  "인간 수행 필요": {
    bg: "#ECFDF5",
    text: "#065F46",
    dotColor: "#10B981",
    borderColor: "#A7F3D0",
    display: "인간 수행 필요",
  },
  미분류: {
    bg: "#F3F4F6",
    text: "#6B7280",
    dotColor: "#9CA3AF",
    borderColor: "#D1D5DB",
    display: "미분류",
  },
};

export default function StatusBadge({ label, size = "md" }: Props) {
  const s = STYLES[label] ?? STYLES["미분류"];
  const px = size === "sm" ? "px-2 py-0.5 text-xs" : "px-2.5 py-1 text-sm";

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border font-medium ${px}`}
      style={{ background: s.bg, color: s.text, borderColor: s.borderColor }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: s.dotColor }} />
      {s.display}
    </span>
  );
}
