# Power Apps Migration — Dataverse-Native Setup From Zero

## 0. Status and Objective

This document replaces the earlier transitional architecture that retained
Airflow, SeaweedFS, and ClickHouse.

Repository composition now uses Dataverse, SharePoint Bronze, Power Automate
contracts, and generated-service bindings. Tenant-owned solution components
still require creation/binding in the selected Power Platform environment.
Legacy adapters are disconnected and retained only until tenant parity passes.

Target repository:

```text
https://github.com/vuongicesmile/ai-data-quality-powerapps-demo
```

Objective:

```text
Preserve the complete Generic Dataset Demo
Replace Google Drive with SharePoint Online
Replace Airflow with Power Automate
Replace SeaweedFS with a SharePoint Bronze library
Replace ClickHouse workflow/Silver/Gold with Microsoft Dataverse
Use direct Dataverse and Flow services in the Power Apps Code App
```

This remains a full governed data-quality workflow, not a frontend-only demo.

---

# 1. Target Architecture

```text
Power Apps Code App
  ├── generated Dataverse table services
  └── generated Power Automate Flow service
             |
             v
Power Automate: DQ_StartIngestion
             |
             v
FastAPI profiling/transformation worker
             |
             ├── Microsoft Graph / SharePoint source
             ├── SharePoint DataQualityBronze library
             └── Microsoft Dataverse
                   ├── datasets, batches, assets, run status
                   ├── profiles, rules, results, evidence
                   ├── mappings, approvals, audit activity
                   ├── generic Silver rows and rejections
                   └── Gold recipes, results and reconciliation
```

## 1.1 Systems of record

| Concern | System of record |
|---|---|
| Source CSV | SharePoint `DataQualityDatasets` library |
| Immutable Bronze CSV | SharePoint `DataQualityBronze` library |
| Workflow state | Dataverse |
| Profiles and quality | Dataverse |
| Rules and evidence | Dataverse |
| Mapping and approvals | Dataverse |
| Generic Silver rows | Dataverse |
| Gold recipes/results | Dataverse |
| Orchestration | Power Automate |
| User interface | Power Apps Code App |
| Heavy bounded computation | Stateless FastAPI worker |

## 1.2 Components to remove after parity

The final runtime must not require:

```text
Airflow
Airflow PostgreSQL
SeaweedFS
S3/boto3
ClickHouse
ClickHouse initialization SQL
```

Do not remove these components before the replacement path is connected and
reviewed in a real Power Platform environment.

---

# 2. Non-Negotiable Rules

## 2.1 Raw files never pass through Power Apps

Forbidden:

```text
SharePoint -> browser -> parse/upload CSV -> worker
```

Required:

```text
SharePoint -> Power Automate/backend -> SharePoint Bronze
```

Power Apps triggers work and displays governed state only.

## 2.2 Dataverse is normalized governance storage

Do not store the entire application as one opaque workflow JSON record. Use
tables, lookups, Choice columns, alternate keys, audit, and security roles.

Generic row payloads may use bounded JSON in Silver/Gold records because CSV
schemas are dynamic. Important fields such as dataset, batch, asset, row
number, status, hash, approval, and timestamps remain normal Dataverse columns.

## 2.3 Demo scale is explicit

Default limits:

```text
Maximum files per dataset: 100
Maximum file size: 25 MB
Maximum rows per file: 5,000
Maximum stored evidence per rule: 100
```

Dataverse is suitable for this governed demo. If production volume exceeds the
limits, create a separate Microsoft Fabric migration plan; do not silently use
Dataverse as an unlimited analytical warehouse.

## 2.4 Preserve full parity

Required functions:

- ingestion trigger, run status, progress, retry, and idempotency;
- multi-asset batches and immutable manifests;
- schema discovery and column profiling;
- quality score and issue counts;
- rule proposal, review, execution, and masked evidence;
- mapping proposal, versioning, editing, and approval;
- Bronze approval;
- Silver transformation, rejection evidence, publication, and approval;
- Gold recipe authoring, versioning, review, execution, reconciliation, and
  approval;
- lineage, business activity, audit history, and repeatable runs.

---

# Phase -1 — Tenant and Tool Checkpoints

## Step -1.1 — Power Platform environment

Record without secrets:

