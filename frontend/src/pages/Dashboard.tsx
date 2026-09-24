import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight, Banknote, ChevronRight, CircleAlert, PiggyBank, ShieldCheck, WalletCards } from "lucide-react";
import { Link, Navigate } from "react-router-dom";

import AppShell from "@/components/AppShell";
import FundExplorer from "@/components/FundExplorer";
import GoalCheckLines from "@/components/GoalCheckLines";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiGet } from "@/lib/api";
import { formatINR, SAMPLE_PROFILE_RESPONSE } from "@/lib/sampleData";
import type { Plan, ProfileResponse } from "@/lib/types";
import { useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";

function Metric({ label, value, note, icon: Icon, testId }: { label: string; value: string; note: string; icon: typeof ShieldCheck; testId: string }) {
  return (
    <Card className="border-[#e4e1d8] bg-white shadow-none transition-transform hover:-translate-y-0.5" data-testid={testId}>
      <CardContent className="p-5">
        <div className="flex items-center justify-between text-[#8a8f99]"><span className="text-[10px] font-bold uppercase tracking-[0.16em]" data-testid={`${testId}-label`}>{label}</span><Icon className="size-4" /></div>
        <p className="mt-5 font-mono text-2xl font-bold tabular-nums tracking-tight text-[#17181c]" data-testid={`${testId}-value`}>{value}</p>
        <p className="mt-2 text-xs leading-5 text-[#8a8f99]" data-testid={`${testId}-note`}>{note}</p>
      </CardContent>
    </Card>
  );
}

function KpiMetric({ label, value, rupeeDetail, formula, benchmark, testId }: { label: string; value: string; rupeeDetail: string; formula: string; benchmark?: string; testId: string }) {
  return <Card className="border-[#e4e1d8] bg-white shadow-none" data-testid={testId}><CardContent className="p-5"><p className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#8a8f99]" data-testid={`${testId}-label`}>{label}</p><p className="mt-4 font-mono text-2xl font-bold tabular-nums text-[#17181c]" data-testid={`${testId}-value`}>{value}</p><p className="mt-2 text-xs font-semibold text-[#5c5f66]" data-testid={`${testId}-rupee-detail`}>{rupeeDetail}</p><p className="mt-4 border-t border-[#f1efe9] pt-3 font-mono text-[10px] leading-4 text-[#8a8f99]" data-testid={`${testId}-formula`}>{formula}</p>{benchmark && <p className="mt-2 text-[10px] leading-4 text-[#a16207]" data-testid={`${testId}-benchmark`}>{benchmark}</p>}</CardContent></Card>;
}

export default function Dashboard() {
  const { user } = useAuth();
  const { t } = useI18n();
  const query = useQuery({ queryKey: ["profile"], queryFn: () => apiGet<ProfileResponse>("/profile"), retry: false });
  const plansQuery = useQuery({ queryKey: ["plans"], queryFn: () => apiGet<Plan[]>("/plans"), retry: false });
  if (user && user.role !== "admin" && !user.profile_complete) return <Navigate to="/" replace />;
  const response = query.data ?? SAMPLE_PROFILE_RESPONSE;
  const { profile, analysis } = response;
  const isSample = !query.data;
  const scoreDegrees = Math.max(0, Math.min(100, analysis.protection_score)) * 3.6;
  const annualCashflow = analysis.annual_surplus_before_protection;
  const uncoveredLiabilities = Math.max(0, analysis.total_liabilities - (profile.existing_term_cover_crore * 10_000_000));
  const publishedPlanCount = plansQuery.data?.length ?? 0;
  const emergencyGapOpen = analysis.emergency_gap > 0;
  const insuranceExceedsSurplus = analysis.annual_insurance_budget > analysis.annual_surplus_before_protection;
  const monthlyInvestable = analysis.investable_surplus / 12;
  const allocationBuckets = [
    { name: "Large cap", slug: "large-cap", pct: analysis.equity_split.large_pct, color: "bg-[#0d7a5f]" },
    { name: "Mid cap", slug: "mid-cap", pct: analysis.equity_split.mid_pct, color: "bg-[#10b981]" },
    { name: "Small cap", slug: "small-cap", pct: analysis.equity_split.small_pct, color: "bg-[#6ee7b7]" },
    { name: "Debt", slug: "debt", pct: analysis.allocation.debt_pct, color: "bg-[#2563eb]" },
    { name: "Gold", slug: "gold", pct: analysis.allocation.gold_pct, color: "bg-[#d97706]" },
  ];
  const categories = [
    { label: "Living costs", value: analysis.annual_expenses, color: "bg-[#c8c4b7]" },
    { label: "EMIs & debt", value: analysis.annual_emi, color: "bg-[#d97706]" },
    { label: "Protection budget", value: analysis.annual_insurance_budget, color: "bg-[#0d7a5f]" },
    { label: "Investable surplus", value: analysis.investable_surplus, color: "bg-[#2563eb]" },
  ];

  return (
    <AppShell>
      <section className="mx-auto max-w-7xl px-4 pb-12 pt-10 sm:px-6 lg:px-8 lg:pt-14">
        <div className="flex flex-col justify-between gap-6 border-b border-[#e4e1d8] pb-8 sm:flex-row sm:items-end">
          <div data-testid="dashboard-header-copy">
            <div className="mb-4 flex items-center gap-2"><Badge variant="outline" className="border-[#d7ebe4] bg-[#eaf6f1] text-[#0d7a5f]" data-testid="dashboard-status-badge">{isSample ? "Sample benchmark" : "Profile analysed"}</Badge><span className="text-xs text-[#8a8f99]" data-testid="dashboard-last-updated">India / INR · rule-based view</span></div>
            <h1 className="font-heading text-4xl font-bold tracking-[-0.04em] text-[#17181c] sm:text-5xl" data-testid="dashboard-heading">{t("greeting")}, {profile.full_name || "there"}.</h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-[#5c5f66]" data-testid="dashboard-subheading">{t("dashboardDescription")}</p>
          </div>
          <Link to="/insurance" className="inline-flex items-center justify-center gap-2 rounded-lg bg-[#17181c] px-4 py-2.5 text-sm font-semibold text-white transition-transform hover:-translate-y-0.5" data-testid="dashboard-review-insurance-link">{t("reviewInsurance")} <ArrowUpRight className="size-4" /></Link>
        </div>

        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Metric label={t("protectionScore")} value={`${analysis.protection_score}/100`} note={analysis.score_label} icon={ShieldCheck} testId="dashboard-protection-score-card" />
          <Metric label={t("termGap")} value={`₹${analysis.term_gap_crore.toFixed(2)} Cr`} note={`Recommended ${analysis.recommended_term_cover_crore.toFixed(2)} Cr`} icon={WalletCards} testId="dashboard-term-gap-metric" />
          <Metric label={t("healthGap")} value={`₹${analysis.health_gap_lakh.toFixed(1)} L`} note={`Floater target ${analysis.recommended_health_cover_lakh} L`} icon={CircleAlert} testId="dashboard-health-gap-metric" />
          <Metric label={t("investableNext")} value={formatINR(analysis.investable_surplus, true)} note="After illustrative cover budget" icon={PiggyBank} testId="dashboard-investable-surplus-card" />
        </div>

        <div className="mt-8 grid gap-6 lg:grid-cols-[0.8fr_1.2fr]">
          <Card className="border-[#e4e1d8] bg-[#17181c] text-white shadow-none" data-testid="dashboard-protection-score-panel">
            <CardContent className="flex min-h-[290px] flex-col justify-between p-6 sm:p-8">
              <div className="flex items-start justify-between"><div><p className="text-[10px] font-bold uppercase tracking-[0.18em] text-[#a8d9c8]" data-testid="dashboard-score-label">Family safety snapshot</p><h2 className="mt-3 font-heading text-2xl font-semibold" data-testid="dashboard-score-title">Protection before performance.</h2></div><ShieldCheck className="size-5 text-[#a8d9c8]" /></div>
              <div className="mt-8 flex items-center gap-6"><div className="relative flex size-32 items-center justify-center rounded-full" style={{ background: `conic-gradient(#10b981 ${scoreDegrees}deg, #323840 ${scoreDegrees}deg)` }} data-testid="dashboard-score-ring"><div className="flex size-24 flex-col items-center justify-center rounded-full bg-[#17181c]"><span className="font-mono text-3xl font-bold" data-testid="dashboard-score-number">{analysis.protection_score}</span><span className="text-[10px] uppercase tracking-widest text-white/45">out of 100</span></div></div><div className="max-w-[180px] text-sm leading-6 text-white/60" data-testid="dashboard-score-explanation">Your score rises when cover, liquidity and debt protection work together — not just when savings are high.</div></div>
              <div className="mt-8 flex items-center gap-2 text-xs text-white/50" data-testid="dashboard-score-footnote"><span className="size-2 rounded-full bg-[#10b981]" /> Calculated from 3 protection pillars</div>
            </CardContent>
          </Card>

          <Card className="border-[#e4e1d8] bg-white shadow-none" data-testid="dashboard-cashflow-card">
            <CardHeader className="p-6 pb-3 sm:p-8 sm:pb-4"><div className="flex items-center justify-between"><div><p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#8a8f99]" data-testid="dashboard-cashflow-eyebrow">Annual cashflow</p><CardTitle className="mt-2 text-2xl font-semibold text-[#17181c]" data-testid="dashboard-cashflow-title">Where every rupee goes</CardTitle></div><Banknote className="size-5 text-[#0d7a5f]" /></div></CardHeader>
            <CardContent className="p-6 pt-3 sm:p-8 sm:pt-4"><div className="flex items-end justify-between border-b border-[#f1efe9] pb-5"><div><p className="text-xs text-[#8a8f99]">Household income</p><p className="mt-1 font-mono text-2xl font-bold text-[#17181c]" data-testid="dashboard-household-income">{formatINR(analysis.annual_household_income, true)}<span className="ml-1 text-xs font-sans font-normal text-[#8a8f99]">/ year</span></p></div><Badge variant="secondary" className="bg-[#eaf6f1] text-[#0d7a5f]" data-testid="dashboard-cashflow-surplus-badge">{formatINR(annualCashflow, true)} before protection</Badge></div><div className="mt-6 space-y-4">{categories.map((item) => <div key={item.label} data-testid={`dashboard-cashflow-${item.label.toLowerCase().replaceAll(" ", "-")}`}><div className="mb-2 flex justify-between text-xs"><span className="flex items-center gap-2 text-[#5c5f66]"><span className={`size-2 rounded-full ${item.color}`} />{item.label}</span><span className="font-mono font-semibold text-[#17181c]">{formatINR(item.value, true)}</span></div><div className="h-2 overflow-hidden rounded-full bg-[#f1efe9]"><div className={`h-full rounded-full ${item.color}`} style={{ width: `${Math.max(6, Math.min(100, (item.value / Math.max(annualCashflow, 1)) * 100))}%` }} /></div></div>)}</div></CardContent>
          </Card>
        </div>

        <section className="mt-6" data-testid="dashboard-next-steps-section">
          <div><p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#8a8f99]">What to do next</p><h2 className="mt-2 font-heading text-2xl font-semibold text-[#17181c]" data-testid="dashboard-next-steps-title">Protect, then invest — in that order.</h2></div>
          <div className="mt-5 grid gap-6 lg:grid-cols-2">
            <Card className="border-[#e4e1d8] bg-[#fff9ef] shadow-none" data-testid="dashboard-investment-card">
              <CardHeader className="p-6 pb-2"><p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#a16207]" data-testid="investment-eyebrow">Surplus direction</p><CardTitle className="mt-2 text-xl font-semibold text-[#17181c]" data-testid="investment-title">Invest what protection leaves behind.</CardTitle></CardHeader>
              <CardContent className="p-6 pt-3">
                {emergencyGapOpen ? (
                  <div data-testid="investment-emergency-blocker">
                    <p className="text-sm leading-6 text-[#5c5f66]">Build your emergency fund before investing — it comes before insurance premiums in the priority order.</p>
                    <p className="mt-4 font-mono text-2xl font-bold text-[#17181c]" data-testid="investment-emergency-gap-amount">{formatINR(analysis.emergency_gap, true)}</p>
                    <p className="mt-1 text-xs text-[#8a8f99]">more needed to reach a 6-month fund ({analysis.emergency_months} months covered today)</p>
                  </div>
                ) : insuranceExceedsSurplus || analysis.investable_surplus <= 0 ? (
                  <div data-testid="investment-insurance-blocker">
                    <p className="text-sm leading-6 text-[#5c5f66]">Your recommended insurance premium exceeds what's left after expenses and EMIs — close that gap before investing.</p>
                    <div className="mt-4 flex items-center justify-between text-xs"><span className="text-[#8a8f99]">Premium needed</span><span className="font-mono font-semibold text-[#17181c]" data-testid="investment-premium-needed">{formatINR(analysis.annual_insurance_budget, true)}/yr</span></div>
                    <div className="mt-2 flex items-center justify-between text-xs"><span className="text-[#8a8f99]">Surplus available</span><span className="font-mono font-semibold text-[#17181c]" data-testid="investment-surplus-available">{formatINR(analysis.annual_surplus_before_protection, true)}/yr</span></div>
                  </div>
                ) : (
                  <div data-testid="investment-sip-plan">
                    <p className="text-sm leading-6 text-[#5c5f66]">After your protection budget, here's how a glide-path split of your monthly surplus could look:</p>
                    <p className="mt-4 font-mono text-2xl font-bold text-[#17181c]" data-testid="investment-monthly-amount">{formatINR(monthlyInvestable, true)}<span className="ml-1 text-xs font-sans font-normal text-[#8a8f99]">/ month</span></p>
                    <div className="mt-5 space-y-3 text-xs">{allocationBuckets.map((bucket) => <div key={bucket.name} className="flex items-center gap-3" data-testid={`investment-allocation-${bucket.slug}`}><span className={`size-2 rounded-full ${bucket.color}`} /><span className="flex-1 font-semibold text-[#17181c]">{bucket.name}</span><span className="font-mono text-[#8a8f99]" data-testid={`investment-allocation-${bucket.slug}-pct`}>{bucket.pct}%</span><span className="w-20 text-right font-mono font-bold text-[#5c5f66]">{formatINR(monthlyInvestable * bucket.pct / 100, true)}</span></div>)}</div>
                    <p className="mt-4 text-[11px] leading-5 text-[#8a8f99]" data-testid="investment-allocation-basis">Age {profile.age} · {profile.risk_tolerance} risk · {profile.investment_horizon_years}-year horizon</p>
                    <GoalCheckLines goal={analysis.goal_check} />
                  </div>
                )}
                <p className="mt-5 border-t border-[#eddcbb] pt-4 text-[11px] leading-5 text-[#8a6b3d]" data-testid="investment-disclaimer">Illustrative only — a rule-of-thumb glide path (equity ≈ 100 − age, scaled by risk tolerance, trimmed for horizons of 3 years or less), split across large, mid and small cap by risk tolerance and checked against assumed long-run returns. Not personalised advice; past performance is not indicative of future returns.</p>
              </CardContent>
            </Card>
            <Card className="border-[#e4e1d8] bg-white shadow-none" data-testid="dashboard-insurance-status-card">
              <CardHeader className="p-6 pb-2"><div className="flex items-center justify-between"><div><p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#8a8f99]" data-testid="insurance-status-eyebrow">Protection coverage</p><CardTitle className="mt-2 text-xl font-semibold text-[#17181c]" data-testid="insurance-status-title">Where your cover stands.</CardTitle></div><ShieldCheck className="size-5 text-[#0d7a5f]" /></div></CardHeader>
              <CardContent className="space-y-4 p-6 pt-3">
                <div className="flex items-center justify-between border-b border-[#f1efe9] pb-3" data-testid="insurance-status-term-row"><div><p className="text-xs font-semibold text-[#17181c]">Term cover</p><p className="mt-1 text-[11px] text-[#8a8f99]">{profile.existing_term_cover_crore.toFixed(2)} Cr held → {analysis.recommended_term_cover_crore.toFixed(2)} Cr recommended</p></div><span className="font-mono text-sm font-bold text-[#d97706]" data-testid="insurance-status-term-gap">{analysis.term_gap_crore.toFixed(2)} Cr gap</span></div>
                <div className="flex items-center justify-between border-b border-[#f1efe9] pb-3" data-testid="insurance-status-health-row"><div><p className="text-xs font-semibold text-[#17181c]">Health cover</p><p className="mt-1 text-[11px] text-[#8a8f99]">{profile.current_health_cover_lakh} L held → {analysis.recommended_health_cover_lakh} L recommended</p></div><span className="font-mono text-sm font-bold text-[#d97706]" data-testid="insurance-status-health-gap">{analysis.health_gap_lakh} L gap</span></div>
                <div className="flex items-center justify-between" data-testid="insurance-status-budget-row"><p className="text-xs font-semibold text-[#17181c]">Annual premium to close both gaps</p><span className="font-mono text-sm font-bold text-[#17181c]" data-testid="insurance-status-budget">{formatINR(analysis.annual_insurance_budget, true)}/yr</span></div>
                <Link to="/insurance" className="mt-2 flex items-center justify-between rounded-lg border border-[#e4e1d8] px-4 py-3 text-xs font-semibold text-[#0d7a5f] transition-colors hover:border-[#0d7a5f] hover:bg-[#f8fbf9]" data-testid="insurance-status-plans-link">{publishedPlanCount > 0 ? `Compare ${publishedPlanCount} published plan${publishedPlanCount === 1 ? "" : "s"}` : "No plans published yet — browse insurance"}<ChevronRight className="size-3.5" /></Link>
              </CardContent>
            </Card>
          </div>
        </section>

        <FundExplorer investmentBlocked={emergencyGapOpen || insuranceExceedsSurplus || analysis.investable_surplus <= 0} />

        <section className="mt-10" data-testid="dashboard-profile-kpi-section">
          <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-end"><div><p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#0d7a5f]">Financial profile</p><h2 className="mt-2 font-heading text-2xl font-semibold text-[#17181c]" data-testid="dashboard-profile-kpi-title">{t("profileKpis")}</h2></div><p className="max-w-md text-xs leading-5 text-[#8a8f99]" data-testid="dashboard-profile-kpi-neutral-note">{t("kpiNeutralNote")}</p></div>
          <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <KpiMetric label={t("emergencyCoverage")} value={`${analysis.kpis.emergency_coverage_pct.toFixed(1)}%`} rupeeDetail={`${formatINR(analysis.emergency_gap)} gap to 6-month fund`} formula="emergency savings ÷ (6 × monthly expenses) × 100" testId="kpi-emergency-coverage" />
            <KpiMetric label={t("runwayMonths")} value={`${analysis.kpis.runway_months.toFixed(1)} months`} rupeeDetail={`${formatINR(profile.emergency_savings)} liquid savings`} formula="emergency savings ÷ monthly expenses" testId="kpi-runway-months" />
            <KpiMetric label={t("termAdequacy")} value={`${analysis.kpis.term_cover_adequacy_pct.toFixed(1)}%`} rupeeDetail={`₹${analysis.term_gap_crore.toFixed(2)} Cr cover gap`} formula="existing term cover ÷ recommended term cover × 100" testId="kpi-term-adequacy" />
            <KpiMetric label={t("healthAdequacy")} value={`${analysis.kpis.health_cover_adequacy_pct.toFixed(1)}%`} rupeeDetail={`₹${analysis.health_gap_lakh.toFixed(1)} L cover gap`} formula="existing health cover ÷ recommended health cover × 100" testId="kpi-health-adequacy" />
            <KpiMetric label={t("savingsRate")} value={`${analysis.kpis.savings_rate_pct.toFixed(1)}%`} rupeeDetail={`${formatINR(analysis.annual_surplus_before_protection)} annual cash surplus`} formula="(income − expenses − EMI) ÷ income × 100" testId="kpi-savings-rate" />
            <KpiMetric label={t("debtToIncome")} value={`${analysis.kpis.debt_to_income_pct.toFixed(1)}%`} rupeeDetail={`${formatINR(profile.monthly_emi)} monthly EMI`} formula="monthly EMI ÷ monthly household income × 100" benchmark={t("illustrativeThreshold")} testId="kpi-debt-to-income" />
            <KpiMetric label={t("coverLiabilities")} value={`${analysis.kpis.cover_to_liabilities_ratio.toFixed(2)}×`} rupeeDetail={`${formatINR(uncoveredLiabilities)} liabilities beyond cover`} formula="existing term cover ÷ total liabilities" testId="kpi-cover-liabilities" />
            <KpiMetric label={t("liabilitiesIncome")} value={`${analysis.kpis.liabilities_to_income_multiple.toFixed(2)}×`} rupeeDetail={`${formatINR(analysis.total_liabilities)} total liabilities`} formula="total liabilities ÷ annual household income" testId="kpi-liabilities-income" />
          </div>
        </section>

        <Card className="mt-6 border-[#eadcc8] bg-[#fffdf9] shadow-none" data-testid="dashboard-formula-card">
          <CardContent className="flex flex-col gap-5 p-6 sm:flex-row sm:items-center sm:justify-between sm:p-8"><div><div className="flex items-center gap-2"><CircleAlert className="size-4 text-[#d97706]" /><p className="text-sm font-semibold text-[#17181c]" data-testid="dashboard-formula-title">Transparent by design</p></div><p className="mt-2 max-w-3xl text-xs leading-5 text-[#8a8f99]" data-testid="dashboard-formula-copy">{analysis.formula_notes.join(" ")}</p></div><Button variant="outline" className="shrink-0 border-[#d9c9ad] bg-white" onClick={() => window.alert(analysis.disclaimer)} data-testid="dashboard-disclaimer-button">Read disclaimer</Button></CardContent>
        </Card>
      </section>
    </AppShell>
  );
}