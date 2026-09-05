# AGENTS.md

## Before every plan or implementation
- Read ALL files in `docs/` (architecture.md, data-contract.md, roadmap.md) in full before planning or touching code.
- `docs/data-contract.md` is the source of truth for the Excel contract; `docs/roadmap.md` is the build order; `docs/architecture.md` is the "why" behind every decision.
- Verify against the project's current state (git status), not against stale memory.

## Communication
- LLM responses are always in English. Answer briefly. No preamble, no summaries of what is already known.
- Never commit unless explicitly asked.

## Exploration
- Use the graphify skill to explore the codebase and answer questions about project content. Prefer it over full-file reads to save tokens.
- If `graphify-out/` exists, treat any codebase/architecture question as a graphify query first.

## AWS CLI restrictions
- Only run read-only AWS commands without asking (`aws sts get-caller-identity`, `aws s3 ls`, `aws lambda list-functions`, `aws configure list`, budgets/`describe-*` commands).
- Never run any AWS command that creates, modifies, deletes, or deploys resources (create/put/delete/deploy/invalidate/update/`sam build`/`sam deploy`) without explicit user approval for that exact command.
- Never set up or modify billing/budgets config. Ask the user first.

## Editing rules
- Smallest working change (YAGNI). No unrequested abstractions, no new deps, no boilerplate.
- Reuse existing code over adding new code.
- Work in roadmap order (Fase 0 → Fase 6). Don't advance to the next fase without the current one testable.
- Tests: pytest. Run them after each change.

## Open decisions (do not re-litigate)
- DB dev: direct Supabase connection (pooled, port 6543).
- Stack fixed: pandas/openpyxl ETL, Flask+Mangum API, psycopg2 no ORM, vanilla JS + Chart.js + Leaflet frontend, SAM infra, GitHub Actions workflows.
- Migration order: per architecture.md §5 (dim_provincia first).
- The readme stays blank until a testable feature exists (Fase 1 hito).