```text
Environment name
Environment ID
Environment URL
Dataverse provisioned: Yes / No
Code Apps enabled: Yes / No
Solution publisher prefix: dq
```

Required access:

```text
make.powerapps.com
Power Platform admin center
Microsoft Entra admin center
SharePoint site administration
Power Automate solution authoring
```

## Step -1.2 — CLI

Use Node.js LTS and the npm Code Apps CLI:

```bash
npm install --global @microsoft/power-apps
power-apps --help
```

Use the current npm CLI for Code App data sources, Dataverse operations, flows,
build, and solution push. Do not copy `power.config.json` or connection IDs from
another tenant.

## Step -1.3 — Licensing checkpoint

Confirm every intended user has the required Power Apps/Dataverse licensing.
Confirm Power Automate and custom connector usage is allowed by environment DLP
policy before implementation.

---

# Phase 0 — Branch and Recovery Point

Status: implemented on `feat/sharepoint-powerapps-platform`.

Implementation branch:

```bash
git switch feat/sharepoint-powerapps-platform
```

Recovery point:

```text
adff09e feat: build SharePoint Power Apps data quality platform
```

The transitional branch remains available until tenant parity passes.

---

# Phase 1 — Create the Power Platform Solution

Status: solution manifest implemented; tenant creation pending.

Create an unmanaged development solution:

```text
Display name: AI Data Quality Power Apps Demo
Unique name: AIDataQualityPowerAppsDemo
Publisher prefix: dq
```

The solution must own:

- all custom Dataverse tables, columns, relationships, keys, and Choices;
- security roles;
- Power Automate flows;
- custom connector;
- environment variables;
- connection references;
- Power Apps Code App;
- Dataverse custom APIs only if later required.

No component should be created in the default solution and referenced
implicitly.

---

# Phase 2 — Dataverse Schema

Status: schema manifest implemented; tenant table creation pending.

## Step 2.1 — Core lifecycle tables

```text
dq_dataset
  dq_datasetid                  GUID primary key
  dq_name                       primary name
  dq_datasetkey                 alternate key
  dq_status                     Choice
  dq_selectedassetkey           Text
  dq_currentstep                Choice
  dq_progress                   Whole Number
  dq_revision                   Whole Number
  dq_sourceprovider             Choice

dq_ingestionrun
  dq_ingestionrunid             GUID primary key
  dq_name                       primary name / run ID
  dq_dataset                    Lookup -> dq_dataset
  dq_status                     Choice
  dq_progress                   Whole Number
  dq_force                      Yes/No
  dq_startedat                  DateTime
  dq_completedat                DateTime
  dq_errortype                  Text
  dq_errormessage               Multiline Text

dq_batch
  dq_batchid                    GUID primary key
  dq_name                       primary name / external batch ID
  dq_dataset                    Lookup -> dq_dataset
  dq_sourceversionhash          Text
  dq_manifesturl                URL
  dq_manifestitemid             Text
  dq_manifestetag               Text
  dq_publishedat                DateTime
  dq_status                     Choice

dq_asset
  dq_assetid                    GUID primary key
  dq_name                       primary name / asset key
  dq_batch                      Lookup -> dq_batch
  dq_filename                   Text
  dq_sourceitemid               Text
  dq_sourceetag                 Text
  dq_sourcepath                 Text
  dq_rowcount                   Whole Number
  dq_columncount                Whole Number
  dq_contenthash                Text
```

Alternate keys must make dataset, run, batch, and asset upserts idempotent.

## Step 2.2 — Bronze metadata

```text
dq_bronzesnapshot
  dq_bronzesnapshotid
  dq_name
  dq_asset                      Lookup -> dq_asset
  dq_driveitemid
  dq_etag
  dq_weburl
  dq_contenthash
  dq_sizebytes
  dq_immutablepath
```

Do not duplicate raw CSV bytes in Dataverse. Dataverse stores governed metadata
and the SharePoint Bronze link.

## Step 2.3 — Profiling, rules, and evidence

```text
dq_columnprofile
dq_rule
dq_ruleresult
dq_evidence
```

Required normalized columns include dataset/batch/asset lookups, column name,
physical/semantic type, counts, percentages, status, review actor, rule type,
violation count, masked value, and source row number. Bounded samples and rule
parameters may use JSON text.

## Step 2.4 — Mapping and approvals

```text
dq_mapping
dq_approval
```

