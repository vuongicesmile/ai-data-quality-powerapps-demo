# Local runbook

## Fast deterministic mode

This mode uses local CSV as the source but runs the real SeaweedFS Bronze,
FastAPI workflow and ClickHouse Silver/Gold adapters.

```bash
cp .env.example .env
docker compose up -d clickhouse seaweedfs
docker compose build api
docker compose up -d --no-deps api
python3 scripts/smoke_test.py
```

Success is:

```text
PASS: 13 lifecycle actions; progress=100%
```

Open API docs at `http://localhost:8000/docs`. Stop services with
`docker compose down`; add `--volumes` only when intentionally deleting local
demo data.

## Full orchestration mode

Set `ORCHESTRATION_MODE=airflow` and run:

```bash
docker compose up --build
```

Airflow is at `http://localhost:8080`, the API at `http://localhost:8000`, and
the Code App preview at `http://localhost:4173`. The API triggers
`sharepoint_generic_dataset_bronze_ingestion`; on success it syncs the latest
Bronze manifest into the workflow.

For a real SharePoint run, also set the variables in `sharepoint-setup.md`.

## Verification commands

```bash
docker run --rm -v "$PWD:/work" -w /work python:3.11-slim \
  sh -c "pip install -q -e '.[dev]' && ruff check . && pytest -q"
cd apps/power-app && npm ci && npm run build
docker compose config --quiet
python3 scripts/smoke_test.py
```

Inspect service health and logs with `docker compose ps` and
`docker compose logs --tail=100 <service>`. A failed layer precondition returns
HTTP 409; upstream authentication, permission and availability failures have
explicit error types in the JSON envelope.

