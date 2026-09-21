import { Check, MessageCircle } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { formatINR } from "@/lib/sampleData";
import type { FinancialAnalysis, Plan, PlanDetails } from "@/lib/types";

const NOT_STATED = "Not stated in the document";
const DETAIL_ROWS: [keyof PlanDetails, string][] = [
  ["cover_range", "Cover range"],
  ["eligibility", "Eligibility"],
  ["waiting_periods", "Waiting periods"],
  ["exclusions", "Exclusions"],
  ["riders", "Riders"],
  ["claim_terms", "Claim terms"],
];

interface PlanDetailDialogProps {
  plan: Plan | null;
  analysis: FinancialAnalysis;
  onClose: () => void;
  onAsk: (question: string) => void;
}

export default function PlanDetailDialog({ plan, analysis, onClose, onAsk }: PlanDetailDialogProps) {
  return (
    <Dialog open={plan !== null} onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-2xl" data-testid="plan-detail-dialog">
        {plan && <PlanDetailBody plan={plan} analysis={analysis} onAsk={onAsk} />}
      </DialogContent>
    </Dialog>
  );
}

function PlanDetailBody({ plan, analysis, onAsk }: { plan: Plan; analysis: FinancialAnalysis; onAsk: (question: string) => void }) {
  const isTerm = plan.category === "term";
  const gap = isTerm ? `${analysis.term_gap_crore.toFixed(2)} Cr additional term cover` : `${analysis.health_gap_lakh} L additional health cover`;
  const facts = [
    { label: "Claim settlement ratio", value: plan.csr ?? "Not stated" },
    { label: "Illustrative premium from", value: plan.annual_premium_from !== null ? `${formatINR(plan.annual_premium_from)} / year` : "Not stated" },
    { label: "Cover", value: plan.cover_label ?? "Not stated" },
  ];

  return (
    <>
      <DialogHeader>
        <Badge variant="outline" className={`w-fit ${isTerm ? "border-[#eadcc8] bg-[#fff9ef] text-[#a16207]" : "border-[#d7ebe4] bg-[#eaf6f1] text-[#0d7a5f]"}`}>{isTerm ? "Term insurance" : "Health insurance"}</Badge>
        <DialogTitle className="text-2xl font-semibold" data-testid="plan-detail-name">{plan.name}</DialogTitle>
        <DialogDescription>{plan.provider}</DialogDescription>
      </DialogHeader>

      <div className="grid gap-3 sm:grid-cols-3">
        {facts.map((fact) => (
          <div key={fact.label} className="rounded-lg bg-[#f8f7f4] p-3">
            <p className="text-[10px] font-bold uppercase tracking-wider text-[#8a8f99]">{fact.label}</p>
            <p className="mt-1 text-sm font-semibold text-[#17181c]">{fact.value}</p>
          </div>
        ))}
      </div>
      <p className="text-xs font-semibold text-[#0d7a5f]">Your profile suggests {gap}.</p>

      {plan.highlights.length > 0 && (
        <div className="space-y-2">
          {plan.highlights.map((highlight) => (
            <div key={highlight} className="flex items-center gap-2 text-sm text-[#5c5f66]"><Check className="size-3.5 shrink-0 text-[#0d7a5f]" />{highlight}</div>
          ))}
        </div>
      )}
      {plan.fit && <p className="text-sm leading-6 text-[#5c5f66]">{plan.fit}</p>}

      <dl className="divide-y divide-[#f1efe9] rounded-xl border border-[#e4e1d8]" data-testid="plan-detail-fields">
        {DETAIL_ROWS.map(([key, label]) => {
          const value = plan.details[key];
          return (
            <div key={key} className="grid gap-1 p-3 sm:grid-cols-[9rem_1fr]">
              <dt className="text-xs font-semibold text-[#8a8f99]">{label}</dt>
              <dd className={`text-sm leading-6 ${value === NOT_STATED ? "text-[#8a8f99]" : "text-[#17181c]"}`}>{value}</dd>
            </div>
          );
        })}
      </dl>

      <div className="flex flex-col gap-3 border-t border-[#f1efe9] pt-4 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-[11px] leading-5 text-[#8a8f99]">
          Source document: {plan.source_title}. Extracted from the insurer’s document and reviewed by an admin. Verify the current policy wording before buying.
        </p>
        <Button type="button" className="shrink-0 bg-[#0d7a5f] text-white hover:bg-[#0a624c]" onClick={() => onAsk(`What are the key features, exclusions and waiting periods of ${plan.source_title}?`)} data-testid="plan-detail-ask-button">
          <MessageCircle className="size-4" /> Ask the advisor about this plan
        </Button>
      </div>
    </>
  );
}
