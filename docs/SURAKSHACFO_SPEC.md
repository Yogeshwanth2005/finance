# SurakshaCFO MVP Spec

## What it does
SurakshaCFO is an India/INR family financial protection planner. A household enters a basic family profile, income, liabilities, existing protection, liquid savings and investments. The app returns a dashboard with rule-based term-insurance, health-cover, emergency-fund and investable-surplus analysis, then offers illustrative plan comparisons and a profile-aware insurance chat surface.

## Data model
- `ProfileInput` / `FamilyProfile`: family demographics, employment and household income, expenses, loans, existing cover, emergency savings and investments.
- `FinancialAnalysis`: annual cashflow, liabilities, protection score, term and health gaps, six-month emergency-fund goal, insurance budget and investable surplus.
- `ProfileKpis`: eight neutral profile metrics—emergency coverage %, runway months, term adequacy %, health adequacy %, savings rate %, debt-to-income %, cover-to-liabilities ratio and liabilities-to-income multiple.
- `Plan`: illustrative term/health plan comparison data.
- `DocumentRecord` and vector chunks: admin-controlled insurance knowledge sources with active/paused status.
- `ChatMessageRecord`: per-account questions, streamed grounded answers and cited source titles.

## Key flows
1. `/` creates or edits the signed-in user's profile in four steps and saves it through `POST /api/profile`; profile values are loaded from the account, never another browser user's draft.
2. `/dashboard` loads `GET /api/profile` and shows the protection score, cashflow, gaps, emergency fund and mutual-fund allocation direction.
3. `/insurance` shows plan filters, comparison guidance and streams contextual answers through `POST /api/chat/stream`.
4. `/admin/documents` is the admin operations workspace: each metric opens its live detail view (customers, completed profiles, per-source chunks, recent questions), alongside document ingestion, source pause/reactivate controls and safe source deletion.
5. `/account` is the user profile and settings workspace. The profile icon sits beside language/logout and lets users update display name, preferred language, reminder/privacy preferences, password, and reopen their saved family/financial details for editing.

## Recommendation rules
- Term need = 15× combined earned income + total liabilities − existing term cover.
- Health baseline = 10L plus household/city adjustment, capped at 25L.
- Emergency fund = 6× monthly household expenses.
- Investable surplus = annual income − expenses − EMIs − illustrative insurance budget, floored at zero.

## Profile KPI rules
- Emergency coverage % = emergency savings ÷ (6 × monthly expenses) × 100; runway = emergency savings ÷ monthly expenses.
- Term adequacy % = existing term cover ÷ recommended term cover × 100; health adequacy % = current health cover ÷ recommended health cover × 100.
- Savings rate % = (household income − annual expenses − annual EMI) ÷ household income × 100.
- Debt-to-income % = monthly EMI ÷ monthly household income × 100. The displayed 40–50% line is explicitly illustrative, not advice.
- Cover-to-liabilities = existing term cover ÷ total liabilities; liabilities-to-income = total liabilities ÷ annual household income.
- Zero denominators return 0. KPIs show plain numbers and rupee context only—no ranking or good/bad verdict.

## Auth and roles
- Email/password accounts use secure httpOnly access and refresh cookies. Signup leads to the family profile; completed users land on their dashboard. Password reset is available as a demo-token flow until an email provider is connected.
- Each user owns one private profile, including separate spouse identity, employment and income details when both partners work.
- New users see only Profile navigation until submission; Dashboard and Insurance navigation appear after completion. Direct access remains guarded.
- Selecting Single hides and clears every spouse field while keeping the children/parents dependents question visible.
- User preferences persist per account: display name, English/Hindi/Telugu/Tamil, reminder preference and enhanced-privacy preference. Password changes require the current password.
- Admin role lands directly on `/admin/documents`; user navigation is hidden there. Admins can index PDF, TXT, DOCX and public web sources, monitor users, pause outdated sources and delete a source with all of its chunks. Demo admin credentials are in `memory/test_credentials.md`.
- Google sign-in is intentionally pending because OAuth credentials were not supplied.

## RAG chatbot
- Admin documents are extracted, chunked and stored in MongoDB with deterministic local vectors. Paused sources are excluded from retrieval immediately.
- User questions retrieve the most relevant indexed chunks, add the user's financial analysis context, and stream a Gemini answer grounded only in those sources.
- General education questions (for example, why term insurance matters) use only the signed-in family's profile and never name a policy. Document retrieval is activated only when the user names a plan/provider or explicitly asks for a comparison.
- Comparison requests are rendered as real tables. Missing policy facts are labelled as not stated rather than inferred.
- RAG retrieval continues over English source documents, but Gemini answers in the account's saved language. Plan/provider names, source titles, monetary values and legal identifiers remain unchanged; general profile-based answers are also localized.
- If no relevant source exists or Gemini is unavailable, the chatbot explicitly falls back without inventing policy details.
- Chat history lasts only for the current session: it is deleted on logout, and every login starts with an empty conversation. Admin "Questions asked" figures therefore reflect only users who are currently signed in.