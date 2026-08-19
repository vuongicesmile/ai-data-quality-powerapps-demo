# SharePoint source and Bronze setup

## Libraries

Create a private site `/sites/AIDataQualityDev` and two document libraries:

```text
DataQualityDatasets/GenericDatasets/ecommerce-v1/
DataQualityBronze/GenericDatasets/
```

Upload the four files from `sample-data/ecommerce-v1` to the source folder.
Enable version history on both libraries. Operators receive read access to the
source; they don't need direct write access to Bronze.

## Entra and Microsoft Graph

Register a single-tenant backend application, add Microsoft Graph application
permission `Sites.Selected`, grant admin consent, and grant that application
`write` on only the development site. Write is required because the worker
publishes immutable Bronze snapshots and manifests.

Resolve the site:

```http
GET https://graph.microsoft.com/v1.0/sites/<tenant>.sharepoint.com:/sites/AIDataQualityDev
```

Grant the selected application with an administrator identity:

```http
POST https://graph.microsoft.com/v1.0/sites/{site-id}/permissions
Content-Type: application/json

{
  "roles": ["write"],
  "grantedToIdentities": [{
    "application": {
      "id": "<backend-client-id>",
      "displayName": "AIDataQuality-Backend-Dev"
    }
  }]
}
```

## Runtime configuration

Set the values from `.env.example`, including `SHAREPOINT_BRONZE_LIBRARY` and
`DATAVERSE_URL`. Never commit the client secret. Create a Dataverse application
user for the same app registration and assign `DQ Backend Application`.

Verify in order: token, site, both drives, source listing, one source download,
Bronze folder creation/upload, manifest download, and Dataverse metadata. A
403 usually means the selected-site grant or Dataverse security role is absent.
