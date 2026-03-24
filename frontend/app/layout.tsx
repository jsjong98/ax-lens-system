import type { Metadata } from "next";
import { Noto_Sans_KR } from "next/font/google";
import "./globals.css";
import LayoutShell from "@/components/LayoutShell";

const notoSansKR = Noto_Sans_KR({
  variable: "--font-noto-sans-kr",
  weight: ["400", "500", "600", "700"],
  preload: false,
  display: "swap",
});

export const metadata: Metadata = {
  title: "PwC AX Lens System",
  description: "AI 기반 업무 혁신 설계 플랫폼 — Pain Point 분석부터 To-Be Workflow 설계, 과제 정의서까지",
  icons: {
    icon: "/pwc-logo.svg",
    shortcut: "/pwc-logo.svg",
  },
  openGraph: {
    title: "PwC AX Lens System",
    description: "AI 기반 업무 혁신 설계 플랫폼 — Pain Point 분석부터 To-Be Workflow 설계, 과제 정의서까지",
    url: "https://pwc-ax-lens.com",
    siteName: "PwC AX Lens",
    images: [{ url: "/og-image.png", width: 1200, height: 630, alt: "PwC AX Lens System" }],
    locale: "ko_KR",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "PwC AX Lens System",
    description: "AI 기반 업무 혁신 설계 플랫폼",
    images: ["/og-image.png"],
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body className={`${notoSansKR.variable} antialiased min-h-screen`} style={{ background: "#FFF5F7" }}>
        <LayoutShell>{children}</LayoutShell>
      </body>
    </html>
  );
}
