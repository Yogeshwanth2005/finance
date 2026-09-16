import { config } from "./config";

export interface EmiInput {
  outstandingAmount: number;
  interestRatePct: number;
  tenureMonths: number;
}

export interface Debt extends EmiInput {
  id: string;
}

export function calculateEmi({
  outstandingAmount,
  interestRatePct,
  tenureMonths,
}: EmiInput): number {
  const monthlyRate = interestRatePct / 12 / 100;
  if (monthlyRate === 0) {
    return outstandingAmount / tenureMonths;
  }
  const growth = Math.pow(1 + monthlyRate, tenureMonths);
  return (outstandingAmount * monthlyRate * growth) / (growth - 1);
}

export function prioritizeDebts(debts: Debt[]): string[] {
  return [...debts]
    .sort((a, b) => b.interestRatePct - a.interestRatePct)
    .map((debt) => debt.id);
}

export type EmergencyFundStatus = "inadequate" | "building" | "adequate";

export interface EmergencyFundInput {
  monthlyExpenses: number;
  currentSavings: number;
}

export interface EmergencyFundResult {
  target: number;
  current: number;
  status: EmergencyFundStatus;
}

// No v1 source for the status thresholds (see decisions/log.md); halfway
// to target is the dividing line between "inadequate" and "building".
export function computeEmergencyFund({
  monthlyExpenses,
  currentSavings,
}: EmergencyFundInput): EmergencyFundResult {
  const target = monthlyExpenses * config.emergency_fund_multiplier;
  const status: EmergencyFundStatus =
    currentSavings >= target
      ? "adequate"
      : currentSavings >= target / 2
        ? "building"
        : "inadequate";

  return { target, current: currentSavings, status };
}

export interface TermCoverInput {
  annualIncome: number;
  existingTermCoverAmount: number;
}

export interface TermCoverResult {
  recommendedTermCover: number;
  gap: number;
}

export function computeTermCoverGap({
  annualIncome,
  existingTermCoverAmount,
}: TermCoverInput): TermCoverResult {
  const recommendedTermCover = annualIncome * config.income_replacement_multiplier;
  return {
    recommendedTermCover,
    gap: Math.max(0, recommendedTermCover - existingTermCoverAmount),
  };
}

export interface HealthCoverInput {
  personalHealthCoverAmount: number;
  employerHealthCoverAmount: number;
}

export interface HealthCoverResult {
  effectiveExistingCover: number;
  recommendedHealthCover: number;
  gap: number;
}

// No v1 source for how personal + employer cover combine (see
// decisions/log.md); treated as a straight sum.
export function computeHealthCoverGap({
  personalHealthCoverAmount,
  employerHealthCoverAmount,
}: HealthCoverInput): HealthCoverResult {
  const effectiveExistingCover = personalHealthCoverAmount + employerHealthCoverAmount;
  const recommendedHealthCover = config.health_cover_baseline;
  return {
    effectiveExistingCover,
    recommendedHealthCover,
    gap: Math.max(0, recommendedHealthCover - effectiveExistingCover),
  };
}

export interface KpiInput {
  emergencyFundCurrent: number;
  emergencyFundTarget: number;
  existingTermCoverAmount: number;
  recommendedTermCover: number;
  effectiveExistingCover: number;
  recommendedHealthCover: number;
  monthlyIncome: number;
  monthlyExpenses: number;
  debts: Debt[];
}

export interface KpiResult {
  emergencyFundCoveragePct: number;
  termCoverAdequacyPct: number;
  healthCoverAdequacyPct: number;
  savingsRatePct: number;
  debtToIncomePct: number;
}

export function computeKpis({
  emergencyFundCurrent,
  emergencyFundTarget,
  existingTermCoverAmount,
  recommendedTermCover,
  effectiveExistingCover,
  recommendedHealthCover,
  monthlyIncome,
  monthlyExpenses,
  debts,
}: KpiInput): KpiResult {
  const totalEmi = debts.reduce((sum, debt) => sum + calculateEmi(debt), 0);

  return {
    emergencyFundCoveragePct: (emergencyFundCurrent / emergencyFundTarget) * 100,
    termCoverAdequacyPct: (existingTermCoverAmount / recommendedTermCover) * 100,
    healthCoverAdequacyPct: (effectiveExistingCover / recommendedHealthCover) * 100,
    savingsRatePct: ((monthlyIncome - monthlyExpenses) / monthlyIncome) * 100,
    debtToIncomePct: (totalEmi / monthlyIncome) * 100,
  };
}

export interface GapAnalysisInput {
  monthlyIncome: number;
  monthlyExpenses: number;
  currentSavings: number;
  existingTermCoverAmount: number;
  personalHealthCoverAmount: number;
  employerHealthCoverAmount: number;
  debts: Debt[];
}

export interface GapAnalysisResult {
  emergencyFundTarget: number;
  emergencyFundCurrent: number;
  emergencyFundStatus: EmergencyFundStatus;
  debtPriorityOrder: string[];
  termCoverGap: number;
  healthCoverGap: number;
  emergencyFundCoveragePct: number;
  termCoverAdequacyPct: number;
  healthCoverAdequacyPct: number;
  savingsRatePct: number;
  debtToIncomePct: number;
}

// Composes 4.1-4.4 (emergency fund, debt priority, term/health gap) with
// the 4.5 KPI layer into the shape gap_analysis_results persists.
export function computeGapAnalysis(input: GapAnalysisInput): GapAnalysisResult {
  const emergencyFund = computeEmergencyFund({
    monthlyExpenses: input.monthlyExpenses,
    currentSavings: input.currentSavings,
  });
  const termCover = computeTermCoverGap({
    annualIncome: input.monthlyIncome * 12,
    existingTermCoverAmount: input.existingTermCoverAmount,
  });
  const healthCover = computeHealthCoverGap({
    personalHealthCoverAmount: input.personalHealthCoverAmount,
    employerHealthCoverAmount: input.employerHealthCoverAmount,
  });
  const debtPriorityOrder = prioritizeDebts(input.debts);
  const kpis = computeKpis({
    emergencyFundCurrent: emergencyFund.current,
    emergencyFundTarget: emergencyFund.target,
    existingTermCoverAmount: input.existingTermCoverAmount,
    recommendedTermCover: termCover.recommendedTermCover,
    effectiveExistingCover: healthCover.effectiveExistingCover,
    recommendedHealthCover: healthCover.recommendedHealthCover,
    monthlyIncome: input.monthlyIncome,
    monthlyExpenses: input.monthlyExpenses,
    debts: input.debts,
  });

  return {
    emergencyFundTarget: emergencyFund.target,
    emergencyFundCurrent: emergencyFund.current,
    emergencyFundStatus: emergencyFund.status,
    debtPriorityOrder,
    termCoverGap: termCover.gap,
    healthCoverGap: healthCover.gap,
    ...kpis,
  };
}
