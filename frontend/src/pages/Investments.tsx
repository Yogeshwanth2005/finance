import { useQuery } from "@tanstack/react-query";
import { Navigate } from "react-router-dom";

import AppShell from "@/components/AppShell";
import FundExplorer from "@/components/FundExplorer";
import SurplusDirectionCard, { type InvestmentBlock } from "@/components/SurplusDirectionCard";
import { Badge } from "@/components/ui/badge";
import { apiGet } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";
import { SAMPLE_PROFILE_RESPONSE } from "@/lib/sampleData";
import type { ProfileResponse } from "@/lib/types";

export default function Investments() {
  const { user } = useAuth();
  const { t } = useI18n();
  const query = useQuery({ queryKey: ["profile"], queryFn: () => apiGet<ProfileResponse>("/profile"), retry: false });
  if (user && user.role !== "admin" && !user.profile_complete) return <Navigate to="/" replace />;
  const { profile, analysis } = query.data ?? SAMPLE_PROFILE_RESPONSE;
  const isSample = !query.data;
  const block: InvestmentBlock = analysis.emergency_gap > 0
    ? "emergency"
    : analysis.annual_insurance_budget > analysis.annual_surplus_before_protection || analysis.investable_surplus <= 0
      ? "insurance"
      : null;

  return (
    <AppShell>
      <section className="mx-auto max-w-7xl px-4 pb-12 pt-10 sm:px-6 lg:px-8 lg:pt-14">
        <div className="border-b border-[#e4e1d8] pb-8" data-testid="investments-header-copy">
          <div className="mb-4 flex items-center gap-2"><Badge variant="outline" className="border-[#d7ebe4] bg-[#eaf6f1] text-[#0d7a5f]" data-testid="investments-status-badge">{isSample ? "Sample benchmark" : "Profile analysed"}</Badge><span className="text-xs text-[#8a8f99]">India / INR · rule-based view</span></div>
          <h1 className="font-heading text-4xl font-bold tracking-[-0.04em] text-[#17181c] sm:text-5xl" data-testid="investments-heading">{t("investmentsPage")}</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-[#5c5f66]" data-testid="investments-subheading">Protect, then invest — in that order. Here is what your surplus could do once protection is covered, and real funds to browse for each slice.</p>
        </div>

        <div className="mt-8">
          <SurplusDirectionCard profile={profile} analysis={analysis} block={block} />
        </div>

        <FundExplorer investmentBlocked={block !== null} />
      </section>
    </AppShell>
  );
}
