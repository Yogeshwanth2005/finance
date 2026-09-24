import GoalCheckLines from "@/components/GoalCheckLines";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatINR } from "@/lib/sampleData";
import type { FamilyProfile, FinancialAnalysis } from "@/lib/types";

// Why the plan says "not yet": the emergency fund comes before insurance premiums, which come before investing.
export type InvestmentBlock = "emergency" | "insurance" | null;

export default function SurplusDirectionCard({ profile, analysis, block }: { profile: FamilyProfile; analysis: FinancialAnalysis; block: InvestmentBlock }) {
  const monthlyInvestable = analysis.investable_surplus / 12;
  const allocationBuckets = [
    { name: "Large cap", slug: "large-cap", pct: analysis.equity_split.large_pct, color: "bg-[#0d7a5f]" },
    { name: "Mid cap", slug: "mid-cap", pct: analysis.equity_split.mid_pct, color: "bg-[#10b981]" },
    { name: "Small cap", slug: "small-cap", pct: analysis.equity_split.small_pct, color: "bg-[#6ee7b7]" },
    { name: "Debt", slug: "debt", pct: analysis.allocation.debt_pct, color: "bg-[#2563eb]" },
    { name: "Gold", slug: "gold", pct: analysis.allocation.gold_pct, color: "bg-[#d97706]" },
  ];

  return (
    <Card className="border-[#e4e1d8] bg-[#fff9ef] shadow-none" data-testid="dashboard-investment-card">
      <CardHeader className="p-6 pb-2"><p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#a16207]" data-testid="investment-eyebrow">Surplus direction</p><CardTitle className="mt-2 text-xl font-semibold text-[#17181c]" data-testid="investment-title">Invest what protection leaves behind.</CardTitle></CardHeader>
      <CardContent className="p-6 pt-3">
        {block === "emergency" ? (
          <div data-testid="investment-emergency-blocker">
            <p className="text-sm leading-6 text-[#5c5f66]">Build your emergency fund before investing — it comes before insurance premiums in the priority order.</p>
            <p className="mt-4 font-mono text-2xl font-bold text-[#17181c]" data-testid="investment-emergency-gap-amount">{formatINR(analysis.emergency_gap, true)}</p>
            <p className="mt-1 text-xs text-[#8a8f99]">more needed to reach a 6-month fund ({analysis.emergency_months} months covered today)</p>
          </div>
        ) : block === "insurance" ? (
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
  );
}
