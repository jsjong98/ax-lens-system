/**
 * Lane(수행주체) 기반 색상 팔레트.
 *
 * 노드의 data.role 에서 primary lane 이름을 꺼내 매핑.
 * "그 외:xxx" 커스텀 값은 lane 판정에서 제외.
 *
 * 모든 색상은 `#` 없는 6자리 hex — canvas 에선 `#${hex}` 형태로 조합, PPT 에선 그대로 사용.
 */

export interface LaneAccent {
  /** 본문 배경색 (hex without #) */
  bodyBg: string;
  /** 테두리 색 (hex without #) */
  border: string;
  /** 본문 글자색 (hex without #) — 배경 대비용 */
  text: string;
  /** 레전드/배지 등에 쓰는 강조색 (hex without #) */
  accent: string;
}

/** AI 오케스트레이션용 진한 블루 */
const SENIOR_AI: LaneAccent = { bodyBg: "649EE2", border: "3A7BC8", text: "000000", accent: "1E5A9E" };
/** AI 실행용 연한 블루 */
const JUNIOR_AI: LaneAccent = { bodyBg: "98BEEC", border: "649EE2", text: "000000", accent: "3A7BC8" };
/** 사람 역할 — 옅은 회색 계열 (상위/하위 2단계) */
const HUMAN_UPPER: LaneAccent = { bodyBg: "FFFFFF", border: "94A3B8", text: "000000", accent: "64748B" };
const HUMAN_LOWER: LaneAccent = { bodyBg: "F8FAFC", border: "CBD5E1", text: "000000", accent: "475569" };

/** 정규화 매핑 — 소문자 기준, 동의어 포함 */
const PALETTE: Record<string, LaneAccent> = {
  // AI 레인
  "senior ai": SENIOR_AI,
  "senior": SENIOR_AI,
  "junior ai": JUNIOR_AI,
  "junior": JUNIOR_AI,
  // HR 레인
  "hr 임원": HUMAN_UPPER,
  "hr 담당자": HUMAN_LOWER,
  "hr": HUMAN_LOWER,
  // 현업 레인
  "현업 임원": HUMAN_UPPER,
  "현업 팀장": HUMAN_LOWER,
  "현업 구성원": HUMAN_UPPER,
  "현업": HUMAN_LOWER,
  "임원": HUMAN_UPPER,
  "임원 (=현업 임원)": HUMAN_UPPER,
  "팀장": HUMAN_LOWER,
  "구성원": HUMAN_UPPER,
};

/**
 * 정확한 lane 이름으로 accent 조회 — PPT export 에서 position→laneIdx→laneName 경로로 사용.
 * authoritative source (노드 y 위치 기반) 라서 role 파싱 없이 신뢰할 수 있음.
 */
export function getLaneAccentByName(name?: string | null): LaneAccent | null {
  if (!name) return null;
  const key = name.trim().toLowerCase();
  if (PALETTE[key]) return PALETTE[key];
  // 부분 일치 (예: "Senior AI 그룹" → "senior ai")
  for (const [paletteKey, accent] of Object.entries(PALETTE)) {
    if (key.includes(paletteKey)) return accent;
  }
  return null;
}

/**
 * role 문자열에서 primary lane 을 추출해 accent 반환.
 * - 콤마 구분 role 중 "그 외"/"기타" 를 제외한 첫 매칭 항목을 사용
 * - 매칭 없으면 null
 * - 캔버스 LevelNode 에서 sheet 컨텍스트 없이 작동하려고 role 기반으로 동작
 * - role 이 비어있거나 알 수 없는 값이면 null 반환 → 호출측에서 기본 스타일 유지
 */
export function getLaneAccent(role?: string | null): LaneAccent | null {
  if (!role) return null;
  const parts = role.split(",").map((r) => r.trim()).filter(Boolean);
  for (const p of parts) {
    if (p.startsWith("그 외") || p.startsWith("기타")) continue;
    const accent = getLaneAccentByName(p);
    if (accent) return accent;
  }
  return null;
}

/**
 * 노드의 CSV-파생 actors 필드에서 가장 먼저 비어있지 않은 항목을 찾아 accent 반환.
 * role 이 비어있을 때의 백업 경로 — CSV 기반 노드가 색상 입혀지도록 함.
 */
export function getLaneAccentFromActors(actors?: {
  exec?: string;
  hr?: string;
  teamlead?: string;
  member?: string;
} | null): LaneAccent | null {
  if (!actors) return null;
  if (actors.exec?.trim()) return HUMAN_UPPER;    // 임원
  if (actors.hr?.trim()) return HUMAN_LOWER;      // HR
  if (actors.teamlead?.trim()) return HUMAN_LOWER; // 팀장
  if (actors.member?.trim()) return HUMAN_UPPER;  // 구성원
  return null;
}

/**
 * 전체 lane 이름 목록과 각 lane 의 accent — 범례(legend) 렌더링용.
 * 주어진 lane 이름들 중 팔레트에 등록된 것만 반환.
 */
export function getLaneLegend(lanes: string[]): { name: string; accent: LaneAccent }[] {
  return lanes
    .map((name) => {
      const accent = getLaneAccentByName(name);
      return accent ? { name, accent } : null;
    })
    .filter((x): x is { name: string; accent: LaneAccent } => x !== null);
}
