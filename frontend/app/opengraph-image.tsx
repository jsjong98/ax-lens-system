import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "PwC AX Lens System";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          background: "linear-gradient(135deg, #FFF5F7 0%, #FFFFFF 50%, #FFF5F7 100%)",
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          fontFamily: "sans-serif",
        }}
      >
        {/* 상단 라인 */}
        <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 6, background: "#A62121" }} />

        {/* Strategy& 텍스트 */}
        <div style={{ fontSize: 24, fontWeight: 700, color: "#666", marginBottom: 16, letterSpacing: 2 }}>
          strategy&
        </div>

        {/* 메인 타이틀 */}
        <div style={{ fontSize: 56, fontWeight: 800, color: "#A62121", marginBottom: 12 }}>
          PwC AX Lens System
        </div>

        {/* 서브타이틀 */}
        <div style={{ fontSize: 24, color: "#666", marginBottom: 40 }}>
          Process Innovation System
        </div>

        {/* 키워드 태그 */}
        <div style={{ display: "flex", gap: 12 }}>
          {["AI Workflow 설계", "Pain Point 분석", "벤치마킹", "과제 정의서"].map((tag) => (
            <div
              key={tag}
              style={{
                padding: "8px 20px",
                borderRadius: 20,
                border: "1.5px solid #A62121",
                color: "#A62121",
                fontSize: 16,
                fontWeight: 600,
              }}
            >
              {tag}
            </div>
          ))}
        </div>

        {/* 하단 URL */}
        <div style={{ position: "absolute", bottom: 30, fontSize: 18, color: "#999" }}>
          pwc-ax-lens.com
        </div>
      </div>
    ),
    { ...size }
  );
}
