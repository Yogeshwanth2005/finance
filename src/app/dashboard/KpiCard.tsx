import { formatInr } from "@/lib/format";

const RADIUS = 40;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

export function KpiCard({
  label,
  pct,
  gapAmount,
  gapLabel,
  statusLabel,
}: {
  label: string;
  pct: number;
  gapAmount: number;
  gapLabel: string;
  statusLabel?: string;
}) {
  const clamped = Math.max(0, Math.min(100, pct));
  const offset = CIRCUMFERENCE * (1 - clamped / 100);

  return (
    <div className="rounded-lg border border-zinc-200 p-5 dark:border-zinc-800">
      <p className="font-mono text-xs text-zinc-400 dark:text-zinc-500">{label}</p>
      <div className="mt-3 flex items-center gap-4">
        <svg width="96" height="96" viewBox="0 0 96 96" className="shrink-0 -rotate-90">
          <circle cx="48" cy="48" r={RADIUS} fill="none" stroke="currentColor" strokeWidth="8" className="text-zinc-200 dark:text-zinc-800" />
          <circle
            cx="48"
            cy="48"
            r={RADIUS}
            fill="none"
            stroke="currentColor"
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={CIRCUMFERENCE}
            strokeDashoffset={offset}
            className="text-accent"
          />
        </svg>
        <div>
          <p className="text-2xl font-semibold tabular-nums text-zinc-900 dark:text-zinc-50">
            {pct.toFixed(0)}%
          </p>
          {statusLabel && (
            <p className="mt-0.5 text-xs capitalize text-zinc-500 dark:text-zinc-400">{statusLabel}</p>
          )}
        </div>
      </div>
      <p className="mt-3 text-xs text-zinc-500 dark:text-zinc-400">
        {gapLabel}: {formatInr(gapAmount)}
      </p>
    </div>
  );
}
