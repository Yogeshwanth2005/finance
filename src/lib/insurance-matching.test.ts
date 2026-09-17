import { describe, expect, test } from "vitest";
import { selectInsuranceExamples } from "./insurance-matching";

const allPlans = [
  { id: "t1", planType: "term" as const, sumAssuredMax: 5000000 },
  { id: "t2", planType: "term" as const, sumAssuredMax: 10000000 },
  { id: "t3", planType: "term" as const, sumAssuredMax: 20000000 },
  { id: "h1", planType: "health" as const, sumAssuredMax: 500000 },
  { id: "h2", planType: "health" as const, sumAssuredMax: 1000000 },
];

describe("selectInsuranceExamples", () => {
  test("filters by planType", () => {
    const result = selectInsuranceExamples("health", 500000, allPlans, 5);
    expect(result.map((p) => p.id)).toEqual(["h1", "h2"]);
  });

  test("sorts by closest sumAssuredMax to gapAmount, ascending distance", () => {
    const result = selectInsuranceExamples("term", 9000000, allPlans, 3);
    expect(result.map((p) => p.id)).toEqual(["t2", "t1", "t3"]);
  });

  test("never sorts by largest or cheapest — closest match only", () => {
    const result = selectInsuranceExamples("term", 4000000, allPlans, 1);
    expect(result.map((p) => p.id)).toEqual(["t1"]);
  });

  test("takes only the first count", () => {
    const result = selectInsuranceExamples("term", 9000000, allPlans, 1);
    expect(result).toHaveLength(1);
  });

  test("defaults the count to config.insurance_examples_per_gap_type when not given", () => {
    const manyTermPlans = Array.from({ length: 5 }, (_, i) => ({
      id: `t${i}`,
      planType: "term" as const,
      sumAssuredMax: i * 1000000,
    }));
    expect(selectInsuranceExamples("term", 5000000, manyTermPlans)).toHaveLength(2);
  });
});
