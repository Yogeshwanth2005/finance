import { useState } from "react";
import type { FormEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { Bot, Check, GitCompareArrows, Info, MessageCircle, Send, Shield, Sparkles, X } from "lucide-react";

import AppShell from "@/components/AppShell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { apiGet, apiStreamPost } from "@/lib/api";
import { formatINR, SAMPLE_PROFILE_RESPONSE } from "@/lib/sampleData";
import type { ChatMessageRecord, Plan, ProfileResponse } from "@/lib/types";
import { Navigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { useI18n } from "@/lib/i18n";

type ChatMessage = { role: "advisor" | "you"; text: string; sources?: string[] };

const cleanMarkdown = (value: string) => value.replace(/\*\*/g, "").trim();

function splitTableRow(line: string) {
  return line.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((cell) => cleanMarkdown(cell));
}

function MessageContent({ text }: { text: string }) {
  const lines = text.replace(/```(?:markdown)?/gi, "").split("\n");
  const separatorIndex = lines.findIndex((line) => {
    const cells = splitTableRow(line);
    return cells.length > 1 && cells.every((cell) => /^:?-{3,}:?$/.test(cell));
  });
  if (separatorIndex < 1) return <p className="whitespace-pre-wrap">{cleanMarkdown(text)}</p>;

  const headers = splitTableRow(lines[separatorIndex - 1]);
  let tableEnd = separatorIndex + 1;
  const rows: string[][] = [];
  while (tableEnd < lines.length && lines[tableEnd].includes("|")) {
    rows.push(splitTableRow(lines[tableEnd]));
    tableEnd += 1;
  }
  const before = cleanMarkdown(lines.slice(0, separatorIndex - 1).join("\n"));
  const after = cleanMarkdown(lines.slice(tableEnd).join("\n"));

  return <div className="space-y-3">{before && <p className="whitespace-pre-wrap">{before}</p>}<div className="overflow-x-auto rounded-lg border border-[#d8d5cd] bg-white" data-testid="chat-comparison-table"><table className="w-full min-w-[520px] border-collapse text-left text-[11px]"><thead className="bg-[#f1efe9] text-[#17181c]"><tr>{headers.map((header, index) => <th key={`${header}-${index}`} className="border-b border-r border-[#d8d5cd] px-3 py-2 font-semibold last:border-r-0">{header}</th>)}</tr></thead><tbody>{rows.map((row, rowIndex) => <tr key={rowIndex} className="border-b border-[#e4e1d8] last:border-b-0">{headers.map((_, cellIndex) => <td key={cellIndex} className="border-r border-[#e4e1d8] px-3 py-2 align-top text-[#5c5f66] last:border-r-0">{row[cellIndex] || "Not stated"}</td>)}</tr>)}</tbody></table></div>{after && <p className="whitespace-pre-wrap">{after}</p>}</div>;
}

export default function Insurance() {
  const { user } = useAuth();
  const { t } = useI18n();
  const profileQuery = useQuery({ queryKey: ["profile"], queryFn: () => apiGet<ProfileResponse>("/profile"), retry: false });
  const response = profileQuery.data ?? SAMPLE_PROFILE_RESPONSE;
  const [filter, setFilter] = useState<"all" | "term" | "health">("all");
  const [compare, setCompare] = useState(false);
  const [question, setQuestion] = useState("");
  const history = useQuery({ queryKey: ["chat-history"], queryFn: () => apiGet<ChatMessageRecord[]>("/chat/history"), retry: false });
  const [localMessages, setLocalMessages] = useState<ChatMessage[]>([]);
  const [streaming, setStreaming] = useState(false);
  const savedMessages = history.data?.map(({ role, text, sources }) => ({ role, text, sources })) ?? [];
  const greeting: ChatMessage = { role: "advisor", text: `I’ve read ${response.profile.full_name || "your"} family profile. Ask me about an insurance plan indexed by the admin.` };
  const messages: ChatMessage[] = localMessages.length > 0 ? localMessages : savedMessages.length > 0 ? savedMessages : [greeting];
  const plans = response.plans.filter((plan) => filter === "all" || plan.category === filter);
  const prompts = [t("promptTerm"), t("promptCompare"), t("promptCritical")];
  if (user && user.role !== "admin" && !user.profile_complete) return <Navigate to="/" replace />;

  const ask = async (value: string) => {
    const cleaned = value.trim();
    if (cleaned.length < 2 || streaming) return;
    const startingMessages = [...messages, { role: "you" as const, text: cleaned }, { role: "advisor" as const, text: "", sources: [] }];
    setLocalMessages(startingMessages);
    setQuestion("");
    setStreaming(true);
    try {
      const result = await apiStreamPost("/chat/stream", { question: cleaned }, (content) => {
        setLocalMessages((current) => current.map((message, index) => index === current.length - 1 ? { ...message, text: message.text + content } : message));
      });
      setLocalMessages((current) => current.map((message, index) => index === current.length - 1 ? { ...message, sources: result.sources } : message));
    } catch {
      setLocalMessages((current) => current.map((message, index) => index === current.length - 1 ? { ...message, text: "I could not reach the grounded document service. Please try again." } : message));
    } finally {
      setStreaming(false);
    }
  };

  const submitQuestion = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    ask(question);
  };

  return (
    <AppShell>
      <section className="mx-auto max-w-7xl px-4 pb-16 pt-10 sm:px-6 lg:px-8 lg:pt-14">
        <div className="grid gap-8 lg:grid-cols-[1fr_0.48fr] lg:items-end">
          <div data-testid="insurance-header-copy"><Badge variant="outline" className="border-[#d7ebe4] bg-[#eaf6f1] text-[#0d7a5f]" data-testid="insurance-page-badge"><Shield className="size-3" /> Protection marketplace</Badge><h1 className="mt-5 max-w-3xl font-heading text-4xl font-bold tracking-[-0.04em] text-[#17181c] sm:text-5xl" data-testid="insurance-page-heading">{t("insuranceTitle")}</h1><p className="mt-4 max-w-2xl text-base leading-7 text-[#5c5f66]" data-testid="insurance-page-description">{t("insuranceDescription")}</p></div>
          <Card className="border-[#e4e1d8] bg-[#17181c] text-white shadow-none" data-testid="insurance-gap-summary-card"><CardContent className="p-6"><p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#a8d9c8]" data-testid="insurance-gap-summary-label">Profile-led starting point</p><div className="mt-5 grid grid-cols-2 gap-5"><div><p className="font-mono text-2xl font-bold" data-testid="insurance-term-gap-summary">{response.analysis.term_gap_crore.toFixed(2)} Cr</p><p className="mt-1 text-xs text-white/55">additional term</p></div><div><p className="font-mono text-2xl font-bold" data-testid="insurance-health-gap-summary">{response.analysis.health_gap_lakh} L</p><p className="mt-1 text-xs text-white/55">additional health</p></div></div></CardContent></Card>
        </div>

        <div className="mt-12 flex flex-col justify-between gap-4 border-b border-[#e4e1d8] pb-4 sm:flex-row sm:items-end" data-testid="insurance-plans-toolbar"><div><p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#8a8f99]">Compare with context</p><h2 className="mt-2 font-heading text-2xl font-semibold text-[#17181c]" data-testid="insurance-plans-heading">Illustrative plan shortlist</h2></div><div className="flex items-center gap-2"><div className="flex rounded-lg border border-[#e4e1d8] bg-white p-1" data-testid="insurance-filter-tabs">{(["all", "term", "health"] as const).map((item) => <button type="button" key={item} onClick={() => setFilter(item)} className={`rounded-md px-3 py-1.5 text-xs font-semibold capitalize transition-colors ${filter === item ? "bg-[#17181c] text-white" : "text-[#5c5f66] hover:bg-[#f1efe9]"}`} data-testid={`insurance-filter-${item}-button`}>{item}</button>)}</div><Button variant={compare ? "default" : "outline"} size="sm" onClick={() => setCompare((current) => !current)} data-testid="insurance-compare-button"><GitCompareArrows className="size-3.5" /> {compare ? "Close compare" : "Compare two"}</Button></div></div>

        <div className="mt-6 grid gap-4 md:grid-cols-2">
          {plans.map((plan) => <PlanCard key={plan.id} plan={plan} analysis={response.analysis} />)}
        </div>

        {compare && <Card className="mt-6 border-[#c8c4b7] bg-white shadow-none" data-testid="insurance-comparison-drawer"><CardHeader className="flex-row items-start justify-between p-6 pb-3"><div><p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#0d7a5f]">Side-by-side</p><CardTitle className="mt-2 text-xl font-semibold">What to inspect before buying</CardTitle></div><button type="button" onClick={() => setCompare(false)} className="rounded-md p-1 text-[#8a8f99] hover:bg-[#f1efe9]" data-testid="insurance-comparison-close-button"><X className="size-4" /></button></CardHeader><CardContent className="p-6 pt-2"><div className="grid gap-3 text-sm sm:grid-cols-3"><div className="rounded-lg bg-[#f8f7f4] p-4"><p className="text-xs font-semibold text-[#8a8f99]">Term plans</p><p className="mt-2 font-semibold text-[#17181c]">Income replacement</p><p className="mt-1 text-xs leading-5 text-[#5c5f66]">Check tenure, payout choice, exclusions and rider pricing.</p></div><div className="rounded-lg bg-[#f8f7f4] p-4"><p className="text-xs font-semibold text-[#8a8f99]">Health plans</p><p className="mt-2 font-semibold text-[#17181c]">Claim usability</p><p className="mt-1 text-xs leading-5 text-[#5c5f66]">Check waiting periods, co-pay, room limits and restoration.</p></div><div className="rounded-lg bg-[#f8f7f4] p-4"><p className="text-xs font-semibold text-[#8a8f99]">Every plan</p><p className="mt-2 font-semibold text-[#17181c]">Service quality</p><p className="mt-1 text-xs leading-5 text-[#5c5f66]">CSR is only one signal; read current policy documents.</p></div></div></CardContent></Card>}

        <div className="mt-16 grid gap-6 lg:grid-cols-[0.92fr_1.08fr]" id="cfo-chatbot">
          <Card className="border-[#e4e1d8] bg-[#f1efe9] shadow-none" data-testid="insurance-chatbot-context-card"><CardContent className="p-6 sm:p-8"><div className="flex size-11 items-center justify-center rounded-2xl bg-[#0d7a5f] text-white"><Sparkles className="size-5" /></div><p className="mt-6 text-[10px] font-bold uppercase tracking-[0.16em] text-[#0d7a5f]" data-testid="insurance-chatbot-eyebrow">Your context-aware guide</p><h2 className="mt-3 font-heading text-3xl font-semibold tracking-tight text-[#17181c]" data-testid="insurance-chatbot-heading">Ask the uncomfortable insurance questions.</h2><p className="mt-4 text-sm leading-6 text-[#5c5f66]" data-testid="insurance-chatbot-description">This guide uses the saved profile and the same formulas as your dashboard. It is a decision aid, not a salesperson.</p><div className="mt-8 space-y-3 text-xs text-[#5c5f66]"><div className="flex gap-3"><Check className="size-4 shrink-0 text-[#0d7a5f]" /> Explains the number behind each recommendation</div><div className="flex gap-3"><Check className="size-4 shrink-0 text-[#0d7a5f]" /> Helps compare wording, not just premium</div><div className="flex gap-3"><Check className="size-4 shrink-0 text-[#0d7a5f]" /> Keeps your emergency fund in the conversation</div></div><a href="#cfo-chatbot" className="mt-8 inline-flex items-center gap-2 text-xs font-bold text-[#0d7a5f]" data-testid="nav-ai-chatbot-link"><MessageCircle className="size-4" /> CFO chat is open beside this panel</a></CardContent></Card>

              <Card className="border-[#e4e1d8] bg-white shadow-none" data-testid="insurance-chatbot-card"><CardHeader className="border-b border-[#f1efe9] p-5 sm:p-6"><div className="flex items-center justify-between"><div className="flex items-center gap-3"><span className="flex size-9 items-center justify-center rounded-xl bg-[#eaf6f1] text-[#0d7a5f]"><Bot className="size-4" /></span><div><CardTitle className="text-base font-semibold" data-testid="insurance-chatbot-title">{t("chatTitle")}</CardTitle><p className="mt-0.5 text-[11px] text-[#8a8f99]" data-testid="insurance-chatbot-status">{t("chatStatus")}</p></div></div><Badge variant="outline" className="border-[#d7ebe4] bg-[#eaf6f1] text-[#0d7a5f]" data-testid="insurance-chatbot-grounded-badge">{t("grounded")}</Badge></div></CardHeader><CardContent className="flex min-h-[430px] flex-col p-5 sm:p-6"><div className="flex-1 space-y-4 overflow-y-auto" data-testid="insurance-chatbot-message-list">{messages.map((message, index) => <div key={`${message.role}-${index}`} className={`flex ${message.role === "you" ? "justify-end" : "justify-start"}`} data-testid={`insurance-chatbot-message-${index}`}><div className={`max-w-[88%] rounded-2xl px-4 py-3 text-sm leading-6 ${message.role === "you" ? "rounded-br-md bg-[#17181c] text-white" : "rounded-bl-md bg-[#f1efe9] text-[#5c5f66]"}`}><MessageContent text={message.text || "Reading indexed sources…"} />{message.sources && message.sources.length > 0 && <div className="mt-3 border-t border-[#d8d5cd] pt-2 text-[10px] font-semibold text-[#0d7a5f]" data-testid={`insurance-chatbot-sources-${index}`}>Sources: {message.sources.join(", ")}</div>}</div></div>)}{streaming && <div className="text-[10px] font-semibold text-[#0d7a5f]" data-testid="insurance-chatbot-typing">Streaming grounded answer…</div>}</div><div className="mt-5 flex gap-2 overflow-x-auto pb-1" data-testid="insurance-chatbot-prompt-list">{prompts.map((prompt, index) => <button type="button" key={prompt} onClick={() => void ask(prompt)} className="shrink-0 rounded-full border border-[#e4e1d8] bg-white px-3 py-2 text-[11px] font-semibold text-[#5c5f66] transition-colors hover:border-[#0d7a5f] hover:text-[#0d7a5f]" data-testid={`rag-prompt-chip-${index + 1}`}>{prompt}</button>)}</div><form onSubmit={submitQuestion} className="mt-4 flex gap-2" data-testid="insurance-chatbot-form"><Input value={question} onChange={(event) => setQuestion(event.target.value)} placeholder={t("chatPlaceholder")} className="h-10" data-testid="rag-chatbot-input-field" /><Button type="submit" size="icon" className="size-10 bg-[#0d7a5f] text-white hover:bg-[#0a624c]" disabled={streaming || question.trim().length < 2} data-testid="rag-chatbot-send-button"><Send className="size-4" /></Button></form><p className="mt-3 flex items-center gap-1.5 text-[10px] text-[#8a8f99]" data-testid="insurance-chatbot-disclaimer"><Info className="size-3" /> {t("chatRule")}</p></CardContent></Card>
        </div>
      </section>
    </AppShell>
  );
}

function PlanCard({ plan, analysis }: { plan: Plan; analysis: ProfileResponse["analysis"] }) {
  const isTerm = plan.category === "term";
  return <Card className="border-[#e4e1d8] bg-white shadow-none transition-transform hover:-translate-y-0.5" data-testid={`insurance-plan-card-${plan.id}`}><CardHeader className="p-6 pb-3"><div className="flex items-start justify-between gap-3"><div><Badge variant="outline" className={isTerm ? "border-[#eadcc8] bg-[#fff9ef] text-[#a16207]" : "border-[#d7ebe4] bg-[#eaf6f1] text-[#0d7a5f]"} data-testid={`insurance-plan-${plan.id}-category`}>{isTerm ? "Term insurance" : "Health insurance"}</Badge><CardTitle className="mt-4 text-xl font-semibold text-[#17181c]" data-testid={`insurance-plan-${plan.id}-name`}>{plan.name}</CardTitle><p className="mt-1 text-xs text-[#8a8f99]" data-testid={`insurance-plan-${plan.id}-provider`}>{plan.provider}</p></div><div className="rounded-xl bg-[#f8f7f4] px-3 py-2 text-right"><p className="font-mono text-lg font-bold text-[#17181c]" data-testid={`insurance-plan-${plan.id}-csr`}>{plan.csr}</p><p className="text-[9px] font-bold uppercase tracking-wider text-[#8a8f99]">CSR</p></div></div></CardHeader><CardContent className="p-6 pt-3"><div className="flex items-end justify-between border-b border-[#f1efe9] pb-4"><div><p className="text-[10px] uppercase tracking-wider text-[#8a8f99]">Illustrative from</p><p className="mt-1 font-mono text-xl font-bold text-[#17181c]" data-testid={`insurance-plan-${plan.id}-premium`}>{formatINR(plan.annual_premium_from)}<span className="ml-1 font-sans text-[11px] font-normal text-[#8a8f99]">/ year</span></p></div><p className="text-right text-xs font-semibold text-[#0d7a5f]" data-testid={`insurance-plan-${plan.id}-fit`}>{isTerm ? `${analysis.term_gap_crore.toFixed(2)} Cr gap` : `${analysis.health_gap_lakh} L gap`}</p></div><div className="mt-4 space-y-2">{plan.highlights.map((highlight) => <div key={highlight} className="flex items-center gap-2 text-xs text-[#5c5f66]" data-testid={`insurance-plan-${plan.id}-highlight-${highlight.toLowerCase().replaceAll(" ", "-")}`}><Check className="size-3.5 text-[#0d7a5f]" />{highlight}</div>)}</div><p className="mt-5 text-xs leading-5 text-[#8a8f99]" data-testid={`insurance-plan-${plan.id}-description`}>{plan.fit}</p></CardContent></Card>;
}