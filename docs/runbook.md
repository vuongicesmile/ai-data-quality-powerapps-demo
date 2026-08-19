# Power Platform runbook

## Local worker/UI preview

Copy `.env.example` to `.env`, supply a development SharePoint/Dataverse
environment and start:

```bash
docker compose up --build
```

Only the stateless worker and frontend preview run locally. Dataverse and
SharePoint remain the durable services; there are no local Airflow, PostgreSQL,
SeaweedFS, or ClickHouse containers.

## Governed lifecycle

1. Start `DQ_StartIngestion` from the Code App.
2. Observe `dq_ingestionrun` progress and the SharePoint Bronze manifest.
3. Discover/profile, then review and execute rules.
4. Review mappings and approve Bronze.
5. Publish generic Silver rows, inspect rejections, and approve Silver.
6. Author/version/review a Gold recipe, publish results, reconcile, and approve
   Gold.
7. Confirm lifecycle 100%, `dq_activity`, and Dataverse audit history.

## Operational diagnosis

- `401`: worker Entra credential/token audience is invalid.
- `403` Graph: verify `Sites.Selected` and selected-site write grant.
- `403` Dataverse: verify application user and `DQ Backend Application` role.
- `404`: verify site, library, folder, Dataverse entity-set logical names, and
  solution deployment.
- `409/412`: stale Dataverse ETag; refresh before repeating review/approval.
- `429`: respect Retry-After; the adapters retry within configured bounds.
- Flow FAILED: inspect the failure scope and correlated `dq_ingestionrun`.

## Tenant acceptance

Use the Phase 9 checklist in the migration document. Do not remove the
disconnected legacy adapters until the real tenant completes the full
SharePoint-to-Gold path.
