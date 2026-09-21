import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Check, ChevronLeft, CircleHelp, LockKeyhole, RotateCcw } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

import AppShell from "@/components/AppShell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { apiGet, apiPost } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import type { ProfileInput, ProfileResponse, User } from "@/lib/types";

const initialDraft: ProfileInput = {
  full_name: "",
  dob: "1990-01-01",
  age: 35,
  city_tier: "tier_1",
  marital_status: "married",
  dependents: 2,
  spouse_full_name: "",
  spouse_dob: "",
  spouse_age: 32,
  spouse_employment_type: "not_working",
  employment_type: "mnc",
  annual_income: 1800000,
  spouse_income: 0,
  monthly_expenses: 60000,
  annual_bonus: 0,
  home_loan: 0,
  other_loans: 0,
  monthly_emi: 0,
  other_debts: 0,
  current_health_cover_lakh: 0,
  existing_term_cover_crore: 0,
  emergency_savings: 0,
  current_investments: 0,
};

const steps = [
  { number: 1, label: "Family", title: "Who are we protecting?", description: "Start with the household details that shape your coverage needs." },
  { number: 2, label: "Income", title: "Map your earning engine", description: "A clear picture of income and monthly commitments makes the advice useful." },
  { number: 3, label: "Liabilities", title: "Make debt visible", description: "Your cover should protect the family from inheriting outstanding loans." },
  { number: 4, label: "Protection", title: "What is already in place?", description: "Finish with existing cover, savings and investments so we only suggest the gap." },
];

function Field({ label, hint, children, testId }: { label: string; hint?: string; children: ReactNode; testId: string }) {
  return (
    <label className="space-y-2" data-testid={`${testId}-field`}>
      <span className="block text-xs font-semibold text-[#5c5f66]">{label}</span>
      {children}
      {hint && <span className="block text-[11px] leading-4 text-[#8a8f99]">{hint}</span>}
    </label>
  );
}

