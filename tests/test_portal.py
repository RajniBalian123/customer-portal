"""Checks for tenancy, sync, lifecycle, and reveal tokens."""

import unittest
from datetime import timedelta

from src.portal import (NotFound, PermissionDenied, Portal, Project,
                        Resource, Tenant, User)


def make_portal() -> tuple[Portal, dict[str, User]]:
    portal = Portal()
    portal.add_tenant(Tenant(id="t-a", name="Tenant A", brand_color="#111111"))
    portal.add_tenant(Tenant(id="t-b", name="Tenant B", brand_color="#222222"))
    portal.add_project(Project(id="p-a", tenant_id="t-a", name="Proj A", slug="a"))
    portal.add_project(Project(id="p-b", tenant_id="t-b", name="Proj B", slug="b"))
    portal.add_resource(Resource(id="r-a", project_id="p-a",
                                 name="Guide", path="docs/guide.pdf"))
    users = {
        "alice": User(id="alice", name="Alice", tenant_id="t-a", role="customer"),
        "bob": User(id="bob", name="Bob", tenant_id="t-b", role="customer"),
        "sam": User(id="sam", name="Sam", tenant_id="", role="staff"),
    }
    for u in users.values():
        portal.add_user(u)
    return portal, users


class TestTenancy(unittest.TestCase):
    def test_customer_sees_only_own_tenant(self):
        portal, users = make_portal()
        portal.submit_request(users["alice"], "p-a", "Bug", "body")
        portal.submit_request(users["bob"], "p-b", "Bug", "body")
        self.assertEqual(len(portal.list_requests(users["alice"], "t-a")), 1)
        self.assertEqual(len(portal.list_requests(users["bob"], "t-b")), 1)

    def test_cross_tenant_read_is_refused(self):
        portal, users = make_portal()
        with self.assertRaises(PermissionDenied):
            portal.list_requests(users["alice"], "t-b")

    def test_cross_tenant_comment_is_refused(self):
        portal, users = make_portal()
        req = portal.submit_request(users["alice"], "p-a", "Bug", "body")
        with self.assertRaises(PermissionDenied):
            portal.add_comment(users["bob"], req.id, "hello")

    def test_cross_tenant_resource_is_refused(self):
        portal, users = make_portal()
        with self.assertRaises(PermissionDenied):
            portal.reveal_resource(users["bob"], "r-a")


class TestSync(unittest.TestCase):
    def test_submit_creates_work_item(self):
        portal, users = make_portal()
        req = portal.submit_request(users["alice"], "p-a", "Bug", "body")
        item = portal.work_items[req.work_item_id]
        self.assertEqual(item.title, "[Proj A] Bug")
        self.assertEqual(item.status, "triage")

    def test_work_item_status_syncs_to_request(self):
        portal, users = make_portal()
        req = portal.submit_request(users["alice"], "p-a", "Bug", "body")
        portal.set_work_item_status(users["sam"], req.work_item_id, "in progress")
        self.assertEqual(req.status, "in progress")
        portal.set_work_item_status(users["sam"], req.work_item_id, "done")
        self.assertEqual(req.status, "resolved")

    def test_request_status_syncs_to_work_item(self):
        portal, users = make_portal()
        req = portal.submit_request(users["alice"], "p-a", "Bug", "body")
        portal.set_status(users["sam"], req.id, "resolved")
        self.assertEqual(portal.work_items[req.work_item_id].status, "done")

    def test_comments_sync_both_ways(self):
        portal, users = make_portal()
        req = portal.submit_request(users["alice"], "p-a", "Bug", "body")
        portal.add_comment(users["sam"], req.id, "looking into it")
        item = portal.work_items[req.work_item_id]
        self.assertEqual(len(req.comments), 1)
        self.assertEqual(len(item.comments), 1)
        self.assertEqual(item.comments[0].body, "looking into it")

    def test_customer_cannot_change_work_item(self):
        portal, users = make_portal()
        req = portal.submit_request(users["alice"], "p-a", "Bug", "body")
        with self.assertRaises(PermissionDenied):
            portal.set_work_item_status(users["alice"], req.work_item_id, "done")


class TestResources(unittest.TestCase):
    def test_reveal_token_expires(self):
        portal, users = make_portal()
        token = portal.reveal_resource(users["alice"], "r-a",
                                       ttl=timedelta(seconds=0))
        self.assertFalse(token.is_valid())

    def test_unknown_request_raises_not_found(self):
        portal, users = make_portal()
        with self.assertRaises(NotFound):
            portal.add_comment(users["alice"], "req-9999", "hello")


if __name__ == "__main__":
    unittest.main()
