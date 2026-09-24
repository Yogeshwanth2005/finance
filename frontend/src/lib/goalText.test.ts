import { describe, expect, it } from "vitest";

import { crashLine, goalLine } from "@/lib/goalText";
import type { GoalCheck } from "@/lib/types";

// An age-50 moderate profile: 50% equity expects 9.6% against a 10% goal, and 58.6% equity would reach it.
const below: GoalCheck = {
  inflation_pct: 6,
  margin_pct: 4,
  target_pct: 10,
  expected_return_pct: 9.6,
  beats_target: false,
  reachable: true,
  suggestion_suppressed: false,
  min_equity_pct: 58.6,
  crash_loss_pct: 18.4,
  crash_loss_at_min_equity_pct: 21.6,
};
const beats: GoalCheck = { ...below, beats_target: true, expected_return_pct: 10.6, min_equity_pct: null, crash_loss_at_min_equity_pct: null };

describe("goalLine", () => {
  it("ticks a mix that beats the goal", () => {
    expect(goalLine(beats)).toBe("Goal: inflation 6% + 4% = 10%/yr → this mix expects ≈ 10.6% ✓");
  });

  it("says how much equity would reach the goal and what a crash would then cost", () => {
    expect(goalLine(below)).toBe(
      "Goal: inflation 6% + 4% = 10%/yr → this mix expects ≈ 9.6%, below the goal. About 59% equity would reach it (a March-2020-style fall would then have cost about 22%).",
    );
  });

  it("never pushes equity for a short horizon", () => {
    const short = { ...below, suggestion_suppressed: true, reachable: null, min_equity_pct: null, crash_loss_at_min_equity_pct: null };
    expect(goalLine(short)).toBe("Goal: inflation 6% + 4% = 10%/yr → this mix expects ≈ 9.6%. Short horizons aren't pushed toward more equity.");
  });

  it("says so when no mix can reach the goal", () => {
    const unreachable = { ...below, reachable: false, min_equity_pct: null, crash_loss_at_min_equity_pct: null };
    expect(goalLine(unreachable)).toContain("The goal is not reachable at this risk level");
    expect(goalLine(unreachable)).not.toContain("About");
  });

  it("falls back to the plain shortfall when a suggestion is missing", () => {
    const missing = { ...below, min_equity_pct: null, crash_loss_at_min_equity_pct: null };
    expect(goalLine(missing)).toBe("Goal: inflation 6% + 4% = 10%/yr → this mix expects ≈ 9.6%, below the goal.");
  });
});

describe("crashLine", () => {
  it("rounds the fall and says it is one crash, not a worst case", () => {
    expect(crashLine(below)).toBe("March-2020-style fall: about −18% (one crash in the data, not a worst case)");
  });
});
