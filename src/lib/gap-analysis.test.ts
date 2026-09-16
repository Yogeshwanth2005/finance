import { describe, expect, test } from "vitest";
import {
  calculateEmi,
  computeEmergencyFund,
  computeGapAnalysis,
  computeHealthCoverGap,
  computeKpis,
  computeTermCoverGap,
  prioritizeDebts,
} from "./gap-analysis";

describe("calculateEmi", () => {
  test("computes standard amortized EMI for a nonzero interest rate", () => {
    const emi = calculateEmi({
      outstandingAmount: 100000,
      interestRatePct: 12,
      tenureMonths: 12,
    });

    expect(emi).toBeCloseTo(8884.88, 1);
  });

  test("falls back to straight-line division when interest rate is zero", () => {
    const emi = calculateEmi({
      outstandingAmount: 120000,
      interestRatePct: 0,
      tenureMonths: 12,
    });

    expect(emi).toBeCloseTo(10000, 5);
  });
});

describe("prioritizeDebts", () => {
  test("orders debt ids highest interest rate first", () => {
    const order = prioritizeDebts([
      { id: "car-loan", outstandingAmount: 300000, interestRatePct: 9, tenureMonths: 48 },
      { id: "credit-card", outstandingAmount: 50000, interestRatePct: 36, tenureMonths: 12 },
      { id: "personal-loan", outstandingAmount: 100000, interestRatePct: 14, tenureMonths: 24 },
    ]);

    expect(order).toEqual(["credit-card", "personal-loan", "car-loan"]);
  });

  test("returns an empty order for no debts", () => {
    expect(prioritizeDebts([])).toEqual([]);
  });
});

describe("computeEmergencyFund", () => {
  test("target is 6 months of expenses", () => {
    const result = computeEmergencyFund({ monthlyExpenses: 40000, currentSavings: 0 });
    expect(result.target).toBe(240000);
  });

  test("status is adequate once current savings meet the target", () => {
    const result = computeEmergencyFund({ monthlyExpenses: 40000, currentSavings: 240000 });
    expect(result.status).toBe("adequate");
  });

  test("status is inadequate below half the target", () => {
    const result = computeEmergencyFund({ monthlyExpenses: 40000, currentSavings: 100000 });
    expect(result.status).toBe("inadequate");
  });

  test("status is building between half and full target", () => {
    const result = computeEmergencyFund({ monthlyExpenses: 40000, currentSavings: 180000 });
    expect(result.status).toBe("building");
  });
});

describe("computeTermCoverGap", () => {
  test("recommended cover is 10x annual income, gap fills the shortfall", () => {
    const result = computeTermCoverGap({
      annualIncome: 600000,
      existingTermCoverAmount: 2000000,
    });

    expect(result.recommendedTermCover).toBe(6000000);
    expect(result.gap).toBe(4000000);
  });

  test("gap is clamped to zero when existing cover already meets the recommendation", () => {
    const result = computeTermCoverGap({
      annualIncome: 600000,
      existingTermCoverAmount: 9000000,
    });

    expect(result.gap).toBe(0);
  });
});

describe("computeHealthCoverGap", () => {
  test("effective cover sums personal and employer cover against the flat baseline", () => {
    const result = computeHealthCoverGap({
      personalHealthCoverAmount: 200000,
      employerHealthCoverAmount: 100000,
    });

    expect(result.effectiveExistingCover).toBe(300000);
    expect(result.recommendedHealthCover).toBe(500000);
    expect(result.gap).toBe(200000);
  });

  test("gap is clamped to zero when effective cover already meets the baseline", () => {
    const result = computeHealthCoverGap({
      personalHealthCoverAmount: 400000,
      employerHealthCoverAmount: 300000,
    });

    expect(result.gap).toBe(0);
  });
});

describe("computeKpis", () => {
  test("computes all five KPI percentages per Section 4.5's formulas", () => {
    const result = computeKpis({
      emergencyFundCurrent: 180000,
      emergencyFundTarget: 240000,
      existingTermCoverAmount: 2000000,
      recommendedTermCover: 6000000,
      effectiveExistingCover: 300000,
      recommendedHealthCover: 500000,
      monthlyIncome: 50000,
      monthlyExpenses: 40000,
      debts: [
        { id: "credit-card", outstandingAmount: 100000, interestRatePct: 12, tenureMonths: 12 },
      ],
    });

    expect(result.emergencyFundCoveragePct).toBeCloseTo(75, 5);
    expect(result.termCoverAdequacyPct).toBeCloseTo(33.33, 1);
    expect(result.healthCoverAdequacyPct).toBeCloseTo(60, 5);
    expect(result.savingsRatePct).toBeCloseTo(20, 5);
    expect(result.debtToIncomePct).toBeCloseTo(17.77, 1);
  });

  test("sums EMI across multiple debts for debt-to-income", () => {
    const result = computeKpis({
      emergencyFundCurrent: 0,
      emergencyFundTarget: 1,
      existingTermCoverAmount: 0,
      recommendedTermCover: 1,
      effectiveExistingCover: 0,
      recommendedHealthCover: 1,
      monthlyIncome: 50000,
      monthlyExpenses: 0,
      debts: [
        { id: "a", outstandingAmount: 120000, interestRatePct: 0, tenureMonths: 12 },
        { id: "b", outstandingAmount: 120000, interestRatePct: 0, tenureMonths: 12 },
      ],
    });

    // Two zero-interest debts of 120000/12mo = 10000 EMI each = 20000 total.
    expect(result.debtToIncomePct).toBeCloseTo(40, 5);
  });
});

describe("computeGapAnalysis", () => {
  test("composes emergency fund, term/health cover, debt priority, and KPIs from raw profile input", () => {
    const result = computeGapAnalysis({
      monthlyIncome: 50000,
      monthlyExpenses: 40000,
      currentSavings: 180000,
      existingTermCoverAmount: 2000000,
      personalHealthCoverAmount: 200000,
      employerHealthCoverAmount: 100000,
      debts: [
        { id: "credit-card", outstandingAmount: 100000, interestRatePct: 12, tenureMonths: 12 },
        { id: "car-loan", outstandingAmount: 300000, interestRatePct: 9, tenureMonths: 48 },
      ],
    });

    expect(result.emergencyFundTarget).toBe(240000);
    expect(result.emergencyFundCurrent).toBe(180000);
    expect(result.emergencyFundStatus).toBe("building");
    expect(result.debtPriorityOrder).toEqual(["credit-card", "car-loan"]);
    expect(result.termCoverGap).toBe(4000000);
    expect(result.healthCoverGap).toBe(200000);
    expect(result.emergencyFundCoveragePct).toBeCloseTo(75, 5);
    expect(result.savingsRatePct).toBeCloseTo(20, 5);
  });
});
