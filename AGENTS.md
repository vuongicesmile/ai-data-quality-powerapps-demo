# AGENTS.md

## Goal

Migrate the Generic Dataset Demo to a Power Platform-native architecture. The
target must preserve the complete governed data-quality lifecycle while
removing the self-hosted data platform dependencies from the runtime.

Target architecture:

```text
Power Apps Code App
  ├── generated Dataverse services
  └── solution-aware Power Automate flows
             |
             v
FastAPI profiling/transformation worker
             |
             ├── existing SharePoint `TimerApp` lists
             └── Microsoft Dataverse
                   ├── workflow and audit
                   ├── immutable Bronze snapshots and rows
                   ├── profiles, rules, evidence, mappings and approvals
                   ├── generic Silver rows
                   └── versioned Gold recipes and results
```

## Planning Gate

The Power Platform-native migration is approved as the target architecture,
but code refactoring must not start merely because this plan exists. When the
user asks to update the plan or documentation only, modify documentation only.
Start implementation only after an explicit implementation instruction.

For the current migration, do not create or run unit-test files unless the user
explicitly asks for tests. Validation should focus on configuration review,
buildability, and tenant checkpoints requested by the user.

## Required Runtime Replacements

The final runtime must not depend on:

- ClickHouse;
- SeaweedFS or another S3-compatible Bronze store;
- Airflow;
- Airflow PostgreSQL;
- a frontend-only HTTP gateway for Dataverse CRUD.

Replace them as follows:

| Previous component | Power Platform-native replacement |
|---|---|
| Airflow | Solution-aware Power Automate cloud flows |
| SeaweedFS Bronze | Immutable Dataverse Bronze snapshot/row tables |
| ClickHouse workflow state | Normalized Dataverse tables |
| ClickHouse Silver | Dataverse generic Silver-row table |
| ClickHouse Gold | Dataverse Gold recipe/result tables |
| API-only UI access | Generated Dataverse and Flow TypeScript services |

FastAPI remains only for bounded operations that are unsuitable for Power Fx
or Power Automate, such as list-row normalization, profiling, rule execution, mapping
conversion, reconciliation, and masked evidence generation. It must remain
stateless; Dataverse and SharePoint are the systems of record.

## Required Functional Parity

Keep all existing Generic Dataset capabilities:

- Power Apps-triggered ingestion and observable run status;
- multi-asset batches sourced from the four approved `TimerApp` lists;
- immutable Bronze snapshots and manifests;
- schema discovery and deterministic profiling;
- quality scores, violations, and masked evidence;
- rule generation, review, and execution;
- mapping review, versioning, and approval;
- Bronze approval;
- Silver transform, rejection evidence, publication, and approval;
- Gold recipe authoring, versioning, review, execution, reconciliation, and
  approval;
- lineage, business activity, Dataverse auditing, and repeatable/idempotent
  runs.

## Dataverse Model

Use solution-owned custom tables with the `dq_` publisher prefix:

```text
dq_dataset
dq_ingestionrun
dq_batch
dq_asset
dq_bronzesnapshot
dq_bronzerow
dq_columnprofile
dq_rule
dq_ruleresult
dq_evidence
dq_mapping
dq_approval
dq_silverrow
dq_goldrecipe
dq_goldresult
dq_activity
```

Use lookups for ownership and lifecycle relationships, Choice columns for
statuses, alternate keys for idempotent integration, and Dataverse auditing on
governed records. Store only bounded row/profile JSON where a truly generic
schema is necessary. Do not dynamically create Dataverse tables per source
list.

Dataverse is the demo serving and governance platform, not an unlimited
analytical warehouse. Default demo limit: 5,000 rows per source list per run.
A future high-volume variant may move Bronze/Silver/Gold to Microsoft
Fabric, but Fabric is not part of the current implementation scope.

## SharePoint and Graph

Raw SharePoint list items never pass through Power Apps browser code.

Required flow:

```text
TimerApp lists -> backend/flow -> immutable Dataverse Bronze rows -> governed lifecycle
```

Reuse the existing site and source lists; do not provision a new SharePoint
site, document library, folder tree, or CSV upload for this demo:

```text
https://titancorpvncom.sharepoint.com/sites/TimerApp
TimerList_AllProject01
TimerList_AllProject02
TimerList_AllProject03
TimerList_AllProject04
```

Treat each approved list as one logical asset. Capture bounded list-item JSON,
source item ID, eTag, row hash, batch ID, and capture time in immutable
Dataverse `dq_bronzerow` records, with batch inventory in
`dq_bronzesnapshot`. Keep Microsoft Graph behind a read-only infrastructure
adapter. Use app-only `Sites.Selected` with access only to `TimerApp`. Never
expose Graph tokens or credentials to Power Apps.

## Power Apps and Power Automate

Use React/TypeScript and the current npm `@microsoft/power-apps` CLI.

- Bind Code Apps to Dataverse tables using generated typed services.
- Bind ingestion to a solution-aware Power Automate flow using generated Flow
  services.
- Use solution connection references rather than user-specific connection IDs.
- Keep generated tenant-specific configuration and `power.config.json` out of
  source control.
- Use Power Platform environment variables for the TimerApp site/list allowlist, worker URL,
  limits, and environment-specific settings.
- Package Dataverse tables, flows, custom connector, environment variables,
  connection references, security roles, and Code App in one solution.

## Security and Governance

- Use Dataverse security roles for Operator, Reviewer, Approver, and Admin.
- Use an application user or managed identity for backend Dataverse access.
- Prefer certificates, workload identity, managed identity, or Key Vault over
  client secrets outside local development.
- Enable audit on datasets, mappings, rules, recipes, approvals, and lifecycle
  status columns.
- Mask sensitive evidence before persistence.
- Enforce optimistic concurrency through Dataverse ETags on review and
  approval mutations.
- Do not commit environment URLs, application IDs tied to a tenant, connection
  IDs, secrets, tokens, exported data, or generated state.

## Implementation Order

When implementation is explicitly approved, proceed in this order:

1. Dataverse logical schema, relationships, choices, keys, and security roles.
2. Domain contracts and Dataverse/SharePoint adapter interfaces.
3. Dataverse Web API client and normalized repositories.
4. TimerApp list ingestion and Dataverse Bronze snapshot inventory.
5. Power Automate ingestion orchestration.
6. FastAPI composition and provider-neutral worker endpoints.
7. Code App generated Dataverse/Flow services.
8. Remove ClickHouse, SeaweedFS, Airflow, PostgreSQL, and obsolete docs.
9. Tenant validation and solution export.

Do not delete the old adapters until the new tenant flow proves complete
Bronze-to-Gold parity. Keep each removal recoverable in Git history.

## Source of Truth

`POWER_APPS_MIGRATION_SETUP_FROM_ZERO(1).md` is the detailed execution plan.
If it conflicts with older architecture documents, this file and the migration
plan take precedence.
