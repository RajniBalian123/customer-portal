"""Demo walkthrough: file a bug, sync it through triage to resolution."""

import json
from datetime import timedelta
from pathlib import Path

from src.portal import (Portal, PermissionDenied, Project, Resource, Tenant,
                        User)

ROOT = Path(__file__).resolve().parents[1]


def seed(portal: Portal) -> dict:
    seed = json.loads((ROOT / "data" / "seed.json").read_text(encoding="utf-8"))
    for t in seed["tenants"]:
        portal.add_tenant(Tenant(**t))
    for p in seed["projects"]:
        portal.add_project(Project(**p))
    for r in seed["resources"]:
        portal.add_resource(Resource(**r))
    users = {}
    for u in seed["users"]:
        user = User(**u)
        portal.add_user(user)
        users[u["id"]] = user
    return users


def main() -> None:
    portal = Portal()
    users = seed(portal)
    ana = users["ana"]      # customer, Harborview
    priya = users["priya"]  # customer, Northwind
    sam = users["sam"]      # staff

    print("Tenants: " + ", ".join(t.name for t in portal.tenants.values()))

    # 1. Customer files a bug; a work item appears in the tracker.
    req = portal.submit_request(
        ana, "proj-harbor-billing", "Invoice total is wrong for March",
        "The March invoice shows $1,240 but the usage report adds to $1,180.",
        kind="bug")
    item = portal.work_items[req.work_item_id]
    print(f"\n1. Ana files a bug -> request {req.id} ({req.status}), "
          f"work item {item.id} ({item.status})")

    # 2. Staff triage from the tracker; status syncs back to the request.
    portal.set_work_item_status(sam, item.id, "in progress")
    print(f"2. Sam starts work in the tracker -> request is now '{req.status}'")

    # 3. Comments sync both ways.
    portal.add_comment(sam, req.id, "Found it — March has a duplicated usage line. Fixing now.")
    portal.add_comment(ana, req.id, "Thanks — that matches what we saw.")
    print(f"3. Comments: {len(req.comments)} on the request, "
          f"{len(item.comments)} on the work item (same comments)")

    # 4. Staff resolves; the customer sees it.
    portal.set_work_item_status(sam, item.id, "done")
    print(f"4. Sam resolves the work item -> request is now '{req.status}'")

    # 5. Cross-tenant access is refused.
    try:
        portal.list_requests(priya, "tenant-harborview")
        print("5. ERROR: cross-tenant access was allowed")
    except PermissionDenied as e:
        print(f"5. Priya (Northwind) asks for Harborview's requests -> refused: {e}")

    # 6. Resource reveal with an expiry.
    token = portal.reveal_resource(ana, "res-harbor-invoice-guide")
    print(f"6. Ana reveals the invoice guide -> token valid for 1h: "
          f"{token.is_valid()}")
    expired = portal.reveal_resource(ana, "res-harbor-invoice-guide",
                                     ttl=timedelta(seconds=0))
    print(f"   A token with no window is already invalid: {expired.is_valid()}")

    # 7. Branding is per tenant.
    brand = portal.branding(ana, "tenant-harborview")
    print(f"7. Harborview branding: {brand.name}, {brand.brand_color}")


if __name__ == "__main__":
    main()
