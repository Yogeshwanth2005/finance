import { NextResponse } from "next/server";
import { prisma } from "@/lib/db";
import { getOrCreateDemoUser } from "@/lib/demo-user";
import { computeGapAnalysis, type Debt } from "@/lib/gap-analysis";
import { computeAllocation, type RiskTolerance } from "@/lib/allocation";

export interface OnboardingSubmission {
  age: number;
  dependentsCount: number;
  riskTolerance: RiskTolerance;
  investmentHorizonYears: number;
  monthlyIncome: number;
  monthlyExpenses: number;
  currentSavings: number;
  debts: Array<{
    label: string;
    outstandingAmount: number;
    interestRatePct: number;
    tenureMonths: number;
  }>;
  existingTermCoverAmount: number;
  personalHealthCoverAmount: number;
  employerHealthCoverAmount: number;
}

export async function POST(request: Request) {
  const body = (await request.json()) as OnboardingSubmission;
  const user = await getOrCreateDemoUser();

  const { financialProfile, insuranceProfile } = await prisma.$transaction(async (tx) => {
    const financialProfile = await tx.financialProfile.upsert({
      where: { userId: user.id },
      create: {
        userId: user.id,
        age: body.age,
        dependentsCount: body.dependentsCount,
        monthlyIncome: body.monthlyIncome,
        monthlyExpenses: body.monthlyExpenses,
        currentSavings: body.currentSavings,
        riskTolerance: body.riskTolerance,
        investmentHorizonYears: body.investmentHorizonYears,
        consentGivenAt: new Date(),
      },
      update: {
        age: body.age,
        dependentsCount: body.dependentsCount,
        monthlyIncome: body.monthlyIncome,
        monthlyExpenses: body.monthlyExpenses,
        currentSavings: body.currentSavings,
        riskTolerance: body.riskTolerance,
        investmentHorizonYears: body.investmentHorizonYears,
        consentGivenAt: new Date(),
      },
    });

    await tx.existingDebt.deleteMany({ where: { financialProfileId: financialProfile.id } });
    if (body.debts.length > 0) {
      await tx.existingDebt.createMany({
        data: body.debts.map((debt) => ({
          financialProfileId: financialProfile.id,
          label: debt.label,
          outstandingAmount: debt.outstandingAmount,
          interestRatePct: debt.interestRatePct,
          tenureMonths: debt.tenureMonths,
        })),
      });
    }

    const insuranceProfile = await tx.insuranceProfile.upsert({
      where: { userId: user.id },
      create: {
        userId: user.id,
        existingTermCoverAmount: body.existingTermCoverAmount,
        personalHealthCoverAmount: body.personalHealthCoverAmount,
        employerHealthCoverAmount: body.employerHealthCoverAmount,
        consentGivenAt: new Date(),
      },
      update: {
        existingTermCoverAmount: body.existingTermCoverAmount,
        personalHealthCoverAmount: body.personalHealthCoverAmount,
        employerHealthCoverAmount: body.employerHealthCoverAmount,
        consentGivenAt: new Date(),
      },
    });

    return { financialProfile, insuranceProfile };
  });

  const debts: Debt[] = body.debts.map((debt, i) => ({
    id: `pending-${i}`,
    outstandingAmount: debt.outstandingAmount,
    interestRatePct: debt.interestRatePct,
    tenureMonths: debt.tenureMonths,
  }));

  const gapAnalysis = computeGapAnalysis({
    monthlyIncome: Number(financialProfile.monthlyIncome),
    monthlyExpenses: Number(financialProfile.monthlyExpenses),
    currentSavings: Number(financialProfile.currentSavings),
    existingTermCoverAmount: Number(insuranceProfile.existingTermCoverAmount),
    personalHealthCoverAmount: Number(insuranceProfile.personalHealthCoverAmount),
    employerHealthCoverAmount: Number(insuranceProfile.employerHealthCoverAmount),
    debts,
  });

  const allocation = computeAllocation({
    age: financialProfile.age,
    riskTolerance: financialProfile.riskTolerance as RiskTolerance,
    investmentHorizonYears: financialProfile.investmentHorizonYears,
  });

  await prisma.gapAnalysisResult.create({
    data: {
      userId: user.id,
      emergencyFundTarget: gapAnalysis.emergencyFundTarget,
      emergencyFundCurrent: gapAnalysis.emergencyFundCurrent,
      emergencyFundStatus: gapAnalysis.emergencyFundStatus,
      debtPriorityOrder: gapAnalysis.debtPriorityOrder,
      termCoverGap: gapAnalysis.termCoverGap,
      healthCoverGap: gapAnalysis.healthCoverGap,
      emergencyFundCoveragePct: gapAnalysis.emergencyFundCoveragePct,
      termCoverAdequacyPct: gapAnalysis.termCoverAdequacyPct,
      healthCoverAdequacyPct: gapAnalysis.healthCoverAdequacyPct,
      savingsRatePct: gapAnalysis.savingsRatePct,
      debtToIncomePct: gapAnalysis.debtToIncomePct,
    },
  });

  await prisma.allocationResult.create({
    data: {
      userId: user.id,
      equityPct: allocation.equityPct,
      debtPct: allocation.debtPct,
      goldPct: allocation.goldPct,
    },
  });

  return NextResponse.json({ success: true });
}
