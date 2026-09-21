import { useState } from "react";
import type { ReactNode } from "react";
import { useMutation } from "@tanstack/react-query";
import { Sparkles } from "lucide-react";
import { toast } from "sonner";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ApiError, apiPatch, apiPost, apiPut } from "@/lib/api";
import type { DocumentRecord, PlanCardData, PlanDetails } from "@/lib/types";

const NOT_STATED = "Not stated in the document";
const DETAIL_FIELDS: [keyof PlanDetails, string][] = [
  ["cover_range", "Cover range"],
  ["eligibility", "Eligibility"],
  ["waiting_periods", "Waiting periods"],
  ["exclusions", "Exclusions"],
  ["riders", "Riders"],
  ["claim_terms", "Claim terms"],
];

interface FormState {
  category: "term" | "health";
  name: string;
  provider: string;
  csr: string;
  premium: string;
  coverLabel: string;
  highlights: string;
  fit: string;
  details: PlanDetails;
}

const blankDetails = (): PlanDetails => ({ eligibility: NOT_STATED, cover_range: NOT_STATED, waiting_periods: NOT_STATED, exclusions: NOT_STATED, riders: NOT_STATED, claim_terms: NOT_STATED });

function toForm(plan: PlanCardData | null): FormState {
  if (!plan) return { category: "term", name: "", provider: "", csr: "", premium: "", coverLabel: "", highlights: "", fit: "", details: blankDetails() };
  return {
    category: plan.category,
    name: plan.name,
    provider: plan.provider === NOT_STATED ? "" : plan.provider,
    csr: plan.csr ?? "",
    premium: plan.annual_premium_from === null ? "" : String(plan.annual_premium_from),
    coverLabel: plan.cover_label ?? "",
    highlights: plan.highlights.join("\n"),
    fit: plan.fit ?? "",
    details: { ...plan.details },
  };
}

// Mirrors the server's limits so mistakes show up before the request; the server still validates.
function toCard(form: FormState): { card: PlanCardData } | { error: string } {
  const name = form.name.trim();
  if (!name) return { error: "Give the plan a name" };
  const csr = form.csr.trim();
  if (csr && !/^\d{1,3}(\.\d{1,2})?%$/.test(csr)) return { error: "Claim settlement ratio must look like 98.5%" };
  const premiumText = form.premium.trim();
  const premium = premiumText ? Number(premiumText) : null;
  if (premium !== null && (!Number.isInteger(premium) || premium <= 0 || premium >= 10_000_000)) return { error: "Premium must be a whole number of rupees per year" };
  const highlights = form.highlights.split("\n").map((line) => line.trim()).filter(Boolean);
  if (highlights.length > 6) return { error: "Keep at most 6 highlights" };
  const details = Object.fromEntries(DETAIL_FIELDS.map(([key]) => [key, form.details[key].trim() || NOT_STATED])) as unknown as PlanDetails;
  return {
    card: {
      category: form.category,
      name,
      provider: form.provider.trim() || NOT_STATED,
      csr: csr || null,
      annual_premium_from: premium,
      cover_label: form.coverLabel.trim() || null,
      highlights,
      fit: form.fit.trim() || null,
      details,
    },
  };
}

function errorMessage(error: unknown, fallback: string) {
  if (error instanceof ApiError) {
    const detail = (error.body as { detail?: unknown } | null)?.detail;
    return typeof detail === "string" ? detail : fallback;
  }
  return error instanceof Error ? error.message : fallback;
}

function Field({ label, hint, children }: { label: string; hint?: string; children: ReactNode }) {
  return (
    <label className="block space-y-1.5">
      <span className="text-xs font-semibold text-[#5c5f66]">{label}</span>
      {children}
      {hint && <span className="block text-[10px] text-[#8a8f99]">{hint}</span>}
    </label>
  );
}

interface PlanReviewDialogProps {
  document: DocumentRecord | null;
  onClose: () => void;
  onChanged: () => void;
}

export default function PlanReviewDialog({ document, onClose, onChanged }: PlanReviewDialogProps) {
  return (
    <Dialog open={document !== null} onOpenChange={(open) => { if (!open) onClose(); }}>
      <DialogContent className="max-h-[88vh] overflow-y-auto sm:max-w-3xl" data-testid="plan-review-dialog">
        {/* Keyed by the stored card so the form resets after a save or a re-extraction. */}
        {document && <PlanReviewForm key={`${document.id}:${JSON.stringify(document.plan)}`} document={document} onChanged={onChanged} />}
      </DialogContent>
    </Dialog>
  );
}