export default function Home() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const [step, setStep] = useState(1);
  const [draft, setDraft] = useState<ProfileInput>(() => ({ ...initialDraft, full_name: user?.name ?? "" }));
  const hydrated = useRef(false);
  const currentProfile = useQuery({ queryKey: ["profile", "current"], queryFn: () => apiGet<ProfileResponse | null>("/profile/current"), retry: false });

  useEffect(() => {
    if (hydrated.current || !currentProfile.isSuccess) return;
    if (currentProfile.data?.profile) setDraft(currentProfile.data.profile);
    hydrated.current = true;
  }, [currentProfile.data, currentProfile.isSuccess]);
  const mutation = useMutation({
    mutationFn: (payload: ProfileInput) => apiPost<ProfileResponse>("/profile", payload),
    onSuccess: (response) => {
      queryClient.setQueryData(["profile"], response);
      queryClient.setQueryData(["profile", "current"], response);
      queryClient.setQueryData<User | null>(["auth", "me"], (current) => current ? { ...current, profile_complete: true } : current);
      toast.success("Your protection map is ready");
      navigate("/dashboard");
    },
    onError: () => toast.error("We could not save the profile. Please try again."),
  });

  const update = <K extends keyof ProfileInput>(key: K, value: ProfileInput[K]) => {
    setDraft((current) => ({ ...current, [key]: value }));
  };

  const updateMaritalStatus = (value: ProfileInput["marital_status"]) => {
    setDraft((current) => value === "single" ? {
      ...current,
      marital_status: value,
      spouse_full_name: "",
      spouse_dob: "",
      spouse_age: 0,
      spouse_employment_type: "not_working",
      spouse_income: 0,
    } : { ...current, marital_status: value });
  };

  const next = () => {
    if (step < steps.length) setStep((current) => current + 1);
    else mutation.mutate(draft);
  };

  const reset = () => {
    setDraft({ ...initialDraft, full_name: user?.name ?? "" });
    setStep(1);
    toast.success("Draft cleared");
  };

  return (
    <AppShell>
      <section className="mx-auto max-w-7xl px-4 pb-12 pt-10 sm:px-6 lg:px-8 lg:pt-16">
        <div className="grid items-end gap-8 lg:grid-cols-[1.25fr_0.75fr]">
          <div data-testid="profile-wizard-intro">
            <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-[#d7ebe4] bg-[#eaf6f1] px-3 py-1.5 text-[10px] font-bold uppercase tracking-[0.16em] text-[#0d7a5f]">
              <span className="size-1.5 rounded-full bg-[#0d7a5f]" /> {t("profileEyebrow")}
            </div>
            <h1 className="max-w-3xl font-heading text-4xl font-bold leading-[1.08] tracking-[-0.04em] text-[#17181c] sm:text-5xl lg:text-6xl" data-testid="profile-wizard-heading">
              {t("profileTitle")}
            </h1>
            <p className="mt-5 max-w-xl text-base leading-7 text-[#5c5f66]" data-testid="profile-wizard-description">
              {t("profileDescription")}
            </p>
          </div>
          <Card className="border-[#e4e1d8] bg-[#17181c] text-white shadow-[0_18px_40px_rgba(23,24,28,0.12)]" data-testid="profile-wizard-trust-card">
            <CardHeader className="p-6 pb-3">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-bold uppercase tracking-[0.18em] text-[#a8d9c8]">Built for India</span>
                <LockKeyhole className="size-4 text-[#a8d9c8]" />
              </div>
              <CardTitle className="mt-4 text-xl font-semibold text-white" data-testid="profile-wizard-trust-title">No product pushing. Just the gap.</CardTitle>
            </CardHeader>
            <CardContent className="p-6 pt-2 text-sm leading-6 text-white/65" data-testid="profile-wizard-trust-copy">
              Rule-based estimates show their working, so you can question every number before speaking with an advisor.
            </CardContent>
          </Card>
        </div>

        <div className="mt-12 grid gap-8 lg:grid-cols-[0.75fr_1.25fr] lg:gap-12">
          <aside className="lg:pt-4" data-testid="profile-wizard-progress">
            <p className="mb-5 text-[10px] font-bold uppercase tracking-[0.18em] text-[#8a8f99]">Your profile / 04 steps</p>
            <div className="space-y-2">
              {steps.map((item) => (
                <div key={item.number} className={`flex items-start gap-3 rounded-xl px-3 py-3 ${step === item.number ? "bg-white shadow-[0_8px_24px_rgba(23,24,28,0.05)]" : "opacity-55"}`} data-testid={`profile-wizard-step-${item.number}`}>
                  <span className={`flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-bold ${step > item.number ? "bg-[#d7ebe4] text-[#0d7a5f]" : step === item.number ? "bg-[#0d7a5f] text-white" : "bg-[#e4e1d8] text-[#5c5f66]"}`}>
                    {step > item.number ? <Check className="size-3.5" /> : item.number}
                  </span>
                  <div>
                    <p className="text-sm font-semibold text-[#17181c]">{t(item.label.toLowerCase())}</p>
                    <p className="mt-0.5 text-xs leading-5 text-[#8a8f99]">{t(`step${item.number}Title`)}</p>
                  </div>
                </div>
              ))}
            </div>
            <Button variant="ghost" size="sm" className="mt-6 text-[#5c5f66]" onClick={reset} data-testid="profile-wizard-reset-button">
              <RotateCcw className="size-3.5" /> {t("startOver")}
            </Button>
          </aside>

          <Card className="border-[#e4e1d8] bg-white shadow-[0_18px_45px_rgba(23,24,28,0.06)]" data-testid="profile-wizard-step-container">
            <CardHeader className="border-b border-[#f1efe9] p-6 pb-5 sm:p-8 sm:pb-6">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-[#0d7a5f]">Step 0{step}</p>
                  <CardTitle className="mt-2 text-2xl font-semibold tracking-tight text-[#17181c]" data-testid="profile-wizard-step-title">{t(`step${step}Title`)}</CardTitle>
                  <p className="mt-2 max-w-lg text-sm leading-6 text-[#8a8f99]" data-testid="profile-wizard-step-description">{steps[step - 1].description}</p>
                </div>
                <span className="hidden size-12 items-center justify-center rounded-2xl bg-[#f1efe9] text-[#0d7a5f] sm:flex"><CircleHelp className="size-5" /></span>
              </div>
            </CardHeader>
            <CardContent className="p-6 sm:p-8">
              {step === 1 && (
                <div className="grid gap-5 sm:grid-cols-2" data-testid="profile-wizard-family-fields">
                  <Field label={t("fullName")} testId="profile-full-name">
                    <Input value={draft.full_name} onChange={(event) => update("full_name", event.target.value)} placeholder="e.g. Rohan Sharma" data-testid="profile-full-name-input" />
                  </Field>
                  <Field label={t("dateOfBirth")} testId="profile-dob">
                    <Input type="date" value={draft.dob} onChange={(event) => update("dob", event.target.value)} data-testid="profile-dob-input" />
                  </Field>
                  <Field label={t("yourAge")} hint="Used to keep premium estimates realistic" testId="profile-age">
                    <Input type="number" min="18" max="75" value={draft.age} onChange={(event) => update("age", Number(event.target.value))} data-testid="profile-age-input" />
                  </Field>
                  <Field label={t("cityTier")} testId="profile-city-tier">
                    <select value={draft.city_tier} onChange={(event) => update("city_tier", event.target.value as ProfileInput["city_tier"])} className="h-8 w-full rounded-lg border border-[#e4e1d8] bg-white px-2.5 text-sm outline-none focus:border-[#0d7a5f]" data-testid="profile-city-tier-select">
                      <option value="tier_1">Tier 1 — Mumbai, Bengaluru, Delhi</option><option value="tier_2">Tier 2 — Pune, Jaipur, Kochi</option><option value="tier_3">Tier 3 — Other cities</option>
                    </select>
                  </Field>
                  <Field label={t("maritalStatus")} testId="profile-marital-status">
                    <select value={draft.marital_status} onChange={(event) => updateMaritalStatus(event.target.value as ProfileInput["marital_status"])} className="h-8 w-full rounded-lg border border-[#e4e1d8] bg-white px-2.5 text-sm outline-none focus:border-[#0d7a5f]" data-testid="profile-marital-status-select">
                      <option value="married">{t("married")}</option><option value="single">{t("single")}</option>
                    </select>
                  </Field>
                  <Field label={t("dependents")} testId="profile-dependents">
                    <Input type="number" min="0" max="12" value={draft.dependents} onChange={(event) => update("dependents", Number(event.target.value))} data-testid="profile-dependents-input" />
                  </Field>
                  {draft.marital_status === "married" && <Field label={t("spouseAge")} testId="profile-spouse-age">
                    <Input type="number" min="0" max="75" value={draft.spouse_age} onChange={(event) => update("spouse_age", Number(event.target.value))} data-testid="profile-spouse-age-input" />
                  </Field>}
                  {draft.marital_status === "married" && <><Field label={t("spouseName")} testId="profile-spouse-name"><Input value={draft.spouse_full_name} onChange={(event) => update("spouse_full_name", event.target.value)} placeholder="Partner's full name" data-testid="profile-spouse-name-input" /></Field><Field label={t("spouseDob")} testId="profile-spouse-dob"><Input type="date" value={draft.spouse_dob} onChange={(event) => update("spouse_dob", event.target.value)} data-testid="profile-spouse-dob-input" /></Field></>}
                </div>
              )}
              {step === 2 && (
                <div className="grid gap-5 sm:grid-cols-2" data-testid="profile-wizard-income-fields">
                  <Field label={t("employment")} testId="profile-employment">
                    <select value={draft.employment_type} onChange={(event) => update("employment_type", event.target.value as ProfileInput["employment_type"])} className="h-8 w-full rounded-lg border border-[#e4e1d8] bg-white px-2.5 text-sm outline-none focus:border-[#0d7a5f]" data-testid="profile-employment-select">
                      <option value="mnc">MNC / salaried</option><option value="business">Business / self-employed</option><option value="freelance">Freelance / variable</option>
                    </select>
                  </Field>
                  <Field label={t("annualIncome")} testId="profile-annual-income">
                    <Input type="number" min="1" value={draft.annual_income} onChange={(event) => update("annual_income", Number(event.target.value))} data-testid="profile-annual-income-input" />
                  </Field>
                  {draft.marital_status === "married" && <Field label={t("spouseIncome")} testId="profile-spouse-income">
                    <Input type="number" min="0" value={draft.spouse_income} onChange={(event) => update("spouse_income", Number(event.target.value))} data-testid="profile-spouse-income-input" />
                  </Field>}
                  {draft.marital_status === "married" && <Field label={t("spouseEmployment")} testId="profile-spouse-employment"><select value={draft.spouse_employment_type} onChange={(event) => update("spouse_employment_type", event.target.value as ProfileInput["spouse_employment_type"])} className="h-8 w-full rounded-lg border border-[#e4e1d8] bg-white px-2.5 text-sm outline-none focus:border-[#0d7a5f]" data-testid="profile-spouse-employment-select"><option value="not_working">Not currently working</option><option value="mnc">MNC / salaried</option><option value="business">Business / self-employed</option><option value="freelance">Freelance / variable</option></select></Field>}
                  <Field label={t("monthlyExpenses")} testId="profile-monthly-expenses">
                    <Input type="number" min="1" value={draft.monthly_expenses} onChange={(event) => update("monthly_expenses", Number(event.target.value))} data-testid="profile-monthly-expenses-input" />
                  </Field>
                  <Field label={t("annualBonus")} hint="Enter 0 if income is fixed" testId="profile-annual-bonus">
                    <Input type="number" min="0" value={draft.annual_bonus} onChange={(event) => update("annual_bonus", Number(event.target.value))} data-testid="profile-annual-bonus-input" />
                  </Field>
                </div>
              )}
              {step === 3 && (
                <div className="grid gap-5 sm:grid-cols-2" data-testid="profile-wizard-liability-fields">
                  <Field label={t("homeLoan")} testId="profile-home-loan"><Input type="number" min="0" value={draft.home_loan} onChange={(event) => update("home_loan", Number(event.target.value))} data-testid="profile-home-loan-input" /></Field>
                  <Field label={t("otherLoans")} testId="profile-other-loans"><Input type="number" min="0" value={draft.other_loans} onChange={(event) => update("other_loans", Number(event.target.value))} data-testid="profile-other-loans-input" /></Field>
                  <Field label={t("monthlyEmi")} testId="profile-monthly-emi"><Input type="number" min="0" value={draft.monthly_emi} onChange={(event) => update("monthly_emi", Number(event.target.value))} data-testid="profile-monthly-emi-input" /></Field>
                  <Field label={t("otherDebts")} testId="profile-other-debts"><Input type="number" min="0" value={draft.other_debts} onChange={(event) => update("other_debts", Number(event.target.value))} data-testid="profile-other-debts-input" /></Field>
                </div>
              )}
              {step === 4 && (
                <div className="grid gap-5 sm:grid-cols-2" data-testid="profile-wizard-protection-fields">
                  <Field label={t("healthCover")} testId="profile-health-cover"><Input type="number" min="0" value={draft.current_health_cover_lakh} onChange={(event) => update("current_health_cover_lakh", Number(event.target.value))} data-testid="profile-health-cover-input" /></Field>
                  <Field label={t("termCover")} testId="profile-term-cover"><Input type="number" min="0" step="0.1" value={draft.existing_term_cover_crore} onChange={(event) => update("existing_term_cover_crore", Number(event.target.value))} data-testid="profile-term-cover-input" /></Field>
                  <Field label={t("emergencySavings")} hint="Savings you can access without selling investments" testId="profile-emergency-savings"><Input type="number" min="0" value={draft.emergency_savings} onChange={(event) => update("emergency_savings", Number(event.target.value))} data-testid="profile-emergency-savings-input" /></Field>
                  <Field label={t("investments")} testId="profile-investments"><Input type="number" min="0" value={draft.current_investments} onChange={(event) => update("current_investments", Number(event.target.value))} data-testid="profile-investments-input" /></Field>
                </div>
              )}

              <div className="mt-8 flex items-center justify-between border-t border-[#f1efe9] pt-5">
                <Button variant="ghost" onClick={() => setStep((current) => Math.max(1, current - 1))} disabled={step === 1 || mutation.isPending} data-testid="profile-wizard-back-button"><ChevronLeft className="size-4" /> {t("back")}</Button>
                <Button onClick={next} disabled={mutation.isPending || (step === 1 && draft.full_name.trim().length < 2)} className="bg-[#0d7a5f] text-white hover:bg-[#0a624c]" data-testid={step === 4 ? "wizard-submit-button" : `wizard-step-${step}-next-button`}>
                  {mutation.isPending ? "Building map…" : step === 4 ? t("buildMap") : t("continue")} <ArrowRight className="size-4" />
                </Button>
              </div>
              <p className="mt-4 text-center text-[11px] text-[#8a8f99]" data-testid="profile-wizard-privacy-note">Your information stays in this private demo workspace.</p>
            </CardContent>
          </Card>
        </div>
      </section>
    </AppShell>
  );
}