# Implementation Plan — v2 (Educational Demo Project)

**Purpose:** Hand this directly to a coding agent (e.g. Claude Code) to build. This extends the v1 plan with a KPI/ratio layer and real fund/insurance reference data. These additions are only appropriate because this remains a personal/portfolio demo project — not a published, live financial or insurance service. Read Section 0 before touching Sections 5.2 or 6.3.

## 0. Project Context (read first)

### 0.1 What's new in v2
- A deterministic KPI/ratio layer on top of the existing gap-analysis output (Section 4.5)
- Real mutual fund reference examples mapped to the allocation output (Section 5.2)
- Real insurance plan reference examples mapped to the coverage gaps, with a "view full details" redirect to the insurer's own site (Section 6.3)
- An updated onboarding disclaimer naming this as a demo/portfolio project, not a live service (Section 3)
- A `DEMO_MODE` flag gating all of the above

### 0.2 Why this is allowed now — and when it stops being allowed
v1 deliberately avoided naming specific funds or insurance products because doing so, for a real published service, runs into SEBI's Investment Advisers Regulations (personalized fund recommendations require RIA registration) and IRDAI's Insurance Web Aggregator Regulations (displaying/comparing named insurance products and passing leads to insurers requires a web aggregator license). Those regulations govern real businesses offering services to real clients.

This build is a personal/portfolio project — not published, not offered as a service to the public. That is why v2 can safely show real fund and insurance names where v1 could not.

**This reasoning breaks if the project's status changes.** If this is ever deployed for real users making real financial or insurance decisions beyond demo/portfolio purposes — the "closed beta with friends/family" milestone in Section 7 is the likely trigger point — revert Sections 5.2 and 6.3 to v1's category-only behavior and reassess licensing before going further. This document is not a permanent clearance for a real deployment.

## 1. Tech Stack
*(unchanged from v1)*
- Frontend: Next.js (React) + Tailwind CSS, single web app, mobile-responsive
- Backend: Next.js API routes
- Database: PostgreSQL via Supabase
- Auth: Managed provider (Supabase Auth or Clerk)
- Hosting: Vercel
- No ML libraries, no LLM API calls — every calculation is deterministic. The two new lookups in v2 (fund/insurance reference matching) are plain table queries against curated data, not model-driven recommendations — the "no ML" principle from v1 still holds.

## 2. Data Model (Postgres schema, conceptual)

`users`, `financial_profile`, `insurance_profile`, and `allocation_results` carry over unchanged from v1. Changes below.

**gap_analysis_results** — add columns (alongside the existing emergency_fund_target/current/status, debt_priority_order, term_cover_gap, health_cover_gap, computed_at):
```
emergency_fund_coverage_pct
term_cover_adequacy_pct
health_cover_adequacy_pct
savings_rate_pct
debt_to_income_pct
```

**fund_reference** (NEW)
```
id, scheme_code, scheme_name, amc_name,
category (enum: equity_large_cap, equity_diversified,
          debt_short_duration, fixed_deposit,
          gold_etf, sovereign_gold_bond),
expense_ratio, latest_nav, nav_date,
external_url, last_synced_at
```

**insurance_plan_reference** (NEW)
```
id, insurer_name, plan_name, plan_type (enum: term, health),
sum_assured_min, sum_assured_max,
indicative_premium_note (text — e.g. "starts around ₹X/month
  for a 30-year-old non-smoker, per insurer's published rate card";
  not a live quote),
key_features (jsonb: array of short strings),
external_url, last_updated_at, source_note
```

Note: this reference data is general product information, not tied to any individual user, so it carries no DPDP consent requirement of its own — the v1 consent rules for `financial_profile` and `insurance_profile` are unaffected.

## 3. Onboarding Flow — updated Screen 1
Replace the v1 Screen 1 disclaimer with a two-part acknowledgment, both required before data entry:

> **Part A (unchanged, educational scope):** "This tool provides educational guidance based on information you provide. It is not personalized financial or insurance advice."
>
> **Part B (new, project status):** "This is a personal/portfolio demo project, not a live financial or insurance service. Any fund or insurance plan examples shown are for illustration and are not offers, recommendations, or solicitations to buy."

Screens 2–6 are otherwise unchanged from v1.

## 4. Gap Analysis Logic
Sections 4.1–4.4 (emergency fund, debt prioritization, term cover gap, health cover gap) are unchanged from v1 — implement exactly as specified there.

### 4.5 KPI / Ratio Layer (NEW)
Pure functions computed alongside 4.1–4.4, written to the new `gap_analysis_results` columns:
```
emergency_fund_coverage_pct = emergency_fund_current / emergency_fund_target * 100
term_cover_adequacy_pct     = existing_term_cover_amount / recommended_term_cover * 100
health_cover_adequacy_pct   = effective_existing_cover / recommended_health_cover * 100
savings_rate_pct            = (monthly_income - monthly_expenses) / monthly_income * 100
```

Debt-to-income needs one new piece of logic — v1 only sorted debts by interest rate and never computed a payment amount, so derive an EMI per debt first:
```
monthly_rate = interest_rate / 12 / 100
emi = outstanding_amount * monthly_rate * (1 + monthly_rate)^tenure_months
      / ((1 + monthly_rate)^tenure_months - 1)

debt_to_income_pct = sum(emi across all existing_debts) / monthly_income * 100
```

