# Power Apps, Dataverse, and Flow deployment

## 1. Create the solution

Create unmanaged solution `AIDataQualityPowerAppsDemo` with publisher prefix
`dq`. Use `power-platform/dataverse/schema.yaml` to create tables, Choices,
alternate keys, auditing, and roles. Add environment variables and connection
references from `power-platform/solution/solution.yaml`.

## 2. Import the worker connector

Import `power-platform/custom-connector/openapi.yaml`, replace the worker host
and Entra API application ID, configure OAuth, and create the solution-owned
connection reference `dq_WorkerConnectorConnection`.

## 3. Build DQ_StartIngestion

Create a solution-aware Power Apps V2 instant flow following
`power-platform/flows/DQ_StartIngestion.contract.json`. Use Dataverse and worker
connection references. The failure scope must always persist a FAILED run.

## 4. Bind the Code App

From `apps/power-app`, authenticate the npm `power-apps` CLI, initialize the app
in this solution, add each `dq_` Dataverse table, add the custom connector, and
add `DQ_StartIngestion`. The CLI writes typed models/services under
`src/generated`; tenant-specific generated output and `power.config.json` stay
uncommitted.

Wire generated services to the interfaces in
`src/services/powerPlatformGateway.ts` and call
`registerPowerPlatformServices` during app startup. Production does not fall
back to the local HTTP gateway.

On Linux, the Power Apps CLI may require the system `libsecret` runtime. Install
it through the workstation's approved package-management process if the CLI
reports `libsecret-1.so.0` missing.

## 5. ALM

Push the Code App into the unmanaged development solution. Export a managed
solution for Test/Prod and provide deployment settings for environment
variables and connection references. Do not export tenant credentials or
user-specific connection IDs into Git.
