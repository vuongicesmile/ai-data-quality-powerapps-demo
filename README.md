# AI Data Quality — SharePoint + Power Apps

A complete Generic Dataset Demo data platform. SharePoint Online replaces
Google Drive while the governed Bronze, profiling, rules, approval, Silver,
Gold, evidence, and lineage workflow remains available through FastAPI and a
Power Apps Code App.

```text
SharePoint → Microsoft Graph → Airflow → SeaweedFS Bronze
    → FastAPI profiling workflow → ClickHouse Silver/Gold → Power Apps
```

## Quick start

```bash
cp .env.example .env
docker compose up -d clickhouse seaweedfs
docker compose build api
docker compose up -d --no-deps api
python3 scripts/smoke_test.py
```

With `DATA_SOURCE_PROVIDER=local`, the complete demo uses the four canonical
files under `sample-data/ecommerce-v1` and needs no Microsoft credentials.
Switch to `sharepoint` after completing `docs/sharepoint-setup.md`.

Run `docker compose up --build` when the full Airflow orchestration and Code App
preview are required. Open:

- API docs: http://localhost:8000/docs
- Airflow: http://localhost:8080
- Local Code App: http://localhost:4173

Documentation:

- [Architecture](docs/architecture.md)
- [SharePoint and Graph setup](docs/sharepoint-setup.md)
- [Power Apps deployment](docs/power-apps-deployment.md)
- [Local and full-platform runbook](docs/runbook.md)
- [Migration checklist](POWER_APPS_MIGRATION_SETUP_FROM_ZERO(1).md)
