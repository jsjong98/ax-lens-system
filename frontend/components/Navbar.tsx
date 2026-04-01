"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ClipboardList, Play, BarChart3, Settings, GitBranch, Sparkles, FolderKanban, LogOut, KeyRound, Shield, ArrowRightLeft, Bell } from "lucide-react";
import { useAuth } from "@/components/AuthProvider";
import ChangePasswordModal from "@/components/ChangePasswordModal";
import { PmApprovalModal, TransferRequestModal } from "@/components/TransferModal";
import { getPendingTransfers } from "@/lib/api";

const baseNavItems = [
  { href: "/tasks",              label: "Task 목록",     icon: ClipboardList },
  { href: "/classify",           label: "분류 실행",     icon: Play          },
  { href: "/results",            label: "결과 확인",     icon: BarChart3     },
  { href: "/workflow",           label: "Workflow",      icon: GitBranch     },
  { href: "/new-workflow",       label: "New Workflow",  icon: Sparkles      },
  { href: "/project-management", label: "과제 관리",     icon: FolderKanban  },
  { href: "/settings",           label: "설정",          icon: Settings      },
];
const adminNavItem = { href: "/admin", label: "Admin", icon: Shield };

export default function Navbar() {
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const [showPwModal, setShowPwModal] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [showPmModal, setShowPmModal] = useState(false);
  const [showTransferModal, setShowTransferModal] = useState(false);
  const [pendingCount, setPendingCount] = useState(0);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // PM이면 대기 중 요청 수 조회
  useEffect(() => {
    if (user?.is_pm || user?.is_admin) {
      getPendingTransfers().then((d) => setPendingCount(d.requests.length)).catch(() => {});
    }
  }, [user]);

  // PM이면 대기 요청 있을 때 자동으로 모달 표시
  useEffect(() => {
    if (pendingCount > 0 && (user?.is_pm || user?.is_admin)) {
      setShowPmModal(true);
    }
  }, [pendingCount, user]);

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
              {[...baseNavItems, ...(user?.is_admin ? [adminNavItem] : [])].map(({ href, label, icon: Icon }) => {
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
                    className="relative flex items-center justify-center w-9 h-9 rounded-full text-sm font-bold text-white transition-transform hover:scale-105 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#A62121]"
                    style={{ backgroundColor: "#A62121" }}
                    title={user.name}
                  >
                    {initial}
                    {pendingCount > 0 && (
                      <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-red-500 text-white text-[9px] font-bold flex items-center justify-center ring-2 ring-white">
                        {pendingCount}
                      </span>
                    )}
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
                            {user.project ? (
                              <span className="inline-block mt-0.5 px-1.5 py-0.5 rounded text-[10px] font-bold bg-blue-100 text-blue-700">{user.project}</span>
                            ) : user.is_admin ? (
                              <span className="inline-block mt-0.5 px-1.5 py-0.5 rounded text-[10px] font-bold bg-red-100 text-red-700">Admin</span>
                            ) : (
                              <span className="inline-block mt-0.5 px-1.5 py-0.5 rounded text-[10px] font-bold bg-green-100 text-green-700">공통</span>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* 메뉴 항목 */}
                      {/* PM: 승인 요청 확인 */}
                      {(user.is_pm || user.is_admin) && (
                        <button
                          onClick={() => { setShowDropdown(false); setShowPmModal(true); }}
                          className="flex w-full items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                        >
                          <Bell className="h-4 w-4 text-gray-400" />
                          이동 요청 승인
                          {pendingCount > 0 && (
                            <span className="ml-auto px-1.5 py-0.5 rounded-full text-[10px] font-bold bg-red-500 text-white">{pendingCount}</span>
                          )}
                        </button>
                      )}
                      {/* 프로젝트 이동 요청 */}
                      <button
                        onClick={() => { setShowDropdown(false); setShowTransferModal(true); }}
                        className="flex w-full items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                      >
                        <ArrowRightLeft className="h-4 w-4 text-gray-400" />
                        프로젝트 이동 요청
                      </button>
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

      {/* PM 승인 모달 */}
      <PmApprovalModal open={showPmModal} onClose={() => setShowPmModal(false)} />

      {/* 프로젝트 이동 요청 모달 */}
      <TransferRequestModal open={showTransferModal} onClose={() => setShowTransferModal(false)} />

      {/* 첫 로그인 시 강제 비밀번호 변경 */}
      {user?.must_change_password && (
        <ChangePasswordModal open forced onClose={() => {}} />
      )}
    </>
  );
}
