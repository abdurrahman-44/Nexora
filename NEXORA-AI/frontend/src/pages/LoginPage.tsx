import React, { useEffect, useState } from "react";
import { KeyRound, Lock, Mail, ShieldCheck, Sparkles, UserCheck } from "lucide-react";
import { apiRequest } from "../api/client";
import { useAuth } from "../context/AuthContext";

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const [mode, setMode] = useState<"login" | "forgot" | "reset" | "mfa">("login");
  const [email, setEmail] = useState("admin@nexora.lk");
  const [password, setPassword] = useState("Nexora#2026");
  const [totpCode, setTotpCode] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [infoMessage, setInfoMessage] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [demoAccounts, setDemoAccounts] = useState<any[]>([]);

  useEffect(() => {
    apiRequest("/auth/demo-accounts")
      .then((res) => setDemoAccounts(res.accounts || []))
      .catch(() => {});
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setInfoMessage(null);
    setSubmitting(true);
    try {
      if (mode === "login" || mode === "mfa") {
        const res = await login(email, password, mode === "mfa" ? totpCode : undefined);
        if (res.mfa_required) {
          setMode("mfa");
          setInfoMessage("Multi-Factor Authentication is enabled. Enter your 6-digit TOTP code.");
        }
      } else if (mode === "forgot") {
        const res = await apiRequest("/auth/forgot-password", {
          method: "POST",
          body: JSON.stringify({ email }),
        });
        setInfoMessage(res.message);
        if (res.demo_reset_token) {
          setResetToken(res.demo_reset_token);
          setMode("reset");
        }
      } else if (mode === "reset") {
        const res = await apiRequest("/auth/reset-password", {
          method: "POST",
          body: JSON.stringify({
            email,
            reset_token: resetToken,
            new_password: newPassword,
          }),
        });
        setInfoMessage(res.message);
        setPassword(newPassword);
        setMode("login");
      }
    } catch (err: any) {
      setError(err.message || "Authentication failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#080D18] text-[#F5F7FC] flex items-center justify-center p-6 relative overflow-hidden">
      {/* Ambient Background Orbs */}
      <div className="pointer-events-none fixed inset-0">
        <div className="absolute -top-32 left-1/4 w-96 h-96 rounded-full bg-[#648BFF]/20 blur-[130px]" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 rounded-full bg-[#8B7CFF]/15 blur-[130px]" />
      </div>

      <div className="w-full max-w-5xl grid grid-cols-1 lg:grid-cols-12 gap-8 z-10 items-center">
        {/* Left Brand & Role Demo Selector */}
        <div className="lg:col-span-7 space-y-6">
          <div className="inline-flex items-center gap-2.5 px-3.5 py-1.5 rounded-full glass-panel text-xs text-[#648BFF] font-medium">
            <Sparkles className="w-4 h-4" />
            AI-Powered Enterprise Resource Planning Platform
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight leading-tight">
            One intelligent platform.{" "}
            <span className="bg-gradient-to-r from-[#648BFF] via-[#8B7CFF] to-[#20C997] bg-clip-text text-transparent">
              Every business operation.
            </span>{" "}
            Better decisions.
          </h1>
          <p className="text-sm text-[#94A3B8] leading-relaxed max-w-xl">
            Experience <strong className="text-white">Nexora Demo Holdings</strong> — pre-populated with multi-branch LKR operations, double-entry General Ledger, Weighted Average Cost inventory, threshold approval workflows, and machine learning demand & anomaly intelligence.
          </p>

          {/* Instant Demo Role Switcher */}
          <div className="glass-panel rounded-2xl p-4 border border-white/10">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold uppercase tracking-wider text-[#94A3B8] flex items-center gap-1.5">
                <UserCheck className="w-3.5 h-3.5 text-[#20C997]" />
                Click Any Role to Auto-Fill Credentials (Password: Nexora#2026)
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-64 overflow-y-auto pr-1">
              {demoAccounts.map((acc) => (
                <button
                  key={acc.email}
                  type="button"
                  onClick={() => {
                    setEmail(acc.email);
                    setPassword("Nexora#2026");
                    setMode("login");
                    setError(null);
                  }}
                  className={`p-2.5 rounded-xl border text-left transition flex items-center justify-between ${
                    email === acc.email
                      ? "bg-[#648BFF]/20 border-[#648BFF] text-white"
                      : "bg-white/5 border-white/10 hover:bg-white/10 text-[#94A3B8]"
                  }`}
                >
                  <div className="min-w-0">
                    <div className="text-xs font-semibold text-white truncate">
                      {acc.full_name}
                    </div>
                    <div className="text-[11px] font-mono text-[#648BFF] truncate">
                      {acc.email}
                    </div>
                  </div>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-white/10 text-white shrink-0 ml-2">
                    {acc.roles?.[0] || "USER"}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Right Glass Authentication Card */}
        <div className="lg:col-span-5">
          <div className="glass-panel rounded-3xl p-8 border border-white/15 shadow-2xl space-y-6">
            <div className="flex items-center gap-3">
              <div className="w-11 h-11 rounded-2xl bg-gradient-to-br from-[#648BFF] to-[#8B7CFF] flex items-center justify-center shadow-lg shadow-[#648BFF]/30">
                <ShieldCheck className="w-6 h-6 text-white" />
              </div>
              <div>
                <h2 className="text-lg font-bold">
                  {mode === "login" && "Sign in to NEXORA ERP"}
                  {mode === "mfa" && "TOTP MFA Verification"}
                  {mode === "forgot" && "Password Recovery"}
                  {mode === "reset" && "Set New Argon2id Password"}
                </h2>
                <p className="text-xs text-[#94A3B8]">
                  Argon2id • JWT + HttpOnly Refresh Rotation • RBAC
                </p>
              </div>
            </div>

            {error && (
              <div className="p-3 rounded-xl bg-[#F06464]/15 border border-[#F06464]/40 text-xs text-[#F06464]">
                {error}
              </div>
            )}

            {infoMessage && (
              <div className="p-3 rounded-xl bg-[#20C997]/15 border border-[#20C997]/40 text-xs text-[#20C997]">
                {infoMessage}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-[#94A3B8] mb-1.5">
                  Corporate Email Address
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-[#94A3B8] absolute left-3.5 top-3" />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-[#141F31] border border-white/10 text-sm focus:outline-none focus:border-[#648BFF]"
                    placeholder="admin@nexora.lk"
                  />
                </div>
              </div>

              {(mode === "login" || mode === "mfa") && (
                <div>
                  <label className="block text-xs font-medium text-[#94A3B8] mb-1.5">
                    Password
                  </label>
                  <div className="relative">
                    <Lock className="w-4 h-4 text-[#94A3B8] absolute left-3.5 top-3" />
                    <input
                      type="password"
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-[#141F31] border border-white/10 text-sm focus:outline-none focus:border-[#648BFF]"
                    />
                  </div>
                </div>
              )}

              {mode === "mfa" && (
                <div>
                  <label className="block text-xs font-medium text-[#94A3B8] mb-1.5">
                    6-Digit Authenticator Code
                  </label>
                  <div className="relative">
                    <KeyRound className="w-4 h-4 text-[#648BFF] absolute left-3.5 top-3" />
                    <input
                      type="text"
                      required
                      maxLength={6}
                      value={totpCode}
                      onChange={(e) => setTotpCode(e.target.value)}
                      className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-[#141F31] border border-[#648BFF] text-sm font-mono tracking-widest focus:outline-none"
                      placeholder="000000"
                    />
                  </div>
                </div>
              )}

              {mode === "reset" && (
                <>
                  <div>
                    <label className="block text-xs font-medium text-[#94A3B8] mb-1.5">
                      Reset Token
                    </label>
                    <input
                      type="text"
                      required
                      value={resetToken}
                      onChange={(e) => setResetToken(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-[#141F31] border border-white/10 text-xs font-mono"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-[#94A3B8] mb-1.5">
                      New Password (min 8 chars)
                    </label>
                    <input
                      type="password"
                      required
                      minLength={8}
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-xl bg-[#141F31] border border-white/10 text-sm"
                    />
                  </div>
                </>
              )}

              <button
                type="submit"
                disabled={submitting}
                className="w-full py-3 rounded-xl bg-gradient-to-r from-[#648BFF] to-[#8B7CFF] hover:opacity-95 text-white font-semibold text-sm shadow-lg shadow-[#648BFF]/25 transition disabled:opacity-50"
              >
                {submitting
                  ? "Authenticating..."
                  : mode === "login"
                  ? "Access Enterprise Workspace"
                  : mode === "mfa"
                  ? "Verify MFA Code"
                  : mode === "forgot"
                  ? "Generate Password Reset Token"
                  : "Reset Password"}
              </button>
            </form>

            <div className="flex items-center justify-between text-xs text-[#94A3B8] pt-2 border-t border-white/10">
              {mode === "login" ? (
                <button
                  type="button"
                  onClick={() => setMode("forgot")}
                  className="hover:text-[#648BFF] transition"
                >
                  Forgot password?
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => setMode("login")}
                  className="hover:text-[#648BFF] transition"
                >
                  ← Back to Sign In
                </button>
              )}
              <span>Locale: LKR • Asia/Colombo</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
