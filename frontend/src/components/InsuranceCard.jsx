import { formatInr } from "../lib/format.js";

function features(plan) {
  return Array.isArray(plan.key_features) ? plan.key_features : [];
}

export function InsuranceCard({ plan }) {
  return (
    <div className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
      <p className="text-sm font-medium text-zinc-900 dark:text-zinc-50">{plan.plan_name}</p>
      <p className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">{plan.insurer_name}</p>
      <p className="mt-3 text-xs text-zinc-600 dark:text-zinc-400">
        Sum assured: {formatInr(plan.sum_assured_min)} – {formatInr(plan.sum_assured_max)}
      </p>
      <ul className="mt-2 list-inside list-disc text-xs text-zinc-600 dark:text-zinc-400">
        {features(plan).slice(0, 3).map((feature) => <li key={feature}>{feature}</li>)}
      </ul>
      <p className="mt-2 text-xs text-zinc-500 dark:text-zinc-400">{plan.indicative_premium_note}</p>
      <dl className="mt-2 space-y-1 text-xs text-zinc-600 dark:text-zinc-400">
        <div className="flex justify-between">
          <dt>Claim settlement ratio</dt>
          <dd>{plan.claim_settlement_ratio_pct.toFixed(1)}%</dd>
        </div>
        <div className="flex justify-between">
          <dt>Avg. settlement time</dt>
          <dd>{plan.avg_claim_settlement_days} days</dd>
        </div>
      </dl>
      <a href={plan.external_url} target="_blank" rel="noopener noreferrer" className="mt-3 inline-block text-xs font-medium text-accent underline underline-offset-4">
        Show more details
      </a>
    </div>
  );
}

// Neutral comparison — every column is a plain fact, no ranking, no
// "best value" badge, no score, no sort implying one plan is better.
export function InsuranceComparisonTable({ plans }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-zinc-200 dark:border-zinc-800">
      <table className="w-full text-left text-xs">
        <thead>
          <tr className="border-b border-zinc-200 text-zinc-500 dark:border-zinc-800 dark:text-zinc-400">
            <th className="px-3 py-2 font-medium">Plan</th>
            <th className="px-3 py-2 font-medium">Sum assured</th>
            <th className="px-3 py-2 font-medium">Premium (indicative)</th>
            <th className="px-3 py-2 font-medium">Claim settlement ratio</th>
            <th className="px-3 py-2 font-medium">Avg. settlement time</th>
            <th className="px-3 py-2 font-medium">Link</th>
          </tr>
        </thead>
        <tbody>
          {plans.map((plan) => (
            <tr key={plan.id} className="border-b border-zinc-100 last:border-b-0 dark:border-zinc-900">
              <td className="px-3 py-2">
                <p className="font-medium text-zinc-900 dark:text-zinc-50">{plan.plan_name}</p>
                <p className="text-zinc-500 dark:text-zinc-400">{plan.insurer_name}</p>
              </td>
              <td className="px-3 py-2">{formatInr(plan.sum_assured_min)} – {formatInr(plan.sum_assured_max)}</td>
              <td className="px-3 py-2">{plan.indicative_premium_note}</td>
              <td className="px-3 py-2">{plan.claim_settlement_ratio_pct.toFixed(1)}%</td>
              <td className="px-3 py-2">{plan.avg_claim_settlement_days} days</td>
              <td className="px-3 py-2">
                <a href={plan.external_url} target="_blank" rel="noopener noreferrer" className="font-medium text-accent underline underline-offset-4">
                  Details
                </a>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