function PlanReviewForm({ document, onChanged }: { document: DocumentRecord; onChanged: () => void }) {
  const [form, setForm] = useState(() => toForm(document.plan));
  const set = <K extends keyof FormState>(key: K, value: FormState[K]) => setForm((current) => ({ ...current, [key]: value }));
  const setDetail = (key: keyof PlanDetails, value: string) => setForm((current) => ({ ...current, details: { ...current.details, [key]: value } }));
  const published = document.plan_status === "published";

  const save = useMutation({
    mutationFn: async (status: "draft" | "published" | null) => {
      const result = toCard(form);
      if ("error" in result) throw new Error(result.error);
      let saved = await apiPut<DocumentRecord>(`/admin/documents/${document.id}/plan`, result.card);
      if (status && saved.plan_status !== status) saved = await apiPatch<DocumentRecord>(`/admin/documents/${document.id}/plan/status`, { status });
      return saved;
    },
    onSuccess: (saved) => {
      onChanged();
      toast.success(saved.plan_status === "published" ? "Card saved and visible to customers" : "Card saved as a draft");
    },
    onError: (error) => toast.error(errorMessage(error, "Could not save the card")),
  });

  const extract = useMutation({
    mutationFn: () => apiPost<DocumentRecord>(`/admin/documents/${document.id}/plan/extract`),
    onSuccess: () => {
      onChanged();
      toast.success("Extracted a fresh draft. Check every value against the document.");
    },
    onError: (error) => toast.error(errorMessage(error, "Could not extract plan details")),
  });

  const runExtraction = () => {
    if (document.plan && !window.confirm("Replace the current card with a fresh AI extraction? Your edits will be lost and the card returns to draft.")) return;
    extract.mutate();
  };

  const busy = save.isPending || extract.isPending;

  return (
    <>
      <DialogHeader>
        <div className="flex flex-wrap items-center gap-2">
          <DialogTitle data-testid="plan-review-title">Plan card for “{document.title}”</DialogTitle>
          <Badge variant="outline" className={published ? "border-[#d7ebe4] bg-[#eaf6f1] text-[#0d7a5f]" : document.plan ? "border-[#eadcc8] bg-[#fff9ef] text-[#a16207]" : "border-[#e4e1d8] bg-[#f1efe9] text-[#8a8f99]"} data-testid="plan-review-status">
            {published ? "published" : document.plan ? "draft" : "no card yet"}
          </Badge>
        </div>
        <DialogDescription>
          {published ? "Customers see this card on the Insurance page." : "Customers do not see this card until you publish it."} AI extraction can misread tables: check every number against the source document before publishing.
        </DialogDescription>
      </DialogHeader>

      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Type">
          <select value={form.category} onChange={(event) => set("category", event.target.value as "term" | "health")} className="h-9 w-full rounded-lg border border-input bg-transparent px-2.5 text-sm" data-testid="plan-review-category">
            <option value="term">Term insurance</option>
            <option value="health">Health insurance</option>
          </select>
        </Field>
        <Field label="Plan name"><Input value={form.name} onChange={(event) => set("name", event.target.value)} maxLength={120} data-testid="plan-review-name-input" /></Field>
        <Field label="Insurer"><Input value={form.provider} onChange={(event) => set("provider", event.target.value)} maxLength={120} placeholder="HDFC Life" /></Field>
        <Field label="Cover label"><Input value={form.coverLabel} onChange={(event) => set("coverLabel", event.target.value)} maxLength={160} placeholder="Term cover ₹1 crore" /></Field>
        <Field label="Claim settlement ratio" hint="Leave blank if the document does not state it"><Input value={form.csr} onChange={(event) => set("csr", event.target.value)} maxLength={12} placeholder="98.5%" data-testid="plan-review-csr-input" /></Field>
        <Field label="Illustrative premium from (₹ / year)" hint="Leave blank if the document does not state it"><Input inputMode="numeric" value={form.premium} onChange={(event) => set("premium", event.target.value)} placeholder="18500" data-testid="plan-review-premium-input" /></Field>
      </div>

      <Field label="Highlights" hint="One per line, up to 6; the first 4 show on the card"><Textarea value={form.highlights} onChange={(event) => set("highlights", event.target.value)} rows={3} /></Field>
      <Field label="Who it suits"><Textarea value={form.fit} onChange={(event) => set("fit", event.target.value)} maxLength={300} rows={2} /></Field>

      <div className="grid gap-4 sm:grid-cols-2">
        {DETAIL_FIELDS.map(([key, label]) => (
          <Field key={key} label={label}><Textarea value={form.details[key]} onChange={(event) => setDetail(key, event.target.value)} maxLength={600} rows={3} /></Field>
        ))}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[#f1efe9] pt-4">
        <Button type="button" variant="outline" onClick={runExtraction} disabled={busy} data-testid="plan-review-extract-button">
          <Sparkles className="size-4" /> {extract.isPending ? "Extracting…" : document.plan ? "Re-extract with AI" : "Extract with AI"}
        </Button>
        <div className="flex flex-wrap gap-2">
          {published ? (
            <>
              <Button type="button" variant="outline" onClick={() => save.mutate("draft")} disabled={busy} data-testid="plan-review-unpublish-button">Unpublish</Button>
              <Button type="button" className="bg-[#0d7a5f] text-white hover:bg-[#0a624c]" onClick={() => save.mutate(null)} disabled={busy} data-testid="plan-review-save-button">Save changes</Button>
            </>
          ) : (
            <>
              <Button type="button" variant="outline" onClick={() => save.mutate("draft")} disabled={busy} data-testid="plan-review-save-button">Save draft</Button>
              <Button type="button" className="bg-[#0d7a5f] text-white hover:bg-[#0a624c]" onClick={() => save.mutate("published")} disabled={busy} data-testid="plan-review-publish-button">Save &amp; publish</Button>
            </>
          )}
        </div>
      </div>
    </>
  );
}
