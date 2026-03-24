"use client";

import { useState } from "react";
import { X, Eye, EyeOff, Check, AlertCircle } from "lucide-react";
import { changePassword } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";

interface Props {
  open: boolean;
  onClose: () => void;
  forced?: boolean;
}

function PasswordInput({
  label,
  value,
  onChange,
  hint,
  status,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  hint?: string;
  status?: "match" | "mismatch" | null;
}) {
  const [show, setShow] = useState(false);
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      <div className="relative">
        <input
          type={show ? "text" : "password"}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          required
          className={`w-full rounded-lg border px-4 py-2.5 pr-20 text-sm outline-none transition-colors ${
            status === "mismatch"
              ? "border-red-400 focus:border-red-500 focus:ring-1 focus:ring-red-500"
              : status === "match"
              ? "border-green-400 focus:border-green-500 focus:ring-1 focus:ring-green-500"
              : "border-gray-300 focus:border-[#A62121] focus:ring-1 focus:ring-[#A62121]"
          }`}
        />
        <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
          {status === "match" && <Check className="h-4 w-4 text-green-500" />}
          {status === "mismatch" && <AlertCircle className="h-4 w-4 text-red-400" />}
          <button
            type="button"
            onClick={() => setShow((v) => !v)}
            className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
            tabIndex={-1}
          >
            {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        </div>
      </div>
      {hint && <p className={`text-xs mt-1 ${status === "mismatch" ? "text-red-500" : "text-gray-400"}`}>{hint}</p>}
    </div>
  );
}

export default function ChangePasswordModal({ open, onClose, forced }: Props) {
  const { refresh } = useAuth();
  const [oldPw, setOldPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  if (!open) return null;

  // 실시간 검증
  const newPwValid = newPw.length >= 4;
  const confirmMatch = confirmPw.length > 0 && newPw === confirmPw;
  const confirmMismatch = confirmPw.length > 0 && newPw !== confirmPw;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (!newPwValid) {
      setError("새 비밀번호는 4자 이상이어야 합니다.");
      return;
    }
    if (!confirmMatch) {
      setError("새 비밀번호가 일치하지 않습니다.");
      return;
    }

    setLoading(true);
    try {
      await changePassword(oldPw, newPw);
      await refresh();
      setOldPw("");
      setNewPw("");
      setConfirmPw("");
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "비밀번호 변경 실패");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50">
      <div className="w-full max-w-md rounded-2xl bg-white p-8 shadow-2xl">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-gray-900">비밀번호 변경</h2>
          {!forced && (
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
              <X className="h-5 w-5" />
            </button>
          )}
        </div>

        {forced && (
          <p className="mb-4 text-sm text-amber-700 bg-amber-50 rounded-lg p-3">
            초기 비밀번호를 사용 중입니다. 보안을 위해 비밀번호를 변경해 주세요.
          </p>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <PasswordInput
            label="현재 비밀번호"
            value={oldPw}
            onChange={setOldPw}
          />
          <PasswordInput
            label="새 비밀번호"
            value={newPw}
            onChange={setNewPw}
            hint={newPw.length > 0 && !newPwValid ? "4자 이상 입력해 주세요" : undefined}
            status={newPw.length > 0 ? (newPwValid ? null : "mismatch") : null}
          />
          <PasswordInput
            label="새 비밀번호 확인"
            value={confirmPw}
            onChange={setConfirmPw}
            hint={
              confirmMismatch ? "비밀번호가 일치하지 않습니다" :
              confirmMatch ? "비밀번호가 일치합니다" : undefined
            }
            status={confirmMatch ? "match" : confirmMismatch ? "mismatch" : null}
          />

          {error && <p className="text-sm text-red-600">{error}</p>}

          <button
            type="submit"
            disabled={loading || !newPwValid || !confirmMatch}
            className="w-full rounded-lg py-2.5 text-sm font-semibold text-white transition-colors disabled:opacity-50"
            style={{ backgroundColor: "#A62121" }}
          >
            {loading ? "변경 중..." : "비밀번호 변경"}
          </button>
        </form>
      </div>
    </div>
  );
}
