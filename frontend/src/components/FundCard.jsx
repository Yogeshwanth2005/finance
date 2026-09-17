import { formatInr } from "../lib/format.js";

export function FundCard({ fund }) {
  return (
    <div className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
      <p className="text-sm font-medium text-zinc-900 dark:text-zinc-50">{fund.scheme_name}</p>
      <p className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">{fund.amc_name}</p>
      <dl className="mt-3 space-y-1 text-xs text-zinc-600 dark:text-zinc-400">
        <div className="flex justify-between">
          <dt>Category</dt>
          <dd className="capitalize">{fund.category.replace(/_/g, " ")}</dd>
        </div>
        <div className="flex justify-between">
          <dt>Expense ratio</dt>
          <dd>{fund.expense_ratio.toFixed(2)}%</dd>
        </div>
        <div className="flex justify-between">
          <dt>Latest NAV</dt>
          <dd>{formatInr(fund.latest_nav)}</dd>
        </div>
      </dl>
      <a href={fund.external_url} target="_blank" rel="noopener noreferrer" className="mt-3 inline-block text-xs font-medium text-accent underline underline-offset-4">
        View scheme details
      </a>
    </div>
  );
}
