import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiClient } from "../api/client.js";
import { formatInr } from "../lib/format.js";
import { KpiCard } from "../components/KpiCard.jsx";
import { FundCard } from "../components/FundCard.jsx";
import { InsuranceCard, InsuranceComparisonTable } from "../components/InsuranceCard.jsx";

const BUCKETS = ["equity", "debt", "gold"];

export default function Dashboard() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient
      .get("/api/dashboard")
      .then(setData)
      .catch(() => navigate("/onboarding"))
      .finally(() => setLoading(false));
  }, [navigate]);

  if (loading || !data) return null;

  const { kpis, allocation, fund_examples: fundExamples, insurance_examples: insuranceExamples, demo_mode: demoMode } = data;

  return (
    <div className="mx-auto max-w-4xl px-6 py-16 sm:py-20">
      <p className="font-mono text-xs text-zinc-400 dark:text-zinc-500">fin — dashboard</p>
      <h1 className="mt-3 text-2xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
        Your financial gap analysis
      </h1>

      <section className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <KpiCard
          label="Emergency fund coverage"
          pct={kpis.emergency_fund_coverage_pct}
          gapAmount={kpis.emergency_fund_gap}
          gapLabel="Gap to target"
          statusLabel={kpis.emergency_fund_status}
        />
        <KpiCard label="Term cover adequacy" pct={kpis.term_cover_adequacy_pct} gapAmount={kpis.term_cover_gap} gapLabel="Cover gap" />
        <KpiCard label="Health cover adequacy" pct={kpis.health_cover_adequacy_pct} gapAmount={kpis.health_cover_gap} gapLabel="Cover gap" />
        <KpiCard label="Savings rate" pct={kpis.savings_rate_pct} gapAmount={0} gapLabel="—" />
        <KpiCard label="Debt-to-income" pct={kpis.debt_to_income_pct} gapAmount={0} gapLabel="—" />
      </section>

      <section className="mt-12">
        <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">Allocation snapshot</h2>
        <div className="mt-4 flex gap-6 text-sm">
          <p>Equity: <span className="font-medium">{allocation.equity_pct.toFixed(0)}%</span></p>
          <p>Debt: <span className="font-medium">{allocation.debt_pct.toFixed(0)}%</span></p>
          <p>Gold: <span className="font-medium">{allocation.gold_pct.toFixed(0)}%</span></p>
        </div>
      </section>

      {demoMode && (
        <section className="mt-12">
          <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">Fund examples</h2>
          <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">Illustrative only — see disclaimer below.</p>
          <div className="mt-4 space-y-6">
            {BUCKETS.map((bucket) => {
              const examples = fundExamples[bucket];
              if (!examples || examples.length === 0) return null;
              return (
                <div key={bucket}>
                  <h3 className="mb-2 text-xs font-medium capitalize text-zinc-600 dark:text-zinc-400">{bucket}</h3>
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                    {examples.map((fund) => <FundCard key={fund.id} fund={fund} />)}
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {demoMode && (kpis.term_cover_gap > 0 || kpis.health_cover_gap > 0) && (
        <section className="mt-12">
          <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">Insurance examples</h2>
          <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">Illustrative only — see disclaimer below.</p>
          <div className="mt-4 space-y-6">
            {[["term", kpis.term_cover_gap], ["health", kpis.health_cover_gap]].map(([planType, gap]) => {
              if (gap <= 0) return null;
              const examples = insuranceExamples[planType];
              if (!examples || examples.length === 0) return null;
              return (
                <div key={planType}>
                  <h3 className="mb-2 text-xs font-medium capitalize text-zinc-600 dark:text-zinc-400">
                    {planType} cover — gap: {formatInr(gap)}
                  </h3>
                  {examples.length === 1 ? (
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                      <InsuranceCard plan={examples[0]} />
                    </div>
                  ) : (
                    <InsuranceComparisonTable plans={examples} />
                  )}
                </div>
              );
            })}
          </div>
        </section>
      )}
    </div>
  );
}
