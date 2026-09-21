# Active Roadmap & Technical Debt

## Replace Fin v2 with the `finance` app on MongoDB (IN PROGRESS — 2026-09-21)
Plan: `docs/superpowers/plans/2026-09-21-replace-project-with-finance-app.md`. Rollback point:
git tag `pre-finance-swap`.

| Task | Area | Status |
|---|---|---|
| 1 | Snapshot commit + tag `pre-finance-swap` | **Done** |
| 2 | Backend swapped to FastAPI/Motor; `lib/llm.py` Gemini adapter replaces the Emergent client | **Done** — adapter tests pass without network |
| 3 | Live-server suite green; `/auth/me` 500, default-password admin seed and dead index fixed | **Done** — 32 pytest tests passing, 0 server errors |
| 4 | Frontend swapped, `@emergentbase/*` plugins removed | **Done** — typecheck, lint (warnings only) and build exit 0; dev proxy verified |
| 5 | Root config, README, docs, second brain | **Done** |
| 6 | Browser pass through the core journey; delete `finance/`, `.next/`, root `node_modules/` | **Pending** — deletions need user confirmation |

---

## Proposed / Not Yet Scoped
- **SIP management (CAS import, view-only)** — idea only. See decisions/log.md's
  2026-09-17/18 entries for the narrowing history before resuming. No design, schema or code exists.

## Known Tech Debt
- **Rotate secrets**: `EMERGENT_LLM_KEY` sat in plaintext in the shared `finance/` folder; treat it
  as compromised. decisions/log.md (2026-09-16) records real Supabase credentials in the root
  `.env`; revoke them if that project is still live. (`JWT_SECRET` was already regenerated during
  the swap.)
- **RAG is not semantic**: `lib/rag.py` `retrieve` loads up to 5,000 chunks into Python and does
  cosine there, over 128-dim hashed bag-of-words vectors. Upgrade path: Atlas Vector Search plus a
  real embedding model.
- **`login_attempts` never expire** (no TTL index) and are keyed per IP+email.
- **`/auth/forgot-password`** returns `demo_token` in the response and reveals whether the account
  exists; demo-only until an email provider exists.
- **Google sign-in** is pending (no OAuth credentials).
- **`_plans()` in `routers/profile.py`** hard-codes named insurers and claim-settlement ratios.
  The old `DEMO_MODE` gate was not ported (see decisions/log.md, 2026-09-21).
- **Gemini streaming is unverified**: with no key only the deterministic fallback path runs. Set
  `GEMINI_API_KEY`, upload a small TXT and ask about it to check real SSE deltas.
- **Frontend install**: needs `npm install --legacy-peer-deps` (npm 10.9.8 arborist crash on
  vitest's optional peers). `npm audit` reports 4 vulnerabilities (2 moderate, 2 high), untriaged.
- **Test hygiene**: tests never clean up (`tscheck-*` docs and users accumulate), and the language
  tests share one retest user, so parallel modules can race on `preferred_language`.
- **Playwright workspace** (`tests/`) has no specs yet.
- **`implementationplanv2.md`** is stale product history; remove it or archive it.
