# Architecture

## Runtime flow

```text
Power Apps Code App
        |
        | governed JSON commands and read models
        v
FastAPI application API --------> Airflow REST API
        |                              |
        |                              v
        |                    SharePoint Online
        |                    via Microsoft Graph
        |                              |
        |                              v
        +---------------------- SeaweedFS Bronze
        |                              |
        v                              v
profiling, rules, evidence, mapping and approval workflow
        |
        +------------> ClickHouse workflow state and audit
        +------------> ClickHouse Silver tables
        +------------> ClickHouse governed Gold tables
```

Power Apps never receives raw CSV bytes. It starts and observes ingestion, then
uses provider-neutral workflow endpoints. Microsoft Graph credentials exist
only in Airflow/backend configuration.

## Boundaries

- `apps/api`: thin HTTP transport and dependency composition.
- `packages/data-quality-core/domain`: serializable models, errors and ports.
- `packages/data-quality-core/application`: ingestion and governed lifecycle.
- `packages/data-quality-core/integrations`: Graph, S3, Airflow and ClickHouse.
- `orchestration/airflow`: scheduled/triggered source-to-Bronze execution.
- `apps/power-app`: React Power Apps Code App; no source-provider logic.

`DatasetSource`, `BronzeStore`, `StateRepository`, and `WarehouseRepository`
keep vendor code outside application logic. `LocalDatasetSource` is a
deterministic development substitute for SharePoint; it exercises the same
Bronze and downstream path.

## Governed state machine

```text
ingest -> discover -> profile -> approve Bronze
       -> approve mappings -> publish Silver -> approve Silver
       -> propose/review recipe -> publish Gold -> approve Gold
```

Rules can be reviewed and executed after profiling. Evidence masks sensitive
values and lineage records activity across source, Bronze, profile, Silver and
Gold. Every mutation persists a new revision in ClickHouse.

## Data guarantees

- Bronze keys are immutable and content-addressed by manifest metadata.
- Source eTag/version, SHA-256, row counts and columns are retained.
- CSV count/size, Graph pagination and downloads have explicit bounds.
- Silver is published through staging and atomic `EXCHANGE TABLES`.
- Gold is generated only from an approved, versioned recipe after Silver
  approval and reports reconciliation metadata.
- App-only `Sites.Selected` access is preferred over tenant-wide site access.

