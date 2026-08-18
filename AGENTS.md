# AGENTS.md

## Goal

Preserve the complete Generic Dataset Demo while replacing Google Drive with
SharePoint Online through Microsoft Graph and delivering the UI as a Power Apps
Code App.

## Architecture

```text
Power Apps → FastAPI → Airflow → SharePoint/Graph → SeaweedFS Bronze
           → profiling/rules/approvals → ClickHouse Silver/Gold
```

Raw CSV never passes through frontend code. Graph credentials are backend-only.
Keep controllers thin and dependency direction pointing from API/orchestration
to application ports to infrastructure adapters.

## Required parity

Keep ingestion status, multi-asset discovery, profiling, quality, violations,
masked evidence, rules, mapping approval, Bronze approval, Silver transform and
approval, Gold recipe/review/run/approval, lineage, audit, and repeatable runs.

## Power Apps

Use React and TypeScript with `@microsoft/power-apps`. Production access goes
through a Power Platform custom connector generated from FastAPI OpenAPI. Do
not commit tenant-specific `power.config.json`, connection IDs, tokens, or
secrets.

## Verification

Run Ruff, pytest, frontend typecheck/build, Docker Compose config validation,
and the deterministic local end-to-end workflow before claiming completion.

Canonical commands and expected results live in `docs/runbook.md`. A local
source run proves implementation integrity, but does not replace the required
tenant checkpoints: Graph with `Sites.Selected`, the custom connector as a
non-admin user, and a Code App solution push. Report those checkpoints as
pending until real environment evidence exists.

## Change scope

The entire repository is in scope. Refactor across API, domain, integration,
orchestration, infrastructure and UI boundaries when that improves parity or
maintainability. Preserve provider-neutral API contracts, immutable Bronze
history, approval gates and secrets hygiene. Do not reintroduce Google Drive or
route source files through frontend code.
