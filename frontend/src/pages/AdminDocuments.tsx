import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ClipboardCheck, Database, ExternalLink, FileText, Globe2, LockKeyhole, MessageCircle, Power, Trash2, UploadCloud, Users } from "lucide-react";
import { toast } from "sonner";

import AppShell from "@/components/AppShell";
import PlanReviewDialog from "@/components/PlanReviewDialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { apiDelete, apiGet, apiPatch, apiPostForm } from "@/lib/api";
import type { AdminOverview, AdminQuestionRecord, AdminUserRecord, DocumentRecord } from "@/lib/types";

type DetailKind = "customers" | "completed" | "chunks" | "questions";

const PLAN_LABEL: Record<DocumentRecord["plan_status"], string> = { none: "no card", draft: "draft card", published: "card live" };
const PLAN_BADGE: Record<DocumentRecord["plan_status"], string> = {
  none: "border-[#e4e1d8] bg-[#f1efe9] text-[#8a8f99]",
  draft: "border-[#eadcc8] bg-[#fff9ef] text-[#a16207]",
  published: "border-[#d7ebe4] bg-[#eaf6f1] text-[#0d7a5f]",
};

function AdminMetric({ label, value, icon: Icon, testId, onClick }: { label: string; value: number; icon: typeof Users; testId: string; onClick: () => void }) {
  return <button type="button" onClick={onClick} className="text-left" data-testid={`${testId}-button`}><Card className="border-[#e4e1d8] bg-white shadow-none transition-transform hover:-translate-y-0.5 hover:border-[#c8c4b7]" data-testid={testId}><CardContent className="p-5"><div className="flex items-center justify-between text-[#8a8f99]"><span className="text-[10px] font-bold uppercase tracking-[0.16em]">{label}</span><Icon className="size-4" /></div><p className="mt-4 font-mono text-2xl font-bold text-[#17181c]" data-testid={`${testId}-value`}>{value}</p><p className="mt-2 text-[10px] font-semibold text-[#0d7a5f]">View details</p></CardContent></Card></button>;
}

