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
 SharePoint source     Microsoft Dataverse
 SharePoint Bronze     governance + Silver/Gold
```

## Ownership boundaries

- Power Apps contains presentation and user intent. It never handles raw CSV.
- Power Automate owns user-triggered orchestration, correlation, failure scope,
  and run-status updates.
- FastAPI owns bounded CSV parsing, profiling, rule execution, transformations,
  and reconciliation. It owns no durable state.
- SharePoint owns source files and immutable Bronze objects/manifests.
- Dataverse owns workflow, profiles, rules, evidence, mappings, approvals,
  generic Silver rows, Gold recipes/results, activity, audit, and security.

## Dataverse persistence

`power-platform/dataverse/schema.yaml` is the logical schema source. Records
use alternate keys for idempotent upsert, Choice columns for lifecycle/review
state, ETags for optimistic concurrency, and Dataverse audit on governed
tables. Dynamic CSV payloads use bounded JSON only inside `dq_silverrow` and
`dq_goldresult`; identifiers, hashes, relationships, status, and timestamps are
normal columns.

## Bronze paths

```text
DataQualityBronze/GenericDatasets/{dataset}/batches/{batch-id}/{file}.csv
DataQualityBronze/GenericDatasets/{dataset}/_manifests/{timestamp}.json
```

The manifest retains source and Bronze item IDs/eTags, SHA-256, row/column
counts, size, batch, and publication time. An unchanged set of source versions
returns the existing batch unless `force=true`.

## Data limits

This Dataverse-first variant is a governed demo: 100 files, 25 MB/file, and
5,000 rows/file by default. Move high-volume analytical Silver/Gold to Microsoft
Fabric in a separate architecture; do not increase Dataverse limits silently.

## Recovery boundary

Old Airflow/S3/ClickHouse source files are disconnected from composition and
Docker. They remain temporarily for recovery until tenant acceptance passes;
then remove them in a dedicated cleanup commit.
