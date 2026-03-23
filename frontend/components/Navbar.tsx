"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ClipboardList, Play, BarChart3, Settings, GitBranch, Sparkles, FolderKanban, LogOut, KeyRound } from "lucide-react";
import { useAuth } from "@/components/AuthProvider";
import ChangePasswordModal from "@/components/ChangePasswordModal";

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
  const { user, logout } = useAuth();
  const [showPwModal, setShowPwModal] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // 드롭다운 외부 클릭 시 닫기
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  // 이름의 첫 글자 (아바타용)
  const initial = user?.name?.charAt(0) || "?";

  return (
    <>
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

            {/* 메뉴 + 사용자 */}
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

              {/* 사용자 아바타 + 드롭다운 */}
              {user && (
                <div className="relative ml-3" ref={dropdownRef}>
                  <button
                    onClick={() => setShowDropdown((v) => !v)}
                    className="flex items-center justify-center w-9 h-9 rounded-full text-sm font-bold text-white transition-transform hover:scale-105 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#A62121]"
                    style={{ backgroundColor: "#A62121" }}
                    title={user.name}
                  >
                    {initial}
                  </button>

                  {showDropdown && (
                    <div className="absolute right-0 mt-2 w-64 rounded-xl bg-white shadow-xl ring-1 ring-black/5 py-1 z-[60]">
                      {/* 사용자 정보 */}
                      <div className="px-4 py-3 border-b border-gray-100">
                        <div className="flex items-center gap-3">
                          <div
                            className="flex items-center justify-center w-10 h-10 rounded-full text-sm font-bold text-white shrink-0"
                            style={{ backgroundColor: "#A62121" }}
                          >
                            {initial}
                          </div>
                          <div className="min-w-0">
                            <p className="text-sm font-semibold text-gray-900 truncate">{user.name}</p>
                            <p className="text-xs text-gray-500 truncate">{user.email}</p>
                          </div>
                        </div>
                      </div>

                      {/* 메뉴 항목 */}
                      <button
                        onClick={() => { setShowDropdown(false); setShowPwModal(true); }}
                        className="flex w-full items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                      >
                        <KeyRound className="h-4 w-4 text-gray-400" />
                        비밀번호 변경
                      </button>
                      <div className="border-t border-gray-100" />
                      <button
                        onClick={() => { setShowDropdown(false); logout(); }}
                        className="flex w-full items-center gap-3 px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 transition-colors"
                      >
                        <LogOut className="h-4 w-4" />
                        로그아웃
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </nav>

      {/* 비밀번호 변경 모달 */}
      <ChangePasswordModal open={showPwModal} onClose={() => setShowPwModal(false)} />

      {/* 첫 로그인 시 강제 비밀번호 변경 */}
      {user?.must_change_password && (
        <ChangePasswordModal open forced onClose={() => {}} />
      )}
    </>
  );
}