Mappings are versioned per asset. Approvals use layer Choice values `BRONZE`,
`SILVER`, and `GOLD` and decision Choice values `PENDING`, `APPROVED`, and
`REJECTED`.

Review/approval operations must use ETag optimistic concurrency so a stale
Power Apps screen cannot overwrite a newer decision.

## Step 2.5 — Generic Silver and Gold

```text
dq_silverrow
  dataset, batch, asset lookups
  source row number
  row hash
  validation status
  bounded payload JSON
  rejection JSON

dq_goldrecipe
  dataset lookup
  recipe key and version
  source assets
  joins, filters, dimensions, measures JSON
  review status and actor

dq_goldresult
  recipe lookup
  batch lookup
  result row hash
  dimensions JSON
  measures JSON
  reconciliation status
```

Do not create one Dataverse table dynamically for every arbitrary CSV schema.

## Step 2.6 — Lineage and audit

Create `dq_activity` for the user-facing timeline. Enable Dataverse auditing on
dataset lifecycle, rule review, mapping, recipe, approval, and status columns.

---

# Phase 3 — SharePoint Source and Bronze

Status: SharePoint Bronze adapter implemented; tenant proof pending.

Source library:

```text
DataQualityDatasets/GenericDatasets/ecommerce-v1/
```

Create a separate Bronze library:

```text
DataQualityBronze/
  GenericDatasets/ecommerce-v1/
    batches/{batch-id}/
      customers.csv
      orders.csv
      order_items.csv
      products.csv
    _manifests/{timestamp}.json
```

Each Bronze asset must retain:

```text
source drive item ID
source eTag/version
Bronze drive item ID
Bronze eTag
SharePoint web URL
SHA-256
file size
row and column counts
batch ID
publication timestamp
```

Use Microsoft Graph app-only `Sites.Selected`. The backend application needs
write access only to the selected SharePoint site because it publishes the
Bronze snapshot. No Graph credential may appear in Power Apps.

---

# Phase 4 — Dataverse Backend Boundary

Status: Dataverse OAuth/OData and normalized repositories implemented; tenant proof pending.

Create infrastructure boundaries:

```text
DataverseAuth
DataverseClient
DataverseWorkflowRepository
DataverseProfileRepository
DataverseRuleRepository
DataverseMappingRepository
DataverseApprovalRepository
DataverseSilverRepository
DataverseGoldRepository
SharePointBronzeStore
```

Dataverse client requirements:

- OAuth for the environment organization URL;
- application user or managed identity;
- bounded OData paging;
- `$select` and `$filter` on every collection request;
- alternate-key upsert;
- `$batch` for bounded multi-record writes;
- Retry-After handling for 429;
- bounded retries for transient 5xx;
- ETag concurrency for review/approval mutations;
- safe, typed 401/403/404/409/429/5xx errors.

FastAPI becomes a stateless worker. It must not retain workflow state locally
or depend on ClickHouse/S3/Airflow after cutover.

---

# Phase 5 — Power Automate Orchestration

Status: Flow contract and connector operation implemented; tenant Flow creation pending.

Create a solution-aware instant flow:

```text
Name: DQ_StartIngestion
Trigger: Power Apps
Inputs: datasetKey, force
```

Flow sequence:

```text
Validate caller and dataset
  -> create dq_ingestionrun
  -> call worker custom connector
  -> worker snapshots SharePoint source to Bronze
  -> worker profiles and persists Dataverse records
  -> update progress/status
  -> write dq_activity
  -> return run ID and final/accepted state
```

Add explicit failure scopes so every error updates `dq_ingestionrun` to FAILED.
Retries must remain idempotent by run ID, source version hash, and batch key.

Optional later flows:

```text
DQ_NotifyApprovalRequired
DQ_ApprovalEscalation
DQ_RetentionMaintenance
```

These optional flows must not block the core demo.

---

# Phase 6 — Power Apps Code App

Status: generated-service gateway implemented; tenant data-source generation/binding pending.

Add Dataverse tables using the npm Power Apps CLI so it generates typed model
and service files. Add `DQ_StartIngestion` with the Code Apps Flow command.

The app must use:

```text
Generated Dataverse services for reads and governed CRUD
Generated Flow service for ingestion
Custom connector only for bounded worker commands not exposed as a Flow
Connection references for environment portability
```

Required views remain:

