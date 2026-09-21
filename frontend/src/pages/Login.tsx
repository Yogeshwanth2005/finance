import { useState } from "react";
import { ArrowRight, HeartHandshake, LockKeyhole, Mail, ShieldCheck } from "lucide-react";
import { Navigate, useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError, apiPost } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { User } from "@/lib/types";

function errorMessage(error: unknown) {
  if (error instanceof ApiError && typeof error.body === "object" && error.body !== null && "detail" in error.body) {
    const detail = (error.body as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return detail.map((item) => (typeof item === "object" && item && "msg" in item ? String(item.msg) : String(item))).join(" ");
  }
  return "Something went wrong. Please try again.";
}

export default function Login() {
  const navigate = useNavigate();
  const { user, login, register } = useAuth();
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [pending, setPending] = useState(false);
  const [forgot, setForgot] = useState(false);
  const [resetToken, setResetToken] = useState("");

  if (user) {
    return <Navigate to={user.role === "admin" ? "/admin/documents" : user.profile_complete ? "/dashboard" : "/"} replace />;
  }

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setPending(true);
    try {
      const nextUser: User = mode === "login" ? await login(email, password) : await register(name, email, password);
      toast.success(mode === "login" ? "Welcome back" : "Account created");
      navigate(nextUser.role === "admin" ? "/admin/documents" : nextUser.profile_complete ? "/dashboard" : "/", { replace: true });
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setPending(false);
    }
  };

  const sendReset = async () => {
    try {
      const result = await apiPost<{ message: string; demo_token?: string }>("/auth/forgot-password", { email });
      setResetToken(result.demo_token ?? "");
      toast.success(result.message);
    } catch (error) {
      toast.error(errorMessage(error));
    }
  };

  return (
    <div className="min-h-svh bg-[#f8f7f4] text-[#17181c]">
      <div className="mx-auto grid min-h-svh max-w-6xl items-center gap-12 px-4 py-10 sm:px-8 lg:grid-cols-[1fr_0.8fr] lg:py-16">
        <div className="hidden lg:block" data-testid="login-value-panel"><div className="flex items-center gap-3" data-testid="login-brand"><span className="flex size-10 items-center justify-center rounded-xl bg-[#0d7a5f] text-white"><HeartHandshake className="size-5" /></span><span className="font-heading text-sm font-bold">SurakshaCFO</span></div><p className="mt-20 max-w-xl font-heading text-5xl font-bold leading-[1.08] tracking-[-0.04em]" data-testid="login-value-heading">Your family’s next best decision starts with a safe place for the numbers.</p><p className="mt-6 max-w-md text-base leading-7 text-[#5c5f66]" data-testid="login-value-copy">Keep your profile, protection gaps and document-grounded insurance conversations together — private to your account.</p><div className="mt-10 flex gap-6 text-xs font-semibold text-[#5c5f66]"><span className="flex items-center gap-2"><ShieldCheck className="size-4 text-[#0d7a5f]" /> Private workspace</span><span className="flex items-center gap-2"><LockKeyhole className="size-4 text-[#0d7a5f]" /> Secure session</span></div></div>

        <Card className="border-[#e4e1d8] bg-white shadow-[0_18px_45px_rgba(23,24,28,0.07)]" data-testid="auth-card"><CardHeader className="p-6 pb-4 sm:p-8 sm:pb-5"><div className="flex items-center justify-between"><div><p className="text-[10px] font-bold uppercase tracking-[0.18em] text-[#0d7a5f]" data-testid="auth-eyebrow">Family finance workspace</p><CardTitle className="mt-3 text-2xl font-semibold tracking-tight" data-testid="auth-title">{forgot ? "Reset your password" : mode === "login" ? "Welcome back" : "Create your secure account"}</CardTitle></div><Mail className="size-5 text-[#0d7a5f]" /></div></CardHeader><CardContent className="p-6 pt-2 sm:p-8 sm:pt-3">
          {forgot ? <div data-testid="forgot-password-panel"><p className="text-sm leading-6 text-[#5c5f66]" data-testid="forgot-password-description">Enter the email for your SurakshaCFO account. In this demo workspace, the reset token appears here instead of being emailed.</p><label className="mt-6 block space-y-2"><span className="text-xs font-semibold text-[#5c5f66]">Email address</span><Input type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" data-testid="forgot-password-email-input" /></label><Button className="mt-5 w-full bg-[#0d7a5f] text-white hover:bg-[#0a624c]" onClick={sendReset} data-testid="forgot-password-submit-button">Create reset link <ArrowRight className="size-4" /></Button>{resetToken && <div className="mt-5 rounded-xl border border-[#eadcc8] bg-[#fff9ef] p-4" data-testid="forgot-password-demo-token"><p className="text-xs font-semibold text-[#a16207]">DEMO reset token ready</p><p className="mt-2 break-all font-mono text-[11px] text-[#5c5f66]">{resetToken}</p><Button variant="outline" size="sm" className="mt-3 bg-white" onClick={() => navigate(`/reset-password?token=${encodeURIComponent(resetToken)}`)} data-testid="forgot-password-open-reset-button">Open reset form</Button></div>}<button type="button" className="mt-6 text-xs font-semibold text-[#0d7a5f]" onClick={() => setForgot(false)} data-testid="forgot-password-back-button">Back to sign in</button></div> : <><div className="mb-6 flex rounded-lg border border-[#e4e1d8] bg-[#f8f7f4] p-1" data-testid="auth-mode-tabs"><button type="button" onClick={() => setMode("login")} className={`flex-1 rounded-md py-2 text-xs font-semibold ${mode === "login" ? "bg-white text-[#17181c] shadow-sm" : "text-[#8a8f99]"}`} data-testid="login-mode-button">Sign in</button><button type="button" onClick={() => setMode("signup")} className={`flex-1 rounded-md py-2 text-xs font-semibold ${mode === "signup" ? "bg-white text-[#17181c] shadow-sm" : "text-[#8a8f99]"}`} data-testid="signup-mode-button">Create account</button></div><form onSubmit={submit} className="space-y-4" data-testid={mode === "login" ? "login-form" : "signup-form"}>{mode === "signup" && <label className="block space-y-2"><span className="text-xs font-semibold text-[#5c5f66]">Your name</span><Input value={name} onChange={(event) => setName(event.target.value)} placeholder="Rohan Sharma" required data-testid="signup-name-input" /></label>}<label className="block space-y-2"><span className="text-xs font-semibold text-[#5c5f66]">Email address</span><Input type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" required data-testid={`${mode}-email-input`} /></label><label className="block space-y-2"><span className="text-xs font-semibold text-[#5c5f66]">Password</span><Input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="At least 8 characters" minLength={8} required data-testid={`${mode}-password-input`} /></label><Button type="submit" disabled={pending} className="mt-2 w-full bg-[#0d7a5f] text-white hover:bg-[#0a624c]" data-testid={mode === "login" ? "login-submit-button" : "signup-submit-button"}>{pending ? "Securing your workspace…" : mode === "login" ? "Sign in" : "Create account"} <ArrowRight className="size-4" /></Button></form>{mode === "login" && <button type="button" onClick={() => setForgot(true)} className="mt-5 text-xs font-semibold text-[#0d7a5f]" data-testid="forgot-password-link">Forgot password?</button>}<p className="mt-8 border-t border-[#f1efe9] pt-5 text-[11px] leading-5 text-[#8a8f99]" data-testid="auth-google-status">Google sign-in is ready to add when OAuth credentials are available. Email/password is fully enabled now.</p></>}
        </CardContent></Card>
      </div>
    </div>
  );
}