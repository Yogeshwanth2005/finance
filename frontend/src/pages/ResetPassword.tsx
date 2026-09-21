import { useState } from "react";
import { ArrowRight, LockKeyhole } from "lucide-react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError, apiPost } from "@/lib/api";

export default function ResetPassword() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [token, setToken] = useState(params.get("token") ?? "");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [pending, setPending] = useState(false);

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (password !== confirm) { toast.error("Passwords do not match"); return; }
    setPending(true);
    try {
      await apiPost<{ message: string }>("/auth/reset-password", { token, password });
      toast.success("Password updated");
      navigate("/login", { replace: true });
    } catch (error) {
      toast.error(error instanceof ApiError && typeof error.body === "object" && error.body && "detail" in error.body ? String((error.body as { detail: unknown }).detail) : "This reset link is no longer valid");
    } finally { setPending(false); }
  };

  return <div className="flex min-h-svh items-center justify-center bg-[#f8f7f4] px-4"><Card className="w-full max-w-md border-[#e4e1d8] bg-white shadow-[0_18px_45px_rgba(23,24,28,0.07)]" data-testid="reset-password-card"><CardHeader className="p-6 pb-3"><LockKeyhole className="size-5 text-[#0d7a5f]" /><CardTitle className="mt-4 text-2xl font-semibold" data-testid="reset-password-title">Choose a new password</CardTitle></CardHeader><CardContent className="p-6 pt-2"><form onSubmit={submit} className="space-y-4" data-testid="reset-password-form"><label className="block space-y-2"><span className="text-xs font-semibold text-[#5c5f66]">Reset token</span><Input value={token} onChange={(event) => setToken(event.target.value)} required data-testid="reset-password-token-input" /></label><label className="block space-y-2"><span className="text-xs font-semibold text-[#5c5f66]">New password</span><Input type="password" minLength={8} value={password} onChange={(event) => setPassword(event.target.value)} required data-testid="reset-password-new-input" /></label><label className="block space-y-2"><span className="text-xs font-semibold text-[#5c5f66]">Confirm password</span><Input type="password" minLength={8} value={confirm} onChange={(event) => setConfirm(event.target.value)} required data-testid="reset-password-confirm-input" /></label><Button type="submit" disabled={pending} className="w-full bg-[#0d7a5f] text-white hover:bg-[#0a624c]" data-testid="reset-password-submit-button">{pending ? "Updating…" : "Update password"} <ArrowRight className="size-4" /></Button></form></CardContent></Card></div>;
}