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
  description: "Process Innovation System — AI 기반 업무 혁신 설계 플랫폼",
  icons: {
    icon: "/pwc-logo.svg",
    shortcut: "/pwc-logo.svg",
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
