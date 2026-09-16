import { config } from "./config";

export type RiskTolerance = "conservative" | "moderate" | "aggressive";

export interface AllocationInput {
  age: number;
  riskTolerance: RiskTolerance;
  investmentHorizonYears: number;
}

export interface AllocationResult {
  equityPct: number;
  debtPct: number;
  goldPct: number;
}

// No v1 source for the base equity formula or the gold sleeve (see
// decisions/log.md): base equity is the standard "constant minus age"
// glide path, and gold is a flat diversification sleeve capped by
// whatever equity leaves behind, so the three buckets always sum to 100.
export function computeAllocation({
  age,
  riskTolerance,
  investmentHorizonYears,
}: AllocationInput): AllocationResult {
  const baseEquityPct = config.base_equity_age_constant - age;
  let equityPct = baseEquityPct * config.risk_tolerance_multipliers[riskTolerance];

  if (investmentHorizonYears <= config.short_horizon_threshold) {
    equityPct -= config.short_horizon_shift;
  }

  equityPct = Math.min(100, Math.max(0, equityPct));

  const goldPct = Math.min(config.gold_allocation_pct, 100 - equityPct);
  const debtPct = 100 - equityPct - goldPct;

  return { equityPct, debtPct, goldPct };
}

export type AllocationBucket = "equity" | "debt" | "gold";

export type FundCategory =
  | "equity_large_cap"
  | "equity_diversified"
  | "debt_short_duration"
  | "fixed_deposit"
  | "gold_etf"
  | "sovereign_gold_bond";

export interface FundReferenceLike {
  id: string;
  category: FundCategory;
  aumCr: number;
}

// Section 5.2's example: equity_pct -> "large-cap index fund or diversified
// equity mutual fund category" implies each bucket spans 2 FundCategory
// enum values, not 1 - mirrored here explicitly since the plan never
// spells the mapping out as a table.
const BUCKET_CATEGORIES: Record<AllocationBucket, FundCategory[]> = {
  equity: ["equity_large_cap", "equity_diversified"],
  debt: ["debt_short_duration", "fixed_deposit"],
  gold: ["gold_etf", "sovereign_gold_bond"],
};

export function selectFundExamples<T extends FundReferenceLike>(
  bucket: AllocationBucket,
  funds: T[],
  count: number = config.fund_examples_per_category,
): T[] {
  const categories = BUCKET_CATEGORIES[bucket];
  return funds
    .filter((fund) => categories.includes(fund.category))
    .sort((a, b) => b.aumCr - a.aumCr)
    .slice(0, count);
}
