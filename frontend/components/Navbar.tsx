"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ClipboardList, Play, BarChart3, Settings, GitBranch, Sparkles, FolderKanban } from "lucide-react";

const navItems = [
  { href: "/tasks",              label: "Task 목록",     icon: ClipboardList },
  { href: "/classify",           label: "분류 실행",     icon: Play          },
  { href: "/results",            label: "결과 확인",     icon: BarChart3     },
  { href: "/workflow",           label: "Workflow",      icon: GitBranch     },
  { href: "/new-workflow",       label: "New Workflow",  icon: Sparkles      },
  { href: "/project-management", label: "과제 관리",     icon: FolderKanban  },
  { href: "/settings",           label: "설정",          icon: Settings      },
];

export default function Navbar() {
  const pathname = usePathname();

  return (
    <nav className="sticky top-0 z-50 bg-white shadow-sm" style={{ borderBottom: "2px solid #A62121" }}>
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          {/* 로고 */}
          <Link href="/tasks" className="flex items-center gap-3">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src="/strategyand-logo.svg"
              alt="Strategy&"
              className="h-8 w-auto"
            />
            <div className="h-5 w-px bg-gray-300" />
            <span className="text-sm font-semibold tracking-tight" style={{ color: "#A62121" }}>
              PwC AX Lens System
            </span>
          </Link>

          {/* 메뉴 */}
          <div className="flex items-center gap-1">
            {navItems.map(({ href, label, icon: Icon }) => {
              const active = pathname.startsWith(href);
              return (
                <Link
                  key={href}
                  href={href}
                  className={`flex items-center gap-1.5 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                    active
                      ? "text-white"
                      : "text-gray-600 hover:text-gray-900"
                  }`}
                  style={active
                    ? { backgroundColor: "#A62121" }
                    : undefined}
                  onMouseEnter={(e) => { if (!active) (e.currentTarget as HTMLElement).style.backgroundColor = "#FFF5F7"; }}
                  onMouseLeave={(e) => { if (!active) (e.currentTarget as HTMLElement).style.backgroundColor = ""; }}
                >
                  <Icon className="h-4 w-4" />
                  {label}
                </Link>
              );
            })}
          </div>
        </div>
      </div>
    </nav>
  );
}