## 5. Allocation Logic
Section 5.1 (base_equity_pct, risk-tolerance adjustment, short-horizon shift, category-level output) is unchanged from v1.

### 5.2 Reference fund examples per category (NEW, project-only)
For each output bucket (equity/debt/gold), select `config.fund_examples_per_category` (default 3) rows from `fund_reference` where `category` matches that bucket's mapped category, sorted deterministically by AUM/fund size descending — not by past performance. Keep the selection rule-based and free of any "best fund" judgment call, consistent with the app's no-ML principle.

Display alongside the existing category description, e.g.:
```
equity_pct -> "large-cap index fund or diversified equity mutual
  fund category" + [3 example schemes pulled from fund_reference]
```

Each example links out via its `external_url` with a neutral label such as "View scheme details" — never "Invest now" or "Buy." The v1 rule against transactional language and buttons is unchanged.

## 6. Dashboard Output
The v1 sections (protection status, allocation snapshot, persistent disclaimer banner, no buy/invest flows) carry over unchanged. Add:

### 6.1 KPI display (NEW)
Show the five percentages from Section 4.5 as headline ring/gauge-style numbers, with the existing ₹-amount gaps as supporting detail underneath each one — the percentage summarizes, it doesn't replace the rupee figure.

### 6.2 Fund reference cards (NEW)
Under the allocation snapshot, show the Section 5.2 example schemes as small cards: scheme name, AMC, category, expense ratio, latest NAV, "View scheme details" link.

### 6.3 Insurance plan reference cards (NEW)
Under the protection status section:
- If `term_cover_gap > 0`: show up to `config.insurance_examples_per_gap_type` (default 2) rows from `insurance_plan_reference` where `plan_type = 'term'`, sorted by how closely `sum_assured_max` approximates the gap.
- If `health_cover_gap > 0`: same query, filtered to `plan_type = 'health'`.
- Each card: insurer name, plan name, sum assured range, 2–3 key features, indicative premium note, and a **"Show more details"** button that opens `external_url` (the insurer's own page) in a new tab.
- Show cards individually, not as a ranked side-by-side comparison table — keeps the UX as "here are examples," not "here's our pick between insurers."

### 6.4 Updated persistent banner text
Append to the existing v1 banner: *"Fund and insurance plan examples shown are illustrative only — this is a demo project, not a live service."*

## 7. Build Order (Milestones)
1. Project scaffold (unchanged from v1)
2. DB schema + migrations — including `fund_reference`, `insurance_plan_reference`, and the five new `gap_analysis_results` columns
3. Onboarding flow UI — updated two-part disclaimer copy; consent tracking unchanged
4. Gap analysis engine — 4.1–4.4 as in v1, plus 4.5 KPI functions, unit-testable independent of UI
5. Allocation engine — 5.1 as in v1, plus 5.2 fund-example selection logic
6. Insurance reference matching logic — pure function mapping gap output to `insurance_plan_reference` rows
7. Seed reference data — one-time AMFI sync script populating a curated shortlist in `fund_reference` (Section 9.1); one-time hand-written seed for `insurance_plan_reference` (Section 9.2)
8. Dashboard UI — wired to KPI outputs and fund/insurance reference cards, all gated behind `DEMO_MODE`
9. End-to-end test — fill form → correct gap/allocation/KPI numbers → reference cards render → both disclaimer parts always visible → redirect links open the correct external URL
10. Deploy to Vercel — `DEMO_MODE=true` by default; share via direct link only (portfolio, recruiters, interviews); don't submit to app directories or otherwise make it publicly discoverable in this state

## 8. Config Values to Keep Editable
All v1 values (emergency fund multiplier, income replacement multiplier, health cover baseline, high-interest debt threshold, risk tolerance multipliers, short-horizon threshold/shift) carry over unchanged. Add:
- `fund_examples_per_category` (default 3)
- `insurance_examples_per_gap_type` (default 2)
- `DEMO_MODE` (default `true`) — when `false`, disables Sections 5.2, 6.2, and 6.3 entirely, falling back to v1's category-only behavior

## 9. Data Sourcing Notes (NEW)

### 9.1 Mutual fund / SIP reference data
AMFI publishes free, public scheme and NAV data (`amfiindia.com/spages/NAVAll.txt`); several free wrapper APIs mirror it in cleaner JSON if parsing AMFI's raw text feed directly isn't wanted. Don't ingest the full ~16,000+ scheme universe for this project — write a one-time (or occasionally re-run, e.g. monthly) seed script that pulls a curated shortlist of 5–10 well-known schemes per category into `fund_reference`. A live sync job is unnecessary for a demo project.

### 9.2 Insurance plan reference data
No AMFI-equivalent public feed exists for insurance. Populate `insurance_plan_reference` by hand: pick a handful (5–10) of real, publicly documented plans across two or three insurers, sourced from each insurer's own published brochure/site, with `external_url` pointing to that same official page. This is a one-time manual curation task, not an integration — refresh by hand if it goes stale; that's an accepted trade-off for a demo project, not a production concern.

---

Sections 1–4.4, 5.1, and the core of Section 6 are unchanged in spirit from v1. Everything marked (NEW) above is additive and gated behind `DEMO_MODE`. Build in the order given in Section 7.
