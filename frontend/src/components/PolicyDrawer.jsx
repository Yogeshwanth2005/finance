import { useState } from "react";
import { apiClient } from "../api/client.js";

export function PolicyDrawer({ isOpen, onClose, defaultPlanId = null, defaultPlanName = "" }) {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  if (!isOpen) return null;

  async function handleSubmit(e) {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await apiClient.post("/api/insurance/rag/chat", {
        query: query.trim(),
        plan_id: defaultPlanId || undefined,
      });
      setResult(res);
    } catch (err) {
      setError(err.message || "Failed to query policy clauses");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/40 backdrop-blur-xs">
      <div className="flex h-full w-full max-w-lg flex-col bg-white p-6 shadow-2xl dark:bg-zinc-900 sm:rounded-l-2xl">
        <div className="flex items-center justify-between border-b border-zinc-200 pb-4 dark:border-zinc-800">
          <div>
            <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-50">
              Policy Intelligence (RAG Lookup)
            </h2>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              {defaultPlanName ? `Querying clauses for ${defaultPlanName}` : "Factual clause search across indexed policy wordings"}
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-md p-1.5 text-zinc-400 hover:bg-zinc-100 hover:text-zinc-600 dark:hover:bg-zinc-800 dark:hover:text-zinc-300"
          >
            ✕
          </button>
        </div>

        <div className="mt-4 flex-1 overflow-y-auto space-y-4 pr-1">
          <div className="rounded-md bg-amber-50 p-3 text-xs text-amber-800 dark:bg-amber-950/40 dark:text-amber-300 border border-amber-200 dark:border-amber-900">
            <strong>Factual lookup only:</strong> Fin extracts official clauses directly from policy wordings. Fin does not rank, score, or recommend insurance products.
          </div>

          <form onSubmit={handleSubmit} className="space-y-3">
            <div>
              <label htmlFor="rag-query" className="block text-xs font-medium text-zinc-700 dark:text-zinc-300">
                Ask a factual policy question
              </label>
              <textarea
                id="rag-query"
                rows={3}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="e.g. What is the waiting period for pre-existing diseases? Does it cover daycare procedures?"
                className="mt-1 w-full rounded-md border border-zinc-300 p-2 text-xs text-zinc-900 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-100"
              />
            </div>
            <div className="flex justify-end gap-2">
              <button
                type="submit"
                disabled={loading || !query.trim()}
                className="rounded-md bg-zinc-900 px-4 py-2 text-xs font-medium text-white hover:bg-zinc-800 disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-200"
              >
                {loading ? "Searching clauses..." : "Lookup Clauses"}
              </button>
            </div>
          </form>

          {error && (
            <div className="rounded-md bg-red-50 p-3 text-xs text-red-700 dark:bg-red-950/40 dark:text-red-300">
              {error}
            </div>
          )}

          {result && (
            <div className="mt-4 space-y-3 border-t border-zinc-200 pt-4 dark:border-zinc-800">
              {result.is_refusal ? (
                <div className="rounded-md border border-amber-300 bg-amber-50 p-4 text-xs text-amber-900 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200">
                  <div className="flex items-center gap-1.5 font-semibold text-amber-900 dark:text-amber-200 mb-1">
                    <span>⚠️ Regulatory Notice</span>
                  </div>
                  <p>{result.answer}</p>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="rounded-md border border-zinc-200 bg-zinc-50 p-4 text-xs text-zinc-800 dark:border-zinc-800 dark:bg-zinc-800/60 dark:text-zinc-200 whitespace-pre-wrap">
                    {result.answer}
                  </div>

                  {result.sources && result.sources.length > 0 && (
                    <div>
                      <h4 className="text-xs font-semibold text-zinc-700 dark:text-zinc-300 mb-2">
                        Cited Policy Documents & Clauses:
                      </h4>
                      <div className="space-y-2">
                        {result.sources.map((src, idx) => (
                          <div
                            key={idx}
                            className="rounded-md border border-zinc-200 p-2.5 text-xs dark:border-zinc-800 bg-white dark:bg-zinc-900"
                          >
                            <div className="flex justify-between items-center text-zinc-900 dark:text-zinc-100 font-medium">
                              <span>📄 {src.title}</span>
                              <span className="text-[10px] text-zinc-400">Match: {(src.similarity * 100).toFixed(1)}%</span>
                            </div>
                            <p className="mt-1 text-[11px] text-zinc-500 dark:text-zinc-400 italic">
                              "{src.excerpt}"
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
