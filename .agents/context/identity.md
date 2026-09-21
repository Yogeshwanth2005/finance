# Identity, Dev Persona & Code Style

## Who is working on this
Solo dev (git user Yogeshwanth2005) building this as a personal/portfolio
demo project — explicitly **not** a live financial or insurance service.
Leans on the agent for full-stack implementation: the FastAPI/Motor backend,
the React/Tailwind UI, and the gap-analysis/allocation logic. Behaviour is
specified in `docs/SURAKSHACFO_SPEC.md`.

## Response Conventions
- Terse. No trailing "here's what I did" summaries — the diff/output speaks
  for itself.
- No comments explaining WHAT code does. A comment is only warranted for a
  non-obvious WHY (e.g. the title-gated retrieval rule, why `_public()` avoids
  an eager `dict.get` default).
- Don't invent fund/insurance reference data, NAVs, premiums or claim ratios.
  The plans in `routers/profile.py` `_plans()` are illustrative; new figures
  need a real, sourced origin.

## Code Style Rules
- TypeScript strict throughout the frontend; no `any` in new code.
- Python: type hints, a Pydantic model per request and response body, `async`
  handlers, `from lib.db import db` for Mongo.
- Gap analysis, allocation and KPI math stay in deterministic functions
  (`routers/profile.py` `_analysis`); the LLM only phrases answers and is never
  the source of a number.
- Behaviour changes get a failing test first (pytest against the live server).
- Educational framing everywhere: estimates only, not financial, tax, medical
  or insurance advice.
