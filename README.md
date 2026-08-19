# AI Data Quality — Power Platform Native

Full Generic Dataset Demo implemented around Microsoft Power Platform:

```text
Power Apps Code App + Power Automate
  -> FastAPI stateless worker
  -> existing TimerApp SharePoint lists
  -> Dataverse immutable Bronze, workflow, profiling, Silver, and Gold
```

The runtime no longer starts Airflow, PostgreSQL, SeaweedFS, or ClickHouse.
Legacy adapters remain disconnected only as a recovery aid until a real tenant
passes the acceptance checklist.

## Repository layout

- `apps/power-app`: React/TypeScript Power Apps Code App.
- `apps/api`: bounded profiling/transformation worker and custom connector API.
- `packages/data-quality-core`: domain workflow, Microsoft Graph, and Dataverse adapters.
- `power-platform`: Dataverse schema, solution metadata, Flow contract, and connector OpenAPI.
- `sample-data`: local-only fallback fixture; production does not upload these files.

## Required Microsoft resources

1. Power Platform environment with Dataverse and Code Apps enabled.
2. Solution `AIDataQualityPowerAppsDemo` with publisher prefix `dq`.
3. Existing SharePoint site `/sites/TimerApp` and its four `TimerList_AllProject*` lists.
4. Entra backend application with read access to that selected site and a
   Dataverse application user with solution privileges.
5. Solution-aware flow `DQ_StartIngestion` and worker custom connector.

Copy `.env.example` to `.env`, provide the target tenant values, then run the
worker/UI preview:

```bash
docker compose up --build
```

The API is available at `http://localhost:8000/docs`; the local Code App preview
is at `http://localhost:4173`.

## Documentation

- [Architecture](docs/architecture.md)
- [SharePoint and Graph](docs/sharepoint-setup.md)
- [Power Apps and Dataverse deployment](docs/power-apps-deployment.md)
- [Operations runbook](docs/runbook.md)
- [Migration plan](POWER_APPS_MIGRATION_SETUP_FROM_ZERO(1).md)
