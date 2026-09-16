import { describe, expect, test } from "vitest";
import { computeAllocation, selectFundExamples } from "./allocation";

describe("computeAllocation", () => {
  test("moderate risk, long horizon: base equity is 100 minus age, gold takes the flat sleeve", () => {
    const result = computeAllocation({ age: 30, riskTolerance: "moderate", investmentHorizonYears: 10 });

    expect(result.equityPct).toBe(70);
    expect(result.goldPct).toBe(10);
    expect(result.debtPct).toBe(20);
  });

  test("aggressive risk tolerance scales equity up", () => {
    const result = computeAllocation({ age: 30, riskTolerance: "aggressive", investmentHorizonYears: 10 });

    expect(result.equityPct).toBe(84);
    expect(result.goldPct).toBe(10);
    expect(result.debtPct).toBe(6);
  });

  test("conservative risk tolerance scales equity down", () => {
    const result = computeAllocation({ age: 30, riskTolerance: "conservative", investmentHorizonYears: 10 });

    expect(result.equityPct).toBe(56);
    expect(result.goldPct).toBe(10);
    expect(result.debtPct).toBe(34);
  });

  test("short investment horizon shifts equity to debt", () => {
    const result = computeAllocation({ age: 30, riskTolerance: "moderate", investmentHorizonYears: 2 });

    expect(result.equityPct).toBe(50);
    expect(result.goldPct).toBe(10);
    expect(result.debtPct).toBe(40);
  });

  test("gold is capped by whatever's left after equity, not always the flat 10%", () => {
    const result = computeAllocation({ age: 20, riskTolerance: "aggressive", investmentHorizonYears: 10 });

    expect(result.equityPct).toBe(96);
    expect(result.goldPct).toBe(4);
    expect(result.debtPct).toBe(0);
  });

  test("equity is clamped to 100 and never pushes debt/gold negative", () => {
    const result = computeAllocation({ age: 5, riskTolerance: "aggressive", investmentHorizonYears: 10 });

    expect(result.equityPct).toBe(100);
    expect(result.goldPct).toBe(0);
    expect(result.debtPct).toBe(0);
  });

  test("equity is clamped to 0 for a low base combined with the short-horizon shift", () => {
    const result = computeAllocation({ age: 90, riskTolerance: "conservative", investmentHorizonYears: 2 });

    expect(result.equityPct).toBe(0);
    expect(result.goldPct).toBe(10);
    expect(result.debtPct).toBe(90);
  });

  test("the three buckets always sum to 100", () => {
    const result = computeAllocation({ age: 45, riskTolerance: "moderate", investmentHorizonYears: 1 });

    expect(result.equityPct + result.debtPct + result.goldPct).toBe(100);
  });
});

const allFunds = [
  { id: "e1", category: "equity_large_cap" as const, aumCr: 5000 },
  { id: "e2", category: "equity_diversified" as const, aumCr: 12000 },
  { id: "e3", category: "equity_large_cap" as const, aumCr: 8000 },
  { id: "d1", category: "debt_short_duration" as const, aumCr: 3000 },
  { id: "d2", category: "fixed_deposit" as const, aumCr: 9000 },
  { id: "g1", category: "gold_etf" as const, aumCr: 2000 },
  { id: "g2", category: "sovereign_gold_bond" as const, aumCr: 1000 },
];

describe("selectFundExamples", () => {
  test("equity bucket maps to both equity categories, sorted by AUM descending", () => {
    const result = selectFundExamples("equity", allFunds, 2);
    expect(result.map((f) => f.id)).toEqual(["e2", "e3"]);
  });

  test("debt bucket maps to debt_short_duration and fixed_deposit", () => {
    const result = selectFundExamples("debt", allFunds, 3);
    expect(result.map((f) => f.id)).toEqual(["d2", "d1"]);
  });

  test("gold bucket maps to gold_etf and sovereign_gold_bond", () => {
    const result = selectFundExamples("gold", allFunds, 3);
    expect(result.map((f) => f.id)).toEqual(["g1", "g2"]);
  });

  test("defaults the count to config.fund_examples_per_category when not given", () => {
    const manyEquityFunds = Array.from({ length: 5 }, (_, i) => ({
      id: `e${i}`,
      category: "equity_large_cap" as const,
      aumCr: i,
    }));
    expect(selectFundExamples("equity", manyEquityFunds)).toHaveLength(3);
  });
});
