import { config } from "./config";

export type InsurancePlanType = "term" | "health";

export interface InsurancePlanReferenceLike {
  id: string;
  planType: InsurancePlanType;
  sumAssuredMax: number;
}

// Closest sum-assured match to the computed gap — never "largest" or
// "cheapest" — to avoid the selection itself acting as a ranking signal
// (see .agents/context/subsystem-notes.md).
export function selectInsuranceExamples<T extends InsurancePlanReferenceLike>(
  planType: InsurancePlanType,
  gapAmount: number,
  plans: T[],
  count: number = config.insurance_examples_per_gap_type,
): T[] {
  return plans
    .filter((plan) => plan.planType === planType)
    .sort(
      (a, b) =>
        Math.abs(a.sumAssuredMax - gapAmount) - Math.abs(b.sumAssuredMax - gapAmount),
    )
    .slice(0, count);
}
