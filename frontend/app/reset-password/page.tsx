"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Mail, KeyRound, Lock } from "lucide-react";
import { requestResetCode, verifyResetCode, confirmResetPassword } from "@/lib/api";

type Step = "email" | "code" | "newPassword";

export default function ResetPasswordPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("email");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [newPw, setNewPw] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleRequestCode = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const msg = await requestResetCode(email);
      setMessage(msg);
      setStep("code");
    } catch (err) {
      setError(err instanceof Error ? err.message : "요청 실패");
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyCode = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await verifyResetCode(email, code);
      setStep("newPassword");
    } catch (err) {
      setError(err instanceof Error ? err.message : "인증 실패");
    } finally {
      setLoading(false);
    }
  };

  const handleResetPassword = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError("");
    if (newPw.length < 4) {
      setError("비밀번호는 4자 이상이어야 합니다.");
      return;
    }
    if (newPw !== confirmPw) {
      setError("비밀번호가 일치하지 않습니다.");
      return;
    }
    setLoading(true);
    try {
      await confirmResetPassword(email, code, newPw);
      router.replace("/login");
    } catch (err) {
      setError(err instanceof Error ? err.message : "재설정 실패");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center" style={{ background: "#FFF5F7" }}>
      <div className="w-full max-w-md">
        {/* 로고 */}
        <div className="text-center mb-8">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/strategyand-logo.svg" alt="Strategy&" className="mx-auto h-12 w-auto mb-4" />
          <h1 className="text-2xl font-bold" style={{ color: "#A62121" }}>비밀번호 재설정</h1>
        </div>

        <div className="bg-white rounded-2xl shadow-lg p-8">
          {/* 단계 표시 */}
          <div className="flex items-center justify-center gap-2 mb-6">
            {(["email", "code", "newPassword"] as Step[]).map((s, i) => (
              <div key={s} className="flex items-center gap-2">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold ${
                    step === s
                      ? "text-white"
                      : i < ["email", "code", "newPassword"].indexOf(step)
                      ? "bg-green-100 text-green-700"
                      : "bg-gray-100 text-gray-400"
                  }`}
                  style={step === s ? { backgroundColor: "#A62121" } : undefined}
                >
                  {i + 1}
                </div>
                {i < 2 && <div className="w-8 h-px bg-gray-300" />}
              </div>
            ))}
          </div>

          {/* Step 1: 이메일 입력 */}
          {step === "email" && (
            <form onSubmit={handleRequestCode} className="space-y-5">
              <div className="text-center mb-2">
                <Mail className="mx-auto h-10 w-10 text-gray-400 mb-3" />
                <p className="text-sm text-gray-600">
                  등록된 이메일을 입력하면<br />인증번호를 보내드립니다.
                </p>
              </div>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="이메일 주소 입력"
                required
                autoFocus
                className="w-full rounded-lg border border-gray-300 px-4 py-3 text-sm focus:border-[#A62121] focus:ring-1 focus:ring-[#A62121] outline-none"
              />
              {error && <p className="text-sm text-red-600">{error}</p>}
              <button
                type="submit"
                disabled={loading}
                className="w-full rounded-lg py-3 text-sm font-semibold text-white disabled:opacity-50"
                style={{ backgroundColor: "#A62121" }}
              >
                {loading ? "발송 중..." : "인증번호 발송"}
              </button>
            </form>
          )}

          {/* Step 2: 인증번호 입력 */}
          {step === "code" && (
            <form onSubmit={handleVerifyCode} className="space-y-5">
              <div className="text-center mb-2">
                <KeyRound className="mx-auto h-10 w-10 text-gray-400 mb-3" />
                <p className="text-sm text-gray-600">
                  <strong>{email}</strong>으로<br />발송된 6자리 인증번호를 입력해 주세요.
                </p>
                {message && (
                  <p className="mt-2 text-xs text-green-600">{message}</p>
                )}
              </div>
              <input
                type="text"
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                placeholder="000000"
                required
                maxLength={6}
                autoFocus
                className="w-full rounded-lg border border-gray-300 px-4 py-3 text-center text-2xl tracking-[0.5em] font-mono focus:border-[#A62121] focus:ring-1 focus:ring-[#A62121] outline-none"
              />
              {error && <p className="text-sm text-red-600">{error}</p>}
              <button
                type="submit"
                disabled={loading || code.length !== 6}
                className="w-full rounded-lg py-3 text-sm font-semibold text-white disabled:opacity-50"
                style={{ backgroundColor: "#A62121" }}
              >
                {loading ? "확인 중..." : "인증번호 확인"}
              </button>
              <button
                type="button"
                onClick={() => { setStep("email"); setError(""); setCode(""); }}
                className="w-full text-sm text-gray-500 hover:text-gray-700"
              >
                다른 이메일로 다시 시도
              </button>
            </form>
          )}

          {/* Step 3: 새 비밀번호 설정 */}
          {step === "newPassword" && (
            <form onSubmit={handleResetPassword} className="space-y-5">
              <div className="text-center mb-2">
                <Lock className="mx-auto h-10 w-10 text-gray-400 mb-3" />
                <p className="text-sm text-gray-600">새로운 비밀번호를 설정해 주세요.</p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">새 비밀번호</label>
                <input
                  type="password"
                  value={newPw}
                  onChange={(e) => setNewPw(e.target.value)}
                  required
                  autoFocus
                  className="w-full rounded-lg border border-gray-300 px-4 py-3 text-sm focus:border-[#A62121] focus:ring-1 focus:ring-[#A62121] outline-none"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">비밀번호 확인</label>
                <input
                  type="password"
                  value={confirmPw}
                  onChange={(e) => setConfirmPw(e.target.value)}
                  required
                  className="w-full rounded-lg border border-gray-300 px-4 py-3 text-sm focus:border-[#A62121] focus:ring-1 focus:ring-[#A62121] outline-none"
                />
              </div>
              {error && <p className="text-sm text-red-600">{error}</p>}
              <button
                type="submit"
                disabled={loading}
                className="w-full rounded-lg py-3 text-sm font-semibold text-white disabled:opacity-50"
                style={{ backgroundColor: "#A62121" }}
              >
                {loading ? "재설정 중..." : "비밀번호 재설정"}
              </button>
            </form>
          )}
        </div>

        {/* 로그인으로 돌아가기 */}
        <button
          onClick={() => router.push("/login")}
          className="mt-6 mx-auto flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700"
        >
          <ArrowLeft className="h-4 w-4" />
          로그인으로 돌아가기
        </button>
      </div>
    </div>
  );
}
