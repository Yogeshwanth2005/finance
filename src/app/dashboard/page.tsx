import { redirect } from "next/navigation";
import { prisma } from "@/lib/db";
import { config } from "@/lib/config";
import { getOrCreateDemoUser } from "@/lib/demo-user";
import { formatInr } from "@/lib/format";
import { selectFundExamples, type AllocationBucket } from "@/lib/allocation";
import { selectInsuranceExamples, type InsurancePlanType } from "@/lib/insurance-matching";
import { KpiCard } from "./KpiCard";
import { FundCard } from "./FundCard";
import { InsuranceCard, InsuranceComparisonTable } from "./InsuranceCard";

const BUCKETS: AllocationBucket[] = ["equity", "debt", "gold"];

export default async function DashboardPage() {
  const user = await getOrCreateDemoUser();

  const [gapResult, allocationResult] = await Promise.all([
    prisma.gapAnalysisResult.findFirst({
      where: { userId: user.id },
      orderBy: { computedAt: "desc" },
    }),
    prisma.allocationResult.findFirst({
      where: { userId: user.id },
      orderBy: { computedAt: "desc" },
    }),
  ]);

  if (!gapResult || !allocationResult) {
    redirect("/onboarding");
  }

  const allocation = {
    equityPct: Number(allocationResult.equityPct),
    debtPct: Number(allocationResult.debtPct),
    goldPct: Number(allocationResult.goldPct),
  };

  const funds = config.DEMO_MODE ? await prisma.fundReference.findMany() : [];
  const insurancePlans = config.DEMO_MODE ? await prisma.insurancePlanReference.findMany() : [];

  const fundsWithNumericAum = funds.map((f) => ({
    ...f,
    expenseRatio: Number(f.expenseRatio),
    aumCr: Number(f.aumCr),
    latestNav: Number(f.latestNav),
  }));
  const plansForMatching = insurancePlans.map((p) => ({
    ...p,
    sumAssuredMin: Number(p.sumAssuredMin),
    sumAssuredMax: Number(p.sumAssuredMax),
    claimSettlementRatioPct: Number(p.claimSettlementRatioPct),
  }));

  const termCoverGap = Number(gapResult.termCoverGap);
  const healthCoverGap = Number(gapResult.healthCoverGap);

  return (
    <div className="mx-auto max-w-4xl px-6 py-16 sm:py-20">
      <p className="font-mono text-xs text-zinc-400 dark:text-zinc-500">fin — dashboard</p>
      <h1 className="mt-3 text-2xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
        Your financial gap analysis
      </h1>

      <section className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <KpiCard
          label="Emergency fund coverage"
          pct={Number(gapResult.emergencyFundCoveragePct)}
          gapAmount={Math.max(0, Number(gapResult.emergencyFundTarget) - Number(gapResult.emergencyFundCurrent))}
          gapLabel="Gap to target"
          statusLabel={gapResult.emergencyFundStatus}
        />
        <KpiCard
          label="Term cover adequacy"
          pct={Number(gapResult.termCoverAdequacyPct)}
          gapAmount={termCoverGap}
          gapLabel="Cover gap"
        />
        <KpiCard
          label="Health cover adequacy"
          pct={Number(gapResult.healthCoverAdequacyPct)}
          gapAmount={healthCoverGap}
          gapLabel="Cover gap"
        />
        <KpiCard
          label="Savings rate"
          pct={Number(gapResult.savingsRatePct)}
          gapAmount={0}
          gapLabel="—"
        />
        <KpiCard
          label="Debt-to-income"
          pct={Number(gapResult.debtToIncomePct)}
          gapAmount={0}
          gapLabel="—"
        />
      </section>

      <section className="mt-12">
        <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">Allocation snapshot</h2>
        <div className="mt-4 flex gap-6 text-sm">
          <p>Equity: <span className="font-medium">{allocation.equityPct.toFixed(0)}%</span></p>
          <p>Debt: <span className="font-medium">{allocation.debtPct.toFixed(0)}%</span></p>
          <p>Gold: <span className="font-medium">{allocation.goldPct.toFixed(0)}%</span></p>
        </div>
      </section>

      {config.DEMO_MODE && (
        <section className="mt-12">
          <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">Fund examples</h2>
          <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">Illustrative only — see disclaimer below.</p>
          <div className="mt-4 space-y-6">
            {BUCKETS.map((bucket) => {
              const examples = selectFundExamples(bucket, fundsWithNumericAum);
              if (examples.length === 0) return null;
              return (
                <div key={bucket}>
                  <h3 className="mb-2 text-xs font-medium capitalize text-zinc-600 dark:text-zinc-400">{bucket}</h3>
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                    {examples.map((fund) => (
                      <FundCard key={fund.id} fund={fund} />
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {config.DEMO_MODE && (termCoverGap > 0 || healthCoverGap > 0) && (
        <section className="mt-12">
          <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-50">Insurance examples</h2>
          <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">Illustrative only — see disclaimer below.</p>
          <div className="mt-4 space-y-6">
            {([["term", termCoverGap], ["health", healthCoverGap]] as Array<[InsurancePlanType, number]>).map(
              ([planType, gap]) => {
                if (gap <= 0) return null;
                const examples = selectInsuranceExamples(planType, gap, plansForMatching);
                if (examples.length === 0) return null;
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
              },
            )}
          </div>
        </section>
      )}
    </div>
  );
}
