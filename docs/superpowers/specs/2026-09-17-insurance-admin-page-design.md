# Insurance Reference Admin Page — Design Spec

**Date:** 2026-09-17
**Status:** Approved, pending implementation plan
**Author:** Design session (Claude Code) with user

## 1. Context & Motivation

`implementationplanv2.md` §9.2 documents that `insurance_plan_reference` has
no automated public data source (unlike `fund_reference`, which AMFI/MFapi
can supply automatically) — it's meant to be curated by hand and refreshed
manually when it goes stale. Currently that means direct DB writes (e.g. via
`prisma studio` or editing a seed script); there is no in-app way to manage
this data.

This spec covers building a minimal, password-gated admin page so insurance
plan reference data can be added/edited/deleted through the app itself,
without requiring the office-Wi-Fi-sensitive DB tooling every time, and
without pulling forward the still-deferred real user-auth decision
(`src/lib/auth.ts`'s `authorize()` stub stays untouched).

## 2. Scope

**In scope:**
- A standalone, password-gated `/admin` area, independent of the app's
  regular (currently stubbed) NextAuth flow.
- CRUD UI for `insurance_plan_reference` only.
- A schema migration adding 3 columns needed by the admin form:
  `claimSettlementRatio`, `avgClaimSettlementDays`, `isGovernmentScheme`
  on `InsurancePlanReference`, plus `aumCr` on `FundReference` (needed by
  the separate fund-sync script, not by this admin page).
- Support for government insurance schemes (PMJJBY, PMSBY, PM-JAY, etc.)
  as rows in the same table, distinguished by `isGovernmentScheme`.

**Explicitly out of scope:**
- `fund_reference` gets **no** admin UI. It is fully handled by an
  automated AMFI/MFapi sync script (Task 7, tracked separately in
  `active-backlog.md`). No manual edit path is needed or provided for
  fund data — this was a deliberate decision after confirming AMFI/MFapi
  provide free, ToS-clean, automatable fund NAV/scheme data.
- No recurring/scheduled web scraper for insurance plan data. Rejected on
  three separate grounds (not just "needs review"):
  1. **Technical fragility** — insurer sites have no structured API and
     break scrapers silently on layout changes.
  2. **ToS violation** — most insurer sites prohibit automated/bot access
     regardless of whether a human reviews the scraped output afterward.
  3. **Regulatory posture** — this project's license to show named
     insurance products at all rests on being a personal, non-published
     demo curating a static dataset by hand (§0.2). A recurring automated
     pipeline that keeps a live insurance-product database current looks
     more like the IRDAI-regulated "web aggregator" activity the project
     is not licensed for. (Flagged as risk judgment, not a cited bright
     line — but reason enough to avoid it here.)
- No live, in-app LLM/AI call for generating plan descriptions. Using AI
  as a one-time, human-reviewed authoring aid when curating a new plan
  (fetch the insurer's or government portal's published page once, draft
  the text, human reviews before saving) is fine and matches the existing
  decision in `decisions/log.md`'s 2026-09-16 entry. That authoring aid is
  a workflow note for whoever curates data, not a feature to build/ship in
  the app.
- No changes to `src/lib/auth.ts` or the real user-auth stub — the admin
  gate is fully independent (see §4).

## 3. Data Model Changes

One new migration:

```prisma
model FundReference {
  // ...existing fields unchanged...
  aumCr Decimal @db.Decimal(12, 2) // AUM in INR crore; written only by the fund-sync script (Task 7), never by admin UI
}

model InsurancePlanReference {
  // ...existing fields unchanged...
  claimSettlementRatio   Decimal @db.Decimal(5, 2)  // percentage
  avgClaimSettlementDays Int                         // average days to settle
  isGovernmentScheme     Boolean @default(false)
}
```

Notes:
- No new column for scheme eligibility criteria (income cap, age band,
  etc.) — these go into the existing `keyFeatures` Json field as bullet
  entries, since `sumAssuredMin`/`Max` and `indicativePremiumNote` already
  accommodate fixed-amount government schemes (e.g. PMJJBY: min = max =
  ₹200000, premium note "₹436/year").
- `aumCr` is added here because it was already-known tech debt (flagged
  in `active-backlog.md`), and bundling it into one migration avoids a
  second office-Wi-Fi-blocked migration attempt later. It is not written
  or read by anything in this spec's admin UI.

## 4. Auth Gate

Fully standalone from the app's real (stubbed) auth:

- `middleware.ts` matches `/admin/**`. Requests without a valid signed
  session cookie redirect to `/admin/login`.
- `/admin/login`: a plain form. Its server action compares the submitted
  password against `process.env.ADMIN_PASSWORD` (single shared secret,
  no DB user record, no session provider).
- On success, sets an HttpOnly, Secure, `SameSite=Lax` cookie containing
  `{ issuedAt: <timestamp> }`, signed with HMAC-SHA256 using
  `process.env.ADMIN_SESSION_SECRET`, via Node's built-in `crypto` module
  — no new npm dependency. Cookie `maxAge` is 24h; middleware also
  re-validates the signed timestamp on every request so a copied/stale
  cookie can't be replayed past expiry even if the browser's own
  expiration is bypassed.
- A logout action (e.g. `/admin/logout`) clears the cookie.
- Server Actions invoked from pages under `/admin/**` are still POSTs to
  that same route path, so `middleware.ts`'s matcher covers them — no
  separate protection needed for mutations.

## 5. Admin UI

Single section: `/admin/insurance`.

- Server Component page: lists all `InsurancePlanReference` rows in a
  table (insurer, plan name, type, government/private, sum assured
  range, claim settlement ratio, last updated).
- "Add new" form and per-row Edit/Delete, all via Next.js Server Actions
  (no separate API routes).
- Form fields: `insurerName`, `planName`, `planType` (term/health),
  `sumAssuredMin`, `sumAssuredMax`, `indicativePremiumNote`,
  `keyFeatures` (simple textarea, one feature per line, stored as JSON
  array), `externalUrl`, `sourceNote`, `claimSettlementRatio`,
  `avgClaimSettlementDays`, `isGovernmentScheme` (checkbox).
- Minimal validation: required fields present, numeric fields in sane
  ranges (e.g. `sumAssuredMin <= sumAssuredMax`, ratio 0–100). No new
  form/validation library — row volume is small (curation of ~10–15
  rows total, not bulk data entry).

## 6. Testing

- Vitest unit tests for the HMAC sign/verify helper: valid cookie,
  tampered signature, expired timestamp.
- Vitest tests for server-action validation logic (missing required
  field, `sumAssuredMin > sumAssuredMax`, out-of-range ratio).
- Manual in-browser verification of the full CRUD flow (add, edit,
  delete a plan; confirm login gate blocks unauthenticated access;
  confirm logout works) per the project's convention of testing UI
  changes in a real browser before calling the work done.

## 7. Relationship to Other Backlog Items

- Task 6 (insurance reference matching logic) and Task 7 (seed reference
  data, including the AMFI/MFapi fund sync script) are separate,
  pre-existing backlog items and are unaffected by this spec except that
  Task 7's fund-sync script is the sole writer of the new `aumCr` column
  added here.
- This admin page is a new item, not previously in `implementationplanv2.md`'s
  build order — it should be added to `active-backlog.md` once
  implemented.
