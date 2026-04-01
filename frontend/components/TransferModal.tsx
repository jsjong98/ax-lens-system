"use client";

import { useState, useEffect, useCallback } from "react";
import {
  getPendingTransfers,
  approveTransfer,
  rejectTransfer,
  requestProjectTransfer,
  type TransferRequest,
} from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";

const ALL_PROJECTS = ["공통", "SKI", "두산"];

/* ── PM 승인 모달 ──────────────────────────────────────────────────────────── */

export function PmApprovalModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [requests, setRequests] = useState<TransferRequest[]>([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getPendingTransfers();
      setRequests(data.requests);
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => {
    if (open) load();
  }, [open, load]);

  const handle = async (id: string, action: "approve" | "reject") => {
    try {
      if (action === "approve") await approveTransfer(id);
      else await rejectTransfer(id);
      load();
    } catch (e) {
      alert((e as Error).message);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg mx-4" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-bold text-gray-800">프로젝트 이동 요청 승인</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
        </div>

        <div className="p-6 max-h-[400px] overflow-y-auto">
          {loading && <div className="text-center py-6 text-gray-400 text-sm">로딩 중...</div>}
          {!loading && requests.length === 0 && (
            <div className="text-center py-8 text-gray-400 text-sm">
              대기 중인 이동 요청이 없습니다.
            </div>
          )}
          {requests.map((req) => (
            <div key={req.id} className="border border-gray-200 rounded-lg p-4 mb-3">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <span className="font-bold text-gray-800">{req.name}</span>
                  <span className="text-xs text-gray-400 ml-2">{req.email}</span>
                </div>
                <span className="text-xs text-gray-400">{req.created_at.replace("T", " ").slice(0, 16)}</span>
              </div>
              <div className="flex items-center gap-2 mb-2 text-sm">
                <span className="px-2 py-0.5 rounded bg-gray-100 text-gray-600">{req.current_project || "공통"}</span>
                <span className="text-gray-400">&rarr;</span>
                <span className="px-2 py-0.5 rounded bg-blue-100 text-blue-700 font-bold">{req.target_project}</span>
              </div>
              {req.reason && <p className="text-xs text-gray-500 mb-3">사유: {req.reason}</p>}
              <div className="flex gap-2 justify-end">
                <button
                  onClick={() => handle(req.id, "reject")}
                  className="px-4 py-1.5 rounded-lg text-xs font-medium border border-gray-300 text-gray-600 hover:bg-gray-50"
                >
                  거절
                </button>
                <button
                  onClick={() => handle(req.id, "approve")}
                  className="px-4 py-1.5 rounded-lg text-xs font-bold text-white"
                  style={{ backgroundColor: "#A62121" }}
                >
                  승인
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ── 이동 요청 모달 (일반 사용자) ────────────────────────────────────────────── */

export function TransferRequestModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { user } = useAuth();
  const [target, setTarget] = useState("");
  const [reason, setReason] = useState("");
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async () => {
    if (!target) return;
    setLoading(true);
    setError("");
    try {
      await requestProjectTransfer(target, reason);
      setDone(true);
    } catch (e) {
      setError((e as Error).message);
    }
    setLoading(false);
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-bold text-gray-800">프로젝트 이동 요청</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">&times;</button>
        </div>

        <div className="p-6">
          {done ? (
            <div className="text-center py-6">
              <div className="text-3xl mb-3">&#9989;</div>
              <p className="text-sm text-gray-700 font-medium">이동 요청이 제출되었습니다.</p>
              <p className="text-xs text-gray-400 mt-1">PM 또는 Admin의 승인을 기다려주세요.</p>
              <button onClick={onClose} className="mt-4 px-4 py-2 rounded-lg text-sm text-white" style={{ backgroundColor: "#A62121" }}>
                닫기
              </button>
            </div>
          ) : (
            <>
              <div className="mb-4">
                <div className="text-xs text-gray-500 mb-1">현재 프로젝트</div>
                <div className="px-3 py-2 bg-gray-50 rounded-lg text-sm font-medium text-gray-700">
                  {user?.project || "공통"}
                </div>
              </div>

              <div className="mb-4">
                <label className="text-xs text-gray-500 mb-1 block">이동할 프로젝트</label>
                <select
                  value={target}
                  onChange={(e) => setTarget(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                >
                  <option value="">선택...</option>
                  {ALL_PROJECTS.filter((p) => p !== (user?.project || "공통")).map((p) => (
                    <option key={p} value={p}>{p}</option>
                  ))}
                </select>
              </div>

              <div className="mb-4">
                <label className="text-xs text-gray-500 mb-1 block">사유 (선택)</label>
                <input
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  placeholder="이동 사유를 입력하세요..."
                />
              </div>

              {error && <p className="text-xs text-red-600 mb-3">{error}</p>}

              <button
                onClick={handleSubmit}
                disabled={!target || loading}
                className="w-full py-2.5 rounded-lg text-sm font-bold text-white disabled:opacity-50"
                style={{ backgroundColor: "#A62121" }}
              >
                {loading ? "요청 중..." : "이동 요청"}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