export default function AdminDocuments() {
  const queryClient = useQueryClient();
  const overview = useQuery({ queryKey: ["admin-overview"], queryFn: () => apiGet<AdminOverview>("/admin/overview"), retry: false });
  const documents = useQuery({ queryKey: ["admin-documents"], queryFn: () => apiGet<DocumentRecord[]>("/admin/documents"), retry: false });
  const users = useQuery({ queryKey: ["admin-users"], queryFn: () => apiGet<AdminUserRecord[]>("/admin/users"), retry: false });
  const questions = useQuery({ queryKey: ["admin-questions"], queryFn: () => apiGet<AdminQuestionRecord[]>("/admin/questions"), retry: false });
  const [title, setTitle] = useState("");
  const [url, setUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [detail, setDetail] = useState<DetailKind | null>(null);
  const [reviewingId, setReviewingId] = useState<string | null>(null);
  const reviewing = documents.data?.find((document) => document.id === reviewingId) ?? null;

  const refreshAdmin = () => {
    queryClient.invalidateQueries({ queryKey: ["admin-documents"] });
    queryClient.invalidateQueries({ queryKey: ["admin-overview"] });
    queryClient.invalidateQueries({ queryKey: ["plans"] });
  };

  const upload = useMutation({
    mutationFn: () => {
      const form = new FormData();
      form.append("title", title);
      if (url) form.append("source_url", url);
      if (file) form.append("file", file);
      return apiPostForm<DocumentRecord>("/admin/documents", form);
    },
    onSuccess: (created) => {
      refreshAdmin();
      setTitle(""); setUrl(""); setFile(null);
      toast.success(created.plan ? "Document indexed. A draft plan card is ready to review." : "Document indexed and activated");
    },
    onError: () => toast.error("We could not index that source. Check its format and try again."),
  });

  const toggle = useMutation({
    mutationFn: ({ document, enabled }: { document: DocumentRecord; enabled: boolean }) => apiPatch<DocumentRecord>(`/admin/documents/${document.id}/status`, { enabled }),
    onSuccess: (document) => { refreshAdmin(); toast.success(`${document.title} ${document.enabled ? "activated" : "paused"}`); },
    onError: () => toast.error("Could not change source status"),
  });

  const remove = useMutation({
    mutationFn: (document: DocumentRecord) => apiDelete<void>(`/admin/documents/${document.id}`),
    onSuccess: () => { refreshAdmin(); toast.success("Document and vector chunks deleted"); },
    onError: () => toast.error("Could not delete that document"),
  });

  const confirmDelete = (document: DocumentRecord) => {
    if (window.confirm(`Delete “${document.title}” and all of its vector chunks? This cannot be undone.`)) remove.mutate(document);
  };

  const stats = overview.data;
  const completedUsers = users.data?.filter((account) => account.profile_complete) ?? [];
  const detailTitles: Record<DetailKind, string> = {
    customers: "Customer accounts",
    completed: "Completed financial profiles",
    chunks: "Vector chunks by source",
    questions: "Recent customer questions",
  };

  return (
    <AppShell>
      <section className="mx-auto max-w-7xl px-4 pb-16 pt-10 sm:px-6 lg:px-8 lg:pt-14">
        <div className="flex flex-col justify-between gap-5 border-b border-[#e4e1d8] pb-8 sm:flex-row sm:items-end">
          <div data-testid="admin-documents-header">
            <Badge variant="outline" className="border-[#eadcc8] bg-[#fff9ef] text-[#a16207]" data-testid="admin-documents-badge"><LockKeyhole className="size-3" /> Admin operations</Badge>
            <h1 className="mt-4 font-heading text-4xl font-bold tracking-[-0.04em]" data-testid="admin-documents-heading">Insurance knowledge control</h1>
            <p className="mt-3 max-w-2xl text-sm leading-6 text-[#5c5f66]" data-testid="admin-documents-description">Manage trusted plan sources, monitor customer readiness, and control exactly what the RAG advisor can retrieve.</p>
          </div>
          <div className="rounded-xl border border-[#d7ebe4] bg-[#eaf6f1] px-4 py-3 text-xs font-semibold text-[#0d7a5f]" data-testid="admin-rag-status">{stats?.active_documents ?? 0} active sources · MongoDB vectors</div>
        </div>

        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4" data-testid="admin-overview-metrics">
          <AdminMetric label="Customer accounts" value={stats?.total_users ?? 0} icon={Users} testId="admin-users-metric" onClick={() => setDetail("customers")} />
          <AdminMetric label="Completed profiles" value={stats?.completed_profiles ?? 0} icon={LockKeyhole} testId="admin-profiles-metric" onClick={() => setDetail("completed")} />
          <AdminMetric label="Active vector chunks" value={stats?.vector_chunks ?? 0} icon={Database} testId="admin-chunks-metric" onClick={() => setDetail("chunks")} />
          <AdminMetric label="Questions asked" value={stats?.user_questions ?? 0} icon={MessageCircle} testId="admin-questions-metric" onClick={() => setDetail("questions")} />
        </div>

        <div className="mt-8 grid gap-6 lg:grid-cols-[0.75fr_1.25fr]">
          <Card className="border-[#e4e1d8] bg-white shadow-none" data-testid="admin-upload-card">
            <CardHeader className="p-6 pb-3"><CardTitle className="text-xl font-semibold">Add a trusted source</CardTitle></CardHeader>
            <CardContent className="p-6 pt-3">
              <form onSubmit={(event) => { event.preventDefault(); upload.mutate(); }} className="space-y-5" data-testid="admin-document-upload-form">
                <label className="block space-y-2"><span className="text-xs font-semibold text-[#5c5f66]">Document title</span><Input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="HDFC ERGO Optima Secure wording" data-testid="admin-document-title-input" /></label>
                <label className="block space-y-2"><span className="text-xs font-semibold text-[#5c5f66]">PDF, TXT or DOCX file</span><input type="file" accept=".pdf,.txt,.docx" onChange={(event) => setFile(event.target.files?.[0] ?? null)} className="block w-full rounded-lg border border-dashed border-[#c8c4b7] bg-[#f8f7f4] px-3 py-3 text-xs text-[#5c5f66]" data-testid="admin-document-file-input" /></label>
                <div className="flex items-center gap-3 text-[10px] font-bold uppercase tracking-widest text-[#8a8f99]"><span className="h-px flex-1 bg-[#f1efe9]" /> or web URL <span className="h-px flex-1 bg-[#f1efe9]" /></div>
                <label className="block space-y-2"><span className="text-xs font-semibold text-[#5c5f66]">Public document URL</span><Input type="url" value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://insurer.example/policy.pdf" data-testid="admin-document-url-input" /></label>
                <Button type="submit" disabled={upload.isPending || (!file && !url)} className="w-full bg-[#0d7a5f] text-white hover:bg-[#0a624c]" data-testid="admin-document-upload-button"><UploadCloud className="size-4" />{upload.isPending ? "Extracting and indexing…" : "Index insurance source"}</Button>
                <p className="text-[11px] leading-5 text-[#8a8f99]" data-testid="admin-document-upload-note">New sources start active. When AI is configured, a draft plan card is extracted for you to review before customers see it. Pause any source immediately if its policy version is outdated.</p>
              </form>
            </CardContent>
          </Card>

          <Card className="border-[#e4e1d8] bg-white shadow-none" data-testid="admin-document-list-card">
            <CardHeader className="flex-row items-center justify-between p-6 pb-3"><div><p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#8a8f99]">Knowledge sources</p><CardTitle className="mt-2 text-xl font-semibold">Indexed documents</CardTitle></div><Badge variant="secondary" data-testid="admin-document-count">{documents.data?.length ?? 0} sources</Badge></CardHeader>
            <CardContent className="p-6 pt-3">
              {documents.data?.length ? <div className="space-y-3">{documents.data.map((document) => <div key={document.id} className="flex items-center gap-3 rounded-xl border border-[#e4e1d8] p-4" data-testid={`admin-document-row-${document.id}`}><span className={`flex size-9 shrink-0 items-center justify-center rounded-lg ${document.enabled ? "bg-[#eaf6f1] text-[#0d7a5f]" : "bg-[#f1efe9] text-[#8a8f99]"}`}>{document.source_type === "web" ? <Globe2 className="size-4" /> : <FileText className="size-4" />}</span><div className="min-w-0 flex-1"><p className="truncate text-sm font-semibold text-[#17181c]">{document.title}</p><p className="mt-1 text-xs text-[#8a8f99]">{document.chunk_count} vector chunks · {document.source_type}</p></div>{document.source_url && <a href={document.source_url} target="_blank" rel="noreferrer" className="text-[#0d7a5f]" data-testid={`admin-document-source-link-${document.id}`}><ExternalLink className="size-4" /></a>}<Badge variant="outline" className={document.enabled ? "border-[#d7ebe4] bg-[#eaf6f1] text-[#0d7a5f]" : "border-[#e4e1d8] bg-[#f1efe9] text-[#8a8f99]"}>{document.enabled ? "active" : "paused"}</Badge><Badge variant="outline" className={PLAN_BADGE[document.plan_status]} data-testid={`admin-document-plan-status-${document.id}`}>{PLAN_LABEL[document.plan_status]}</Badge><button type="button" onClick={() => setReviewingId(document.id)} className="flex h-8 items-center gap-1.5 rounded-lg border border-[#d7ebe4] px-2.5 text-[11px] font-semibold text-[#0d7a5f] hover:bg-[#eaf6f1]" data-testid={`admin-document-review-plan-${document.id}`}><ClipboardCheck className="size-3.5" />Plan card</button><button type="button" onClick={() => toggle.mutate({ document, enabled: !document.enabled })} className="flex size-8 items-center justify-center rounded-lg border border-[#e4e1d8] text-[#5c5f66] hover:bg-[#f1efe9]" aria-label={document.enabled ? "Pause source" : "Activate source"} data-testid={`admin-document-toggle-${document.id}`}><Power className="size-3.5" /></button><button type="button" onClick={() => confirmDelete(document)} className="flex size-8 items-center justify-center rounded-lg border border-[#ead8d2] text-[#c2410c] hover:bg-[#fff4ef]" aria-label="Delete source" data-testid={`admin-document-delete-${document.id}`}><Trash2 className="size-3.5" /></button></div>)}</div> : <div className="rounded-xl border border-dashed border-[#c8c4b7] bg-[#f8f7f4] p-10 text-center" data-testid="admin-document-empty-state"><FileText className="mx-auto size-6 text-[#8a8f99]" /><p className="mt-3 text-sm font-semibold">No sources indexed yet</p><p className="mt-1 text-xs text-[#8a8f99]">Upload the first policy document to ground the chatbot.</p></div>}
            </CardContent>
          </Card>
        </div>

        <Card className="mt-6 border-[#e4e1d8] bg-white shadow-none" data-testid="admin-user-list-card">
          <CardHeader className="flex-row items-center justify-between p-6 pb-3"><div><p className="text-[10px] font-bold uppercase tracking-[0.16em] text-[#8a8f99]">Customer workspace readiness</p><CardTitle className="mt-2 text-xl font-semibold">User accounts</CardTitle></div><Badge variant="secondary" data-testid="admin-user-count">{users.data?.length ?? 0} users</Badge></CardHeader>
          <CardContent className="p-6 pt-3">{users.data?.length ? <div className="divide-y divide-[#f1efe9]">{users.data.map((account) => <div key={account.id} className="grid gap-2 py-4 sm:grid-cols-[1fr_1fr_auto] sm:items-center" data-testid={`admin-user-row-${account.id}`}><div><p className="text-sm font-semibold text-[#17181c]">{account.name}</p><p className="mt-1 text-xs text-[#8a8f99]">Joined {new Date(account.created_at).toLocaleDateString("en-IN")}</p></div><p className="truncate text-xs text-[#5c5f66]">{account.email}</p><Badge variant="outline" className={account.profile_complete ? "border-[#d7ebe4] bg-[#eaf6f1] text-[#0d7a5f]" : "border-[#eadcc8] bg-[#fff9ef] text-[#a16207]"}>{account.profile_complete ? "profile ready" : "profile pending"}</Badge></div>)}</div> : <p className="py-8 text-center text-sm text-[#8a8f99]" data-testid="admin-user-empty-state">No customer accounts yet.</p>}</CardContent>
        </Card>

        <PlanReviewDialog document={reviewing} onClose={() => setReviewingId(null)} onChanged={refreshAdmin} />

        <Dialog open={detail !== null} onOpenChange={(open) => { if (!open) setDetail(null); }}>
          <DialogContent className="max-h-[78vh] overflow-y-auto sm:max-w-3xl" data-testid="admin-metric-detail-dialog">
            <DialogHeader>
              <DialogTitle data-testid="admin-metric-detail-title">{detail ? detailTitles[detail] : "Admin details"}</DialogTitle>
              <DialogDescription data-testid="admin-metric-detail-description">Live operational details from the current SurakshaCFO workspace.</DialogDescription>
            </DialogHeader>
            {detail === "customers" && <AccountDetailList accounts={users.data ?? []} testId="admin-customer-detail-list" />}
            {detail === "completed" && <AccountDetailList accounts={completedUsers} testId="admin-completed-detail-list" />}
            {detail === "chunks" && <div className="space-y-2" data-testid="admin-chunk-detail-list">{documents.data?.map((document) => <div key={document.id} className="flex items-center justify-between gap-4 rounded-lg border border-[#e4e1d8] p-3"><div className="min-w-0"><p className="truncate text-sm font-semibold text-[#17181c]">{document.title}</p><p className="mt-1 text-xs text-[#8a8f99]">{document.source_type} · {document.enabled ? "active" : "paused"}</p></div><span className="font-mono text-sm font-bold text-[#0d7a5f]">{document.enabled ? document.chunk_count : 0} chunks</span></div>)}</div>}
            {detail === "questions" && <div className="space-y-2" data-testid="admin-question-detail-list">{questions.data?.length ? questions.data.map((question) => <div key={question.id} className="rounded-lg border border-[#e4e1d8] p-3"><div className="flex items-center justify-between gap-4"><p className="text-xs font-semibold text-[#17181c]">{question.user_name}</p><span className="text-[10px] text-[#8a8f99]">{new Date(question.created_at).toLocaleString("en-IN")}</span></div><p className="mt-2 text-sm leading-6 text-[#5c5f66]">{question.question}</p><p className="mt-1 text-[10px] text-[#8a8f99]">{question.user_email}</p></div>) : <p className="py-8 text-center text-sm text-[#8a8f99]">No customer questions yet.</p>}</div>}
          </DialogContent>
        </Dialog>
      </section>
    </AppShell>
  );
}

function AccountDetailList({ accounts, testId }: { accounts: AdminUserRecord[]; testId: string }) {
  return <div className="space-y-2" data-testid={testId}>{accounts.length ? accounts.map((account) => <div key={account.id} className="grid gap-2 rounded-lg border border-[#e4e1d8] p-3 sm:grid-cols-[1fr_1fr_auto] sm:items-center"><div><p className="text-sm font-semibold text-[#17181c]">{account.name}</p><p className="mt-1 text-[10px] text-[#8a8f99]">Joined {new Date(account.created_at).toLocaleDateString("en-IN")}</p></div><p className="truncate text-xs text-[#5c5f66]">{account.email}</p><Badge variant="outline" className={account.profile_complete ? "border-[#d7ebe4] bg-[#eaf6f1] text-[#0d7a5f]" : "border-[#eadcc8] bg-[#fff9ef] text-[#a16207]"}>{account.profile_complete ? "profile ready" : "profile pending"}</Badge></div>) : <p className="py-8 text-center text-sm text-[#8a8f99]">No matching accounts.</p>}</div>;
}