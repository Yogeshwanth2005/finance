# Fin — SurakshaCFO Personal Finance Educational Demo

FastAPI + Motor/MongoDB backend and Vite/React frontend implementing
`docs/SURAKSHACFO_SPEC.md` — a family-finance gap-analysis, allocation and
insurance-document Q&A tool built as a personal/portfolio demo (not a live
financial or insurance service).

## How to Work Efficiently (low context — this is the DEFAULT, no need to be told)
- The brain is **queried, not loaded**. Never read whole files or the whole `.agents/` tree "to get context."
- Lookup order for ANY task: (1) `graphify query "<question>"` if `graphify-out/wiki/` exists → exact file:line, (2) the ONE relevant `.agents/` file the task scope points to below, (3) at most 2–3 targeted reads. Full-file reads are the last resort.
- Pull ONLY the `.agents/` file the task scope points to — never preload all of them.
- This runs automatically for every task; the user does NOT have to say "use the second brain."

## Agent Routing Instructions
To prevent context dilution, general invariants and rules are split into modular guides. **Always read these files first based on the scope of your task:**

1.  **Identity, Dev Persona & Code Style Rules**:
    *   Location: `.agents/context/identity.md`
    *   Read when: Starting a new session or reviewing coding style, formatting, and response conventions.
2.  **Invariants, Tech Stack & File Map**:
    *   Location: `.agents/context/stack-and-rules.md`
    *   Read when: Touching MongoDB calls, the Gemini/`lib/llm.py` seam, chat retrieval, auth, or routing.
3.  **Historical Decisions**:
    *   Location: `.agents/decisions/log.md`
    *   Read when: Seeking context on why a module was built/dropped or a stack was replaced. (Its migration index is history for the retired Prisma/Alembic stack; the app has no migrations.)
4.  **Active Roadmap & Technical Debt**:
    *   Location: `.agents/projects/active-backlog.md`
    *   Read when: Checking current backlog tasks or known tech debt.
5.  **Subsystem Notes & Load-Bearing Gotchas**:
    *   Location: `.agents/context/subsystem-notes.md`
    *   Read when: Editing a specific subsystem — holds the *why* and traps the code/wiki can't.

## After Any Change
The low-context lookup above only works if `.agents/` stays current. After
finishing a task, feature, or bugfix — before ending your turn — follow
`.claude/commands/second-brain-close.md` to sync `active-backlog.md` and
`decisions/log.md` with what changed. Do this automatically; don't wait
for the user to ask or to type `/second-brain-close`.
