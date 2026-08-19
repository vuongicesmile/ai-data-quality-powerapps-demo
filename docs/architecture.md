# Power Platform-native architecture

```text
Power Apps Code App
  |-- generated Dataverse services: state, reviews, approvals, lineage
  `-- generated DQ_StartIngestion Flow service
                    |
                    v
          Power Automate cloud flow
                    |
                    v
          FastAPI stateless worker
             |              |
             v              v
 TimerApp lists        Microsoft Dataverse
                       Bronze + governance + Silver/Gold
```

## Ownership boundaries

- Power Apps contains presentation and user intent. It never handles raw list rows.
- Power Automate owns user-triggered orchestration, correlation, failure scope,
  and run-status updates.
- FastAPI owns bounded list-row normalization, profiling, rule execution, transformations,
  and reconciliation. It owns no durable state.
- SharePoint `TimerApp` owns the four authoritative source lists.
- Dataverse owns immutable Bronze rows, workflow, profiles, rules, evidence, mappings, approvals,
  generic Silver rows, Gold recipes/results, activity, audit, and security.

## Dataverse persistence

`power-platform/dataverse/schema.yaml` is the logical schema source. Records
use alternate keys for idempotent upsert, Choice columns for lifecycle/review
state, ETags for optimistic concurrency, and Dataverse audit on governed
tables. Dynamic list payloads use bounded JSON inside `dq_bronzerow`,
`dq_silverrow`, and `dq_goldresult`; identifiers, hashes, relationships,
status, and timestamps are normal columns.

## Bronze identity

```text
dq_bronzesnapshot: one record per batch/list
dq_bronzerow: one immutable record per batch/list/source item
```

The batch retains list IDs, source item IDs/eTags, canonical SHA-256 hashes,
row/column counts, and capture time. The batch key derives from the combined
source versions, so an unchanged rerun upserts the same immutable records.

## Data limits

This Dataverse-first variant is a governed demo: four allowlisted lists and
5,000 rows/list/run by default. Move high-volume analytical Silver/Gold to Microsoft
Fabric in a separate architecture; do not increase Dataverse limits silently.

## Recovery boundary

Old Airflow/S3/ClickHouse source files are disconnected from composition and
Docker. They remain temporarily for recovery until tenant acceptance passes;
then remove them in a dedicated cleanup commit.