```text
Workspace
Profiles
Rules and evidence
Mapping
Bronze approval
Silver results and approval
Gold recipes/results and approval
Lineage/activity
```

Remove ClickHouse, SeaweedFS, and Airflow labels from the UI only after the new
services are bound.

---

# Phase 7 — Security, Roles, and ALM

Status: solution variables/roles declared; tenant provisioning pending.

Create roles:

```text
DQ Operator
DQ Reviewer
DQ Approver
DQ Administrator
DQ Backend Application
```

Use least privilege. Operators must not approve their own governed layer unless
the demo policy explicitly allows it.

Create solution environment variables for:

```text
SharePoint host
Source site path/library/folder
Bronze library/root
Worker base URL
Maximum file size
Maximum rows per file
Maximum evidence rows
```

Store secrets outside the solution or use an environment-variable secret backed
by Azure Key Vault where appropriate.

Dev/Test/Prod imports must use connection references and deployment settings,
not hard-coded connection IDs.

---

# Phase 8 — Code Refactor Sequence

Status: repository refactor implemented; legacy deletion deferred until tenant acceptance.

Safe sequence:

1. Add Dataverse schema manifest and logical-name constants.
2. Change domain ports without deleting existing adapters.
3. Implement Dataverse authentication/client/repositories.
4. Implement SharePoint Bronze store.
5. Switch FastAPI composition to Dataverse and SharePoint.
6. Add Power Automate flow and connector definitions.
7. Bind Code App generated Dataverse and Flow services.
8. Prove the tenant path from source through Gold approval.
9. Remove ClickHouse integration and initialization SQL.
10. Remove SeaweedFS/S3 adapter and boto3.
11. Remove Airflow, its PostgreSQL service, DAG, and API client.
12. Simplify Docker Compose to local worker/UI development only.
13. Update all architecture, setup, deployment, and runbook documents.

Per current user direction, do not create or run unit-test files during this
planning/refactor request unless tests are requested separately.

---

# Phase 9 — Tenant Acceptance Checkpoints

The migration is complete only when a real environment proves:

```text
[ ] Code App opens as a non-admin user
[ ] Code App starts DQ_StartIngestion
[ ] Flow run is visible and reports progress
[ ] Four SharePoint source files become one immutable Bronze batch
[ ] Bronze manifest and Dataverse metadata hashes match
[ ] Profiles and quality are visible
[ ] Rule review/execution and masked evidence work
[ ] Mapping approval works with concurrency protection
[ ] Bronze approval gates Silver
[ ] Silver rows and rejections reconcile to source counts
[ ] Silver approval gates Gold
[ ] Gold recipe review, execution, and reconciliation work
[ ] Gold approval completes lifecycle at 100%
[ ] Activity and Dataverse audit history identify actor and timestamp
[ ] Re-running unchanged input is idempotent
[ ] No runtime container uses ClickHouse, SeaweedFS, Airflow, or PostgreSQL
```

---

# Rollback

Until all tenant checkpoints pass:

1. Keep commit `adff09e` and the transitional branch intact.
2. Keep Dataverse work on `feat/sharepoint-powerapps-platform`.
3. Do not delete SharePoint source or Bronze history.
4. Do not remove old adapters before the replacement path is proven.
5. If Dataverse cannot meet the agreed demo limits, stop and create a separate
   Microsoft Fabric architecture decision instead of restoring ClickHouse
   silently.

---

# Official Microsoft References

- [Power Apps Code Apps documentation](https://learn.microsoft.com/en-us/power-apps/developer/code-apps/)
- [Connect a Code App to Dataverse](https://learn.microsoft.com/en-us/power-apps/developer/code-apps/how-to/connect-to-dataverse)
- [Connect a Code App to data](https://learn.microsoft.com/en-us/power-apps/developer/code-apps/how-to/connect-to-data)
- [Dataverse Web API](https://learn.microsoft.com/en-us/power-apps/developer/data-platform/webapi/overview)
- [Dataverse alternate keys](https://learn.microsoft.com/en-us/power-apps/developer/data-platform/define-alternate-keys-entity)
- [Dataverse auditing](https://learn.microsoft.com/en-us/power-platform/admin/manage-dataverse-auditing)
- [Power Platform environment variables](https://learn.microsoft.com/en-us/power-apps/maker/data-platform/environmentvariables)
