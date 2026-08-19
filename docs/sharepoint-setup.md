# Existing TimerApp source setup

## Reused tenant resources

Do not create a site, document library, folder tree, or CSV upload. Reuse:

```text
https://<tenant>.sharepoint.com/sites/TimerApp
TimerList_AllProject01
TimerList_AllProject02
TimerList_AllProject03
TimerList_AllProject04
```

The lists remain authoritative and are never modified by the worker. Immutable
Bronze snapshots are written to Dataverse tables, not back to SharePoint.

## Entra and Microsoft Graph

Register a single-tenant backend application, add Microsoft Graph application
permission `Sites.Selected`, grant admin consent, and grant that application
`read` on only `TimerApp`.

Resolve the site:

```http
GET https://graph.microsoft.com/v1.0/sites/<tenant>.sharepoint.com:/sites/TimerApp
```

Grant the selected application with an administrator identity:

```http
POST https://graph.microsoft.com/v1.0/sites/{site-id}/permissions
Content-Type: application/json

{
  "roles": ["read"],
  "grantedToIdentities": [{
    "application": {
      "id": "<backend-client-id>",
      "displayName": "AIDataQuality-Backend-Dev"
    }
  }]
}
```

## Runtime configuration

Set `SHAREPOINT_SITE_PATH`, `SHAREPOINT_SOURCE_LISTS`, and `DATAVERSE_URL` from
`.env.example`. Never commit the client secret. Create a Dataverse application
user for the same app registration and assign `DQ Backend Application`.

Verify in order: token, site, four allowlisted lists, bounded list-item paging,
`dq_bronzesnapshot`, `dq_bronzerow`, and reconstructed rows. A 403 usually
means the selected-site grant or Dataverse security role is absent.
