# CLAUDE.md

## Project Overview

`contentflow_lab` is the production-oriented backend platform for the ContentFlow ecosystem.

It hosts:

- a FastAPI runtime used by `contentflow_app`,
- AI automation and research components,
- scheduling, status, and publish-support services used by downstream clients.

## Architecture

- `api/` — FastAPI app and routers:
  - startup/shutdown lifecycle (`api.main`),
  - health + service endpoints,
  - projects/settings/creator/profile/content/drip/jobs/status and analytics APIs.
- `agents/` — CrewAI/PydanticAI pipelines.
- `scheduler/` — periodic orchestration.
- `status/`, `data/`, `utils/` — service and persistence helpers.
- `api/services/` — integrations (analytics, job store, feedback, feedback, drip services, auth/webhand-off helpers).

## Common Commands

```bash
# one-time setup
pip install -r requirements.txt
flox activate  # if using flox

# run API with secrets
doppler run -- uvicorn api.main:app --reload --port 8000
```

```bash
# health + docs
curl http://localhost:8000/health
open http://localhost:8000/docs
open http://localhost:8000/redoc
```

## Backend Focus

- Backend reliability changes must preserve compatibility for authenticated flows consumed by `contentflow_app`.
- Changes to `api/` routers should keep request/response contracts stable and update docs/changelog when impacted.
- New routers should be added with auth, validation, and status/error handling consistent with existing FastAPI patterns.
- Keep startup schema/migration logic defensive (`idempotent`, non-blocking where possible).

## Turso / libSQL Schema Changes (Do Not Skip)

- Production DB is **Turso (SQLite/libSQL)**.
- If you introduce a new table/column/index that the API code relies on, ship the corresponding migration/ensure step in the same change.
- Failure mode is misleading: a missing table (e.g. `UserSettings`) can make onboarding/project selection appear broken and can even trigger upstream 502s.
- **Mandatory before every commit/push**: explicitly decide and state whether a Turso migration is required (`yes/no`), with a short reason.
- If the answer is `yes`, include the migration/ensure changes in the same commit/push. If `no`, record why no migration is needed.

## Related Projects

- `contentflow_app` — Flutter application and web shell.
- `contentflow_site` — marketing/auth entrypoint.

## Forbidden Paths

- `/home/claude/contentflow/contentflow_lab_deploy` is an operator-controlled deployment copy of `contentflow_lab`.
- Agents must treat that directory as out of scope: do not read it, modify it, run tests from it, diff against it, restart services from it, or use it as context unless the user explicitly asks for that exact path.
- Work in `contentflow_lab` only; the user decides when and how deployment copies are updated.

## References

- `AGENTS.md` for conventions and operational notes.
- `CHANGELOG.md` for endpoint/domain-level changes.
- `ENVIRONMENT_SETUP.md` for secrets and runtime configuration.
