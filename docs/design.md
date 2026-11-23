# Design: a multi-tenant customer portal

Status: demo of the tenancy and sync pattern, with synthetic data. It does
not claim authentication, a database, a web UI, chat integrations, or email
intake.

## 1. The flow

```
Customer opens the portal (their tenant)
  -> sees their projects, requests, and resources — nothing else
  -> files a bug or request against a project
  -> an internal work item is created from it, in the team's tracker
  -> staff triage, comment, and resolve the work item
  -> status and comments sync back to the request
  -> customer watches it move and gets the answer in the portal
```

The portal and the tracker hold the same issue in two shapes. Nothing is
re-typed, and neither side has to learn the other's tool.

## 2. Tenancy is a wall, not a filter

Every operation takes the caller and checks their tenant before touching
data:

- A customer reads only their own tenant's projects, requests, and
  resources. Asking for another tenant's request is refused with a
  permission error, not an empty list — an empty list would hide a bug.
- Staff (internal) can see all tenants, but only through the internal view;
  they never act as a customer.
- Branding, provider keys, and integrations are all scoped to the tenant.
  A tenant's key never appears in another tenant's context, and keys are
  stored as references — never printed, never returned by an API.

Tenancy is enforced in the service layer, not the UI. A UI filter can be
bypassed; a service check cannot.

## 3. One issue, two views

A request and its work item share one lifecycle:

| Request status | Work item status |
|---|---|
| open | triage |
| in progress | in progress |
| resolved | done |
| reopened | triage |

A status change on either side updates the other. A comment on either side
appears on the other, attributed to its author. The sync is the product:
without it the portal is a mailbox and the tracker is a second mailbox.

## 4. Resources are revealed, not linked

A project document is never served from a permanent URL. A customer asks
to view it and gets a short-lived reveal token. The token names the
resource, the tenant, and an expiry; after expiry it stops working on its
own. Access is granted for a purpose and a window, not forever.

## 5. Chat and email intake

Customers also reach the team through chat (Slack/Teams) and email. Both
feed the same request pipeline: a chat message or an inbound email that
mentions a project becomes a request, and replies go back through the
channel it came from. The portal is one front door among several, not the
only one.

## 6. Per-tenant AI configuration

Each tenant can bring its own AI provider key, stored encrypted at rest.
Model calls go through a gateway that attributes usage to the tenant, so
cost and usage are visible per customer. Tenant-less tasks use the platform
provider. A tenant with no key gets no AI features, not a shared key.

## 7. Observability

Every request records: who filed it, when, which project, how long each
status lasted, and how many comments crossed the sync. That is the data for
the questions that matter: which projects generate the most issues, which
issues wait longest for triage, and whether customers get answers in the
portal or have to chase by email.

## 8. What production adds

- **Authentication:** SSO with organization/team support; invites by
  email; staff management with feature grants per team.
- **Persistence:** a database (relational, with a queue for the sync
  jobs) instead of in-memory state.
- **Web UI:** the portal itself, with tenant branding, project pages,
  documentation, releases, and a help centre.
- **Integrations:** Slack and Teams chat, a support inbox fed by inbound
  email, and a public API with OAuth-protected MCP access.
- **Deployment:** containers, managed Postgres, a secret store for
  per-tenant keys, and a model gateway.
