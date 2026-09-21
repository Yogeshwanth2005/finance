import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Bell, LockKeyhole, ShieldCheck, UserRound } from "lucide-react";
import { Link } from "react-router-dom";
import { toast } from "sonner";

import AppShell from "@/components/AppShell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ApiError, apiGet, apiPost } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { languageOptions, useI18n } from "@/lib/i18n";
import { formatINR } from "@/lib/sampleData";
import type { ChangePasswordInput, ProfileResponse } from "@/lib/types";

function apiMessage(error: unknown, fallback: string) {
  if (error instanceof ApiError && typeof error.body === "object" && error.body && "detail" in error.body) return String((error.body as { detail: unknown }).detail);
  return fallback;
}

export default function Account() {
  const { user, updateSettings } = useAuth();
  const { t } = useI18n();
  const profile = useQuery({ queryKey: ["profile", "current"], queryFn: () => apiGet<ProfileResponse | null>("/profile/current"), retry: false });
  const [name, setName] = useState(user?.name ?? "");
  const [language, setLanguage] = useState(user?.preferred_language ?? "en");
  const [notifications, setNotifications] = useState(user?.notifications_enabled ?? true);
  const [privacy, setPrivacy] = useState(user?.privacy_mode ?? true);
  const [saving, setSaving] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [changingPassword, setChangingPassword] = useState(false);

  useEffect(() => {
    if (!user) return;
    setName(user.name);
    setLanguage(user.preferred_language);
    setNotifications(user.notifications_enabled);
    setPrivacy(user.privacy_mode);
  }, [user]);

  const save = async () => {
    setSaving(true);
    try {
      await updateSettings({ name, preferred_language: language, notifications_enabled: notifications, privacy_mode: privacy });
      toast.success("Settings saved");
    } catch (error) {
      toast.error(apiMessage(error, "Could not save settings"));
    } finally {
      setSaving(false);
    }
  };

  const changePassword = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (newPassword !== confirmPassword) { toast.error("New passwords do not match"); return; }
    setChangingPassword(true);
    try {
      const payload: ChangePasswordInput = { current_password: currentPassword, new_password: newPassword };
      await apiPost<{ message: string }>("/auth/change-password", payload);
      setCurrentPassword(""); setNewPassword(""); setConfirmPassword("");
      toast.success("Password updated");
    } catch (error) {
      toast.error(apiMessage(error, "Could not change password"));
    } finally {
      setChangingPassword(false);
    }
  };

  const analysis = profile.data?.analysis;

  return (
    <AppShell>
      <section className="mx-auto max-w-6xl px-4 pb-16 pt-10 sm:px-6 lg:px-8 lg:pt-14">
        <div className="border-b border-[#e4e1d8] pb-8" data-testid="account-page-header">
          <Badge variant="outline" className="border-[#d7ebe4] bg-[#eaf6f1] text-[#0d7a5f]" data-testid="account-page-badge"><UserRound className="size-3" /> {t("settings")}</Badge>
          <h1 className="mt-4 font-heading text-4xl font-bold tracking-[-0.04em]" data-testid="account-page-title">{t("accountTitle")}</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-[#5c5f66]" data-testid="account-page-description">{t("accountDescription")}</p>
        </div>

        <div className="mt-8 grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
          <Card className="border-[#e4e1d8] bg-white shadow-none" data-testid="account-personal-settings-card">
            <CardHeader className="p-6 pb-3"><CardTitle className="text-xl font-semibold">{t("personalSettings")}</CardTitle></CardHeader>
            <CardContent className="grid gap-5 p-6 pt-3 sm:grid-cols-2">
              <label className="space-y-2" data-testid="account-display-name-field"><span className="text-xs font-semibold text-[#5c5f66]">{t("displayName")}</span><Input value={name} onChange={(event) => setName(event.target.value)} data-testid="account-display-name-input" /></label>
              <label className="space-y-2" data-testid="account-email-field"><span className="text-xs font-semibold text-[#5c5f66]">{t("email")}</span><Input value={user?.email ?? ""} disabled data-testid="account-email-input" /></label>
              <label className="space-y-2" data-testid="account-language-field"><span className="text-xs font-semibold text-[#5c5f66]">{t("preferredLanguage")}</span><select value={language} onChange={(event) => setLanguage(event.target.value as typeof language)} className="h-8 w-full rounded-lg border border-[#e4e1d8] bg-white px-2.5 text-sm" data-testid="account-language-select">{languageOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
              <div className="space-y-3" data-testid="account-preference-toggles">
                <label className="flex cursor-pointer items-center gap-3 rounded-lg border border-[#e4e1d8] p-3"><input type="checkbox" checked={notifications} onChange={(event) => setNotifications(event.target.checked)} data-testid="account-notifications-toggle" /><Bell className="size-4 text-[#0d7a5f]" /><span className="text-xs font-semibold text-[#5c5f66]">{t("notifications")}</span></label>
                <label className="flex cursor-pointer items-center gap-3 rounded-lg border border-[#e4e1d8] p-3"><input type="checkbox" checked={privacy} onChange={(event) => setPrivacy(event.target.checked)} data-testid="account-privacy-toggle" /><ShieldCheck className="size-4 text-[#0d7a5f]" /><span className="text-xs font-semibold text-[#5c5f66]">{t("privacyMode")}</span></label>
              </div>
              <div className="sm:col-span-2"><Button onClick={save} disabled={saving || name.trim().length < 2} className="bg-[#0d7a5f] text-white hover:bg-[#0a624c]" data-testid="account-save-settings-button">{saving ? "Saving…" : t("saveSettings")} <ArrowRight className="size-4" /></Button></div>
            </CardContent>
          </Card>

          <Card className="border-[#e4e1d8] bg-[#17181c] text-white shadow-none" data-testid="account-financial-profile-card">
            <CardHeader className="p-6 pb-3"><div className="flex items-center justify-between"><CardTitle className="text-xl font-semibold text-white">{t("financialProfile")}</CardTitle><Badge className="bg-[#eaf6f1] text-[#0d7a5f]" data-testid="account-profile-status">{profile.data ? t("profileReady") : t("profilePending")}</Badge></div></CardHeader>
            <CardContent className="p-6 pt-3"><div className="grid grid-cols-2 gap-4 text-sm"><div><p className="text-[10px] uppercase tracking-wider text-white/45">{t("protectionScore")}</p><p className="mt-1 font-mono text-xl font-bold" data-testid="account-protection-score">{analysis ? `${analysis.protection_score}/100` : "—"}</p></div><div><p className="text-[10px] uppercase tracking-wider text-white/45">{t("investableNext")}</p><p className="mt-1 font-mono text-xl font-bold" data-testid="account-investable-surplus">{analysis ? formatINR(analysis.investable_surplus, true) : "—"}</p></div></div><Link to="/" className="mt-8 inline-flex items-center gap-2 rounded-lg bg-white px-4 py-2.5 text-sm font-semibold text-[#17181c]" data-testid="account-edit-financial-profile-link">{t("editProfile")} <ArrowRight className="size-4" /></Link></CardContent>
          </Card>
        </div>

        {analysis && <Card className="mt-6 border-[#e4e1d8] bg-white shadow-none" data-testid="account-kpi-summary-card"><CardHeader className="p-6 pb-3"><div className="flex items-end justify-between gap-4"><CardTitle className="text-xl font-semibold">{t("profileKpis")}</CardTitle><p className="max-w-sm text-right text-[11px] leading-4 text-[#8a8f99]">{t("kpiNeutralNote")}</p></div></CardHeader><CardContent className="grid grid-cols-2 gap-x-6 gap-y-5 p-6 pt-3 sm:grid-cols-4">{[
          ["emergencyCoverage", `${analysis.kpis.emergency_coverage_pct.toFixed(1)}%`, "account-kpi-emergency"],
          ["runwayMonths", `${analysis.kpis.runway_months.toFixed(1)} mo`, "account-kpi-runway"],
          ["termAdequacy", `${analysis.kpis.term_cover_adequacy_pct.toFixed(1)}%`, "account-kpi-term"],
          ["healthAdequacy", `${analysis.kpis.health_cover_adequacy_pct.toFixed(1)}%`, "account-kpi-health"],
          ["savingsRate", `${analysis.kpis.savings_rate_pct.toFixed(1)}%`, "account-kpi-savings"],
          ["debtToIncome", `${analysis.kpis.debt_to_income_pct.toFixed(1)}%`, "account-kpi-dti"],
          ["coverLiabilities", `${analysis.kpis.cover_to_liabilities_ratio.toFixed(2)}×`, "account-kpi-cover-liabilities"],
          ["liabilitiesIncome", `${analysis.kpis.liabilities_to_income_multiple.toFixed(2)}×`, "account-kpi-liabilities-income"],
        ].map(([label, value, testId]) => <div key={testId} data-testid={testId}><p className="text-[10px] font-bold uppercase tracking-[0.12em] text-[#8a8f99]">{t(label)}</p><p className="mt-2 font-mono text-xl font-bold text-[#17181c]">{value}</p></div>)}</CardContent></Card>}

        <Card className="mt-6 border-[#e4e1d8] bg-white shadow-none" data-testid="account-security-card">
          <CardHeader className="p-6 pb-3"><div className="flex items-center gap-3"><LockKeyhole className="size-5 text-[#0d7a5f]" /><CardTitle className="text-xl font-semibold">{t("security")}</CardTitle></div></CardHeader>
          <CardContent className="p-6 pt-3"><form onSubmit={changePassword} className="grid gap-4 sm:grid-cols-3" data-testid="account-change-password-form"><label className="space-y-2"><span className="text-xs font-semibold text-[#5c5f66]">{t("currentPassword")}</span><Input type="password" minLength={8} value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} required data-testid="account-current-password-input" /></label><label className="space-y-2"><span className="text-xs font-semibold text-[#5c5f66]">{t("newPassword")}</span><Input type="password" minLength={8} value={newPassword} onChange={(event) => setNewPassword(event.target.value)} required data-testid="account-new-password-input" /></label><label className="space-y-2"><span className="text-xs font-semibold text-[#5c5f66]">{t("confirmPassword")}</span><Input type="password" minLength={8} value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} required data-testid="account-confirm-password-input" /></label><div className="sm:col-span-3"><Button type="submit" variant="outline" disabled={changingPassword} data-testid="account-change-password-button">{changingPassword ? "Updating…" : t("changePassword")}</Button></div></form></CardContent>
        </Card>
      </section>
    </AppShell>
  );
}