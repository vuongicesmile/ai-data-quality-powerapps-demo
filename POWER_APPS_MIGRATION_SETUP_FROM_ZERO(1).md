# Power Apps Migration — Full Data Platform Setup From Zero

This file is the executable migration checklist for this repository. It
preserves the full Generic Dataset Demo, replaces Google Drive with SharePoint
Online through Microsoft Graph, and delivers the operator UI as a Power Apps
Code App.

## Target architecture

```text
SharePoint Online -> Microsoft Graph app-only -> Airflow
  -> SeaweedFS Bronze -> profiling/rules/evidence/approvals
  -> ClickHouse Silver/Gold -> FastAPI custom connector -> Power Apps Code App
```

Raw CSV must never pass through Power Apps. Graph authentication, pagination,
download and retry logic stay behind `DatasetSource`. Keep SeaweedFS and
ClickHouse until behavioral parity is proven.

## Phase 0 — Repository [complete]

- Repository: `vuongicesmile/ai-data-quality-powerapps-demo`.
- Branch: `feat/sharepoint-powerapps-platform`.
- Monorepo boundaries are documented in `docs/architecture.md`.
- Secrets, generated Power Apps IDs and build output are ignored.

## Phase 1 — Canonical parity fixture [complete]

The deterministic dataset is under `sample-data/ecommerce-v1` and contains
`customers.csv`, `orders.csv`, `order_items.csv`, and `products.csv`.
`scripts/smoke_test.py` proves the complete 13-action lifecycle and requires
100% lifecycle progress.

When the legacy Google Drive environment is available, export its non-secret
row counts, hashes, profiles, violations, Silver/Gold reconciliation and
lineage under `docs/migration-baseline/`. Tenant access is not required to run
the new deterministic parity fixture.

## Phase 2 — SharePoint source [tenant action]

Create `/sites/AIDataQualityDev`, library `DataQualityDatasets`, folder
`GenericDatasets/ecommerce-v1`, and upload the four canonical files. Complete
the browser checkpoint and record only non-secret host/path values. Follow
`docs/sharepoint-setup.md`.

## Phase 3 — Entra least privilege [tenant action]

Register a single-tenant backend app, grant Microsoft Graph application
permission `Sites.Selected`, give that app `read` on only the development site,
and supply credentials through runtime secrets. Never commit a client secret.

## Phase 4 — Graph proof [implemented; tenant verification pending]

The adapter implements token caching, site resolution, drive discovery by
name, bounded paginated folder listing, bounded streaming downloads, eTag
capture, and typed handling for 401/403/404/429/5xx. Verify it against the
tenant in the order documented in `docs/sharepoint-setup.md`.

## Phase 5 — Bronze ingestion [complete]

The Airflow DAG `sharepoint_generic_dataset_bronze_ingestion` and local mode
both use the same `IngestionService`. SeaweedFS stores immutable CSV objects
and versioned manifests with source IDs/versions, SHA-256, size, row count and
columns. Re-runs are deterministic and detect unchanged input.

## Phase 6 — Governed backend [complete]

FastAPI exposes provider-neutral endpoints for ingestion, asset selection,
discovery, profiling, rules, masked evidence, mappings, Bronze approval,
Silver publication/approval, Gold recipe version/review/run/approval and
lineage. ClickHouse persists state revisions and publishes Silver/Gold through
staging tables.

## Phase 7 — Power Apps Code App [code complete; environment push pending]

The React/TypeScript app supports Workspace, Profiles, Rules, Mapping, Silver,
Gold and Lineage views. Local HTTP and generated Power Platform connectors are
behind one `PlatformGateway`. Follow `docs/power-apps-deployment.md` to create
tenant-specific configuration and push into a solution using the current npm
`power-apps` CLI.

## Phase 8 — Verification and cutover

Required before a production claim:

```text
ruff check passes
pytest passes
frontend build passes
docker compose config passes
local smoke lifecycle reaches 100%
SharePoint Graph run has all four source assets
Power Apps connector works as a non-admin user
Silver/Gold counts and hashes match the approved migration baseline
```

The first five checks are repository gates. The last three require the target
Microsoft tenant and its administrator-approved environment configuration.

## Rollback

Disable the SharePoint DAG and API ingestion action, preserve immutable Bronze
objects and ClickHouse revisions, restore the previous deployed solution/API
version, then investigate from manifest batch ID and lineage events. Do not
delete source files or historical manifests during rollback.
