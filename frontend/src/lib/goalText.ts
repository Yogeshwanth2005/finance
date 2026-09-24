import type { GoalCheck } from "@/lib/types";

// Words for the investment card's goal and crash lines. The numbers and flags come from the backend (goal_check);
// only the sentence is decided here.
export function goalLine(goal: GoalCheck): string {
  const target = `Goal: inflation ${goal.inflation_pct}% + ${goal.margin_pct}% = ${goal.target_pct}%/yr`;
  const expects = `this mix expects ≈ ${goal.expected_return_pct.toFixed(1)}%`;
  if (goal.beats_target) return `${target} → ${expects} ✓`;
  if (goal.suggestion_suppressed) return `${target} → ${expects}. Short horizons aren't pushed toward more equity.`;
  if (goal.reachable === false) return `${target} → ${expects}. The goal is not reachable at this risk level with these return assumptions.`;
  if (goal.min_equity_pct === null || goal.crash_loss_at_min_equity_pct === null) return `${target} → ${expects}, below the goal.`;
  return `${target} → ${expects}, below the goal. About ${Math.round(goal.min_equity_pct)}% equity would reach it (a March-2020-style fall would then have cost about ${Math.round(goal.crash_loss_at_min_equity_pct)}%).`;
}

export function crashLine(goal: GoalCheck): string {
  return `March-2020-style fall: about −${Math.round(goal.crash_loss_pct)}% (one crash in the data, not a worst case)`;
}
