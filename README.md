# Customer Portal — Demo

A multi-tenant customer portal, rebuilt from scratch with synthetic data.
Customers submit bugs and requests against their projects; each submission
syncs to an internal work item, comments flow both ways, and customers see
only their own tenant.

This is a personal demo project. It captures the pattern — multi-tenancy,
request-to-work-item sync, tenant branding, and resource access — without
any client code, client data, or proprietary material.

## The problem

A customer reporting a bug should not have to email a stranger and hope.
They should open a portal, see their projects, file the issue, watch it
move, and get an answer — while the internal team works the same issue in
their own tracker, with nothing duplicated by hand.

## How it works

```
Customer (tenant A)                Internal team
  submits a request  ──sync──>  work item created in the tracker
  comments on it     ──sync──>  comment appears on the work item
  watches status     <──sync──  staff triage / resolve updates the request
```

- **Tenants are hard walls.** A customer only ever sees their own tenant's
  projects, requests, and resources. Cross-tenant access is refused, not
  filtered.
- **One issue, two views.** The request and the work item are the same
  issue. Status and comments sync both ways; neither side re-types the
  other.
- **Resources are revealed, not linked.** A project document is accessed
  through a short-lived reveal token, so a shared link stops working on its
  own.
- **Branding per tenant.** Each tenant sees its own name, colours, and logo.

## Run it

```bash
python -m src.run_demo
```

Pure standard library, no dependencies. It seeds two fictional tenants,
files a bug, walks it through triage and resolution with comments syncing
both ways, and shows a cross-tenant access attempt being refused.

Run the checks:

```bash
python -m unittest discover -s tests -v
```

## What this proves

- **Tenant isolation as a rule, not a filter.** Every operation checks
  the caller's tenant before touching data. The test suite proves a
  customer from one tenant cannot read, comment on, or resolve another
  tenant's request.
- **Sync without duplication.** The request and the work item share one
  lifecycle; a status change on either side updates the other.
- **Access that expires.** Resource reveal tokens carry an expiry, so
  access is granted for a purpose and a window, not forever.
- **Per-tenant configuration.** Branding and provider keys are scoped to
  the tenant. Keys are stored as references and are never printed or
  returned by the API.

## Layout

- `src/portal.py` — the domain: tenants, users, projects, requests,
  work items, comments, resources, and the sync rules.
- `src/run_demo.py` — the demo walkthrough.
- `data/seed.json` — two fictional tenants and their projects.
- `docs/design.md` — the full design: tenancy, auth, sync, chat
  integrations, per-tenant keys, observability.
- `tests/` — checks for isolation, sync, lifecycle, and reveal tokens.

## What production adds

Real authentication (SSO with organization support), a database instead of
in-memory state, a web UI, chat integrations (Slack/Teams), email intake
for a support inbox, per-tenant AI provider keys encrypted at rest, and a
model gateway for AI features. None of those are claimed here — the demo is
the tenancy and sync mechanism, local only.
