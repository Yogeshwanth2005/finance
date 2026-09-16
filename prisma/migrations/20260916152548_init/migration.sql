-- CreateEnum
CREATE TYPE "RiskTolerance" AS ENUM ('conservative', 'moderate', 'aggressive');

-- CreateEnum
CREATE TYPE "EmergencyFundStatus" AS ENUM ('inadequate', 'building', 'adequate');

-- CreateEnum
CREATE TYPE "FundCategory" AS ENUM ('equity_large_cap', 'equity_diversified', 'debt_short_duration', 'fixed_deposit', 'gold_etf', 'sovereign_gold_bond');

-- CreateEnum
CREATE TYPE "InsurancePlanType" AS ENUM ('term', 'health');

-- CreateTable
CREATE TABLE "users" (
    "id" TEXT NOT NULL,
    "email" TEXT NOT NULL,
    "name" TEXT,
    "hashedPassword" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "users_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "financial_profile" (
    "id" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "age" INTEGER NOT NULL,
    "dependentsCount" INTEGER NOT NULL DEFAULT 0,
    "monthlyIncome" DECIMAL(14,2) NOT NULL,
    "monthlyExpenses" DECIMAL(14,2) NOT NULL,
    "currentSavings" DECIMAL(14,2) NOT NULL,
    "riskTolerance" "RiskTolerance" NOT NULL,
    "investmentHorizonYears" INTEGER NOT NULL,
    "consentGivenAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "financial_profile_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "existing_debt" (
    "id" TEXT NOT NULL,
    "financialProfileId" TEXT NOT NULL,
    "label" TEXT NOT NULL,
    "outstandingAmount" DECIMAL(14,2) NOT NULL,
    "interestRatePct" DECIMAL(5,2) NOT NULL,
    "tenureMonths" INTEGER NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "existing_debt_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "insurance_profile" (
    "id" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "existingTermCoverAmount" DECIMAL(14,2) NOT NULL DEFAULT 0,
    "personalHealthCoverAmount" DECIMAL(14,2) NOT NULL DEFAULT 0,
    "employerHealthCoverAmount" DECIMAL(14,2) NOT NULL DEFAULT 0,
    "consentGivenAt" TIMESTAMP(3),
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "updatedAt" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "insurance_profile_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "allocation_results" (
    "id" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "equityPct" DECIMAL(5,2) NOT NULL,
    "debtPct" DECIMAL(5,2) NOT NULL,
    "goldPct" DECIMAL(5,2) NOT NULL,
    "computedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "allocation_results_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "gap_analysis_results" (
    "id" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "emergencyFundTarget" DECIMAL(14,2) NOT NULL,
    "emergencyFundCurrent" DECIMAL(14,2) NOT NULL,
    "emergencyFundStatus" "EmergencyFundStatus" NOT NULL,
    "debtPriorityOrder" JSONB NOT NULL,
    "termCoverGap" DECIMAL(14,2) NOT NULL,
    "healthCoverGap" DECIMAL(14,2) NOT NULL,
    "emergencyFundCoveragePct" DECIMAL(7,2) NOT NULL,
    "termCoverAdequacyPct" DECIMAL(7,2) NOT NULL,
    "healthCoverAdequacyPct" DECIMAL(7,2) NOT NULL,
    "savingsRatePct" DECIMAL(7,2) NOT NULL,
    "debtToIncomePct" DECIMAL(7,2) NOT NULL,
    "computedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "gap_analysis_results_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "fund_reference" (
    "id" TEXT NOT NULL,
    "schemeCode" TEXT NOT NULL,
    "schemeName" TEXT NOT NULL,
    "amcName" TEXT NOT NULL,
    "category" "FundCategory" NOT NULL,
    "expenseRatio" DECIMAL(5,2) NOT NULL,
    "latestNav" DECIMAL(10,4) NOT NULL,
    "navDate" DATE NOT NULL,
    "externalUrl" TEXT NOT NULL,
    "lastSyncedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "fund_reference_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "insurance_plan_reference" (
    "id" TEXT NOT NULL,
    "insurerName" TEXT NOT NULL,
    "planName" TEXT NOT NULL,
    "planType" "InsurancePlanType" NOT NULL,
    "sumAssuredMin" DECIMAL(14,2) NOT NULL,
    "sumAssuredMax" DECIMAL(14,2) NOT NULL,
    "indicativePremiumNote" TEXT NOT NULL,
    "keyFeatures" JSONB NOT NULL,
    "externalUrl" TEXT NOT NULL,
    "lastUpdatedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "sourceNote" TEXT NOT NULL,

    CONSTRAINT "insurance_plan_reference_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "users_email_key" ON "users"("email");

-- CreateIndex
CREATE UNIQUE INDEX "financial_profile_userId_key" ON "financial_profile"("userId");

-- CreateIndex
CREATE UNIQUE INDEX "insurance_profile_userId_key" ON "insurance_profile"("userId");

-- CreateIndex
CREATE INDEX "allocation_results_userId_computedAt_idx" ON "allocation_results"("userId", "computedAt");

-- CreateIndex
CREATE INDEX "gap_analysis_results_userId_computedAt_idx" ON "gap_analysis_results"("userId", "computedAt");

-- CreateIndex
CREATE UNIQUE INDEX "fund_reference_schemeCode_key" ON "fund_reference"("schemeCode");

-- CreateIndex
CREATE INDEX "fund_reference_category_idx" ON "fund_reference"("category");

-- CreateIndex
CREATE INDEX "insurance_plan_reference_planType_idx" ON "insurance_plan_reference"("planType");

-- AddForeignKey
ALTER TABLE "financial_profile" ADD CONSTRAINT "financial_profile_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "existing_debt" ADD CONSTRAINT "existing_debt_financialProfileId_fkey" FOREIGN KEY ("financialProfileId") REFERENCES "financial_profile"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "insurance_profile" ADD CONSTRAINT "insurance_profile_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "allocation_results" ADD CONSTRAINT "allocation_results_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "gap_analysis_results" ADD CONSTRAINT "gap_analysis_results_userId_fkey" FOREIGN KEY ("userId") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;
