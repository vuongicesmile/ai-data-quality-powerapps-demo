# Power Apps Code App deployment

The frontend is a React/TypeScript Code App in `apps/power-app`. Local
development uses the HTTP gateway. In Power Platform, register the generated
FastAPI OpenAPI document as a custom connector and implement the generated
connector adapter at `registerPowerAppsGateway()` in `platformClient.ts`.

## Prerequisites

- A Power Platform environment with Dataverse and Code Apps enabled.
- Node.js LTS and npm.
- Access to `make.powerapps.com` for the target environment.
- A reachable HTTPS deployment of this API with organization-approved auth.

## Build locally

```bash
cd apps/power-app
npm ci
npm run build
npm run dev
```

The npm project includes `@microsoft/power-apps`. Authenticate and initialize
against the chosen environment using the current `power-apps` CLI; do not copy
a `power.config.json` from another app or tenant. Tenant-specific app IDs,
connection IDs and generated connector files are intentionally gitignored.

## Custom connector

1. Export `https://<api-host>/openapi.json`.
2. Import it as a custom connector in the same solution as the Code App.
3. Configure the API hostname and the environment's authentication policy.
4. Add the connector to the Code App with the npm CLI data-source command.
5. Map generated operations to `PlatformGateway`; call
   `registerPowerAppsGateway(gateway)` during startup.
6. Test ingestion status, profiles, evidence, mapping, approvals, Silver, Gold
   and lineage from a non-admin application user.

## Publish

Run the CLI build/validate workflow, push the Code App into an unmanaged
development solution, publish it, then export/import the solution through the
normal Power Platform ALM path. Keep API URL and connector connection
references environment-specific. Do not place Graph credentials in the Code
App or custom connector client configuration.

