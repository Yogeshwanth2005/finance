import { describe, expect, test } from "vitest";
import {
  initialWizardState, validateScreen2, validateScreen3, validateScreen4, validateScreen5,
} from "../pages/onboarding/screens.jsx";

describe("validateScreen2", () => {
  test("rejects age outside 18-100", () => {
    const errors = validateScreen2({ ...initialWizardState, age: "15", investmentHorizonYears: "5" });
    expect(errors.age).toBeDefined();
  });

  test("accepts a valid age and horizon", () => {
    const errors = validateScreen2({ ...initialWizardState, age: "30", investmentHorizonYears: "10" });
    expect(errors.age).toBeUndefined();
    expect(errors.investmentHorizonYears).toBeUndefined();
  });

  test("rejects a negative dependents count", () => {
    const errors = validateScreen2({ ...initialWizardState, age: "30", investmentHorizonYears: "10", dependentsCount: "-1" });
    expect(errors.dependentsCount).toBeDefined();
  });
});

describe("validateScreen3", () => {
  test("rejects a missing monthly income", () => {
    const errors = validateScreen3({ ...initialWizardState, monthlyIncome: "", monthlyExpenses: "1000", currentSavings: "1000" });
    expect(errors.monthlyIncome).toBeDefined();
  });

  test("accepts valid non-negative amounts", () => {
    const errors = validateScreen3({ ...initialWizardState, monthlyIncome: "50000", monthlyExpenses: "40000", currentSavings: "180000" });
    expect(Object.keys(errors)).toHaveLength(0);
  });
});

describe("validateScreen4", () => {
  test("rejects a debt with no label", () => {
    const errors = validateScreen4({
      ...initialWizardState,
      debts: [{ key: "debt-1", label: "", outstandingAmount: "1000", interestRatePct: "10", tenureMonths: "12" }],
    });
    expect(errors["debt-1-label"]).toBeDefined();
  });

  test("accepts a fully filled debt row", () => {
    const errors = validateScreen4({
      ...initialWizardState,
      debts: [{ key: "debt-1", label: "Car loan", outstandingAmount: "1000", interestRatePct: "10", tenureMonths: "12" }],
    });
    expect(Object.keys(errors)).toHaveLength(0);
  });
});

describe("validateScreen5", () => {
  test("rejects a negative cover amount", () => {
    const errors = validateScreen5({ ...initialWizardState, existingTermCoverAmount: "-1" });
    expect(errors.existingTermCoverAmount).toBeDefined();
  });

  test("accepts zero cover amounts", () => {
    const errors = validateScreen5({ ...initialWizardState, existingTermCoverAmount: "0", personalHealthCoverAmount: "0", employerHealthCoverAmount: "0" });
    expect(Object.keys(errors)).toHaveLength(0);
  });
});
