import { formatInr } from "@/lib/format";

export interface FundCardData {
  id: string;
  schemeName: string;
  amcName: string;
  category: string;
  expenseRatio: number;
  latestNav: number;
  externalUrl: string;
}

export function FundCard({ fund }: { fund: FundCardData }) {
  return (
    <div className="rounded-lg border border-zinc-200 p-4 dark:border-zinc-800">
      <p className="text-sm font-medium text-zinc-900 dark:text-zinc-50">{fund.schemeName}</p>
      <p className="mt-0.5 text-xs text-zinc-500 dark:text-zinc-400">{fund.amcName}</p>
      <dl className="mt-3 space-y-1 text-xs text-zinc-600 dark:text-zinc-400">
        <div className="flex justify-between">
          <dt>Category</dt>
          <dd className="capitalize">{fund.category.replace(/_/g, " ")}</dd>
        </div>
        <div className="flex justify-between">
          <dt>Expense ratio</dt>
          <dd>{fund.expenseRatio.toFixed(2)}%</dd>
        </div>
        <div className="flex justify-between">
          <dt>Latest NAV</dt>
          <dd>{formatInr(fund.latestNav)}</dd>
        </div>
      </dl>
      <a
        href={fund.externalUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="mt-3 inline-block text-xs font-medium text-accent underline underline-offset-4"
      >
        View scheme details
      </a>
    </div>
  );
}
