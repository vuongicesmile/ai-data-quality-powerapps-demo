# SharePoint and Microsoft Graph setup

## 1. Create the source

Create a private SharePoint Team Site at `/sites/AIDataQualityDev`, a document
library named `DataQualityDatasets`, and this folder:

```text
GenericDatasets/ecommerce-v1/
  customers.csv
  orders.csv
  order_items.csv
  products.csv
```

Upload the four files from `sample-data/ecommerce-v1`. Confirm the intended
owner can open the site, library and each CSV in the browser first.

## 2. Register the backend identity

Create a single-tenant Entra application, add Microsoft Graph application
permission `Sites.Selected`, and grant admin consent. Create a development
client secret; use a managed identity, workload identity or certificate for a
production deployment.

An administrator must separately grant the runtime application read access to
the selected site. `Sites.Selected` by itself grants no site access.

Resolve the site:

```http
GET https://graph.microsoft.com/v1.0/sites/<tenant>.sharepoint.com:/sites/AIDataQualityDev
```

Grant the application:

```http
POST https://graph.microsoft.com/v1.0/sites/{site-id}/permissions
Content-Type: application/json

{
  "roles": ["read"],
  "grantedToIdentities": [{
    "application": {
      "id": "<AZURE_CLIENT_ID>",
      "displayName": "AIDataQuality-Backend-Dev"
    }
  }]
}
```

## 3. Configure the runtime

Copy `.env.example` to `.env` and set:

```dotenv
DATA_SOURCE_PROVIDER=sharepoint
AZURE_TENANT_ID=<tenant-guid>
AZURE_CLIENT_ID=<application-guid>
AZURE_CLIENT_SECRET=<development-secret>
SHAREPOINT_HOST=<tenant>.sharepoint.com
SHAREPOINT_SITE_PATH=/sites/AIDataQualityDev
SHAREPOINT_LIBRARY=DataQualityDatasets
SHAREPOINT_DATASET_FOLDER=GenericDatasets/ecommerce-v1
```

Never commit `.env`, a token or a secret. A `403` normally means the selected
site grant is absent; `404` means the site, library or folder does not match.

## 4. Verify in increasing scope

1. Acquire a client-credentials token for Graph `.default`.
2. Resolve the site.
3. List `/sites/{site-id}/drives` and find `DataQualityDatasets`.
4. List the dataset folder children.
5. Download one drive item through `/content`.
6. Set `ORCHESTRATION_MODE=local` and trigger API ingestion, or enable Airflow
   and trigger `sharepoint_generic_dataset_bronze_ingestion`.
7. Confirm the Bronze manifest has `provider=sharepoint`, source item IDs,
   eTags, hashes and all four assets.

