"""Customer portal domain: tenancy, requests, work-item sync, resources.

Multi-tenant by construction: every operation takes the caller and checks
their tenant before touching data. A request and its internal work item are
one issue in two shapes — status and comments sync both ways.
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

REQUEST_TO_WORK = {"open": "triage", "in progress": "in progress",
                   "resolved": "done", "reopened": "triage"}
WORK_TO_REQUEST = {"triage": "open", "in progress": "in progress",
                   "done": "resolved"}


class PermissionDenied(Exception):
    pass


class NotFound(Exception):
    pass


@dataclass
class Tenant:
    id: str
    name: str
    brand_color: str
    logo: str = ""
    provider_key_ref: str = ""  # reference only; the key itself never leaves the store


@dataclass
class User:
    id: str
    name: str
    tenant_id: str  # "" for internal staff
    role: str       # customer / staff / admin


@dataclass
class Project:
    id: str
    tenant_id: str
    name: str
    slug: str


@dataclass
class Comment:
    author_id: str
    author_name: str
    body: str
    at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class WorkItem:
    id: str
    title: str
    status: str = "triage"
    comments: list[Comment] = field(default_factory=list)


@dataclass
class Request:
    id: str
    tenant_id: str
    project_id: str
    title: str
    body: str
    kind: str  # bug / request
    status: str = "open"
    work_item_id: str = ""
    comments: list[Comment] = field(default_factory=list)


@dataclass
class Resource:
    id: str
    project_id: str
    name: str
    path: str


@dataclass
class RevealToken:
    token: str
    resource_id: str
    tenant_id: str
    expires_at: datetime

    def is_valid(self, now: datetime | None = None) -> bool:
        return (now or datetime.now(timezone.utc)) < self.expires_at


class Portal:
    def __init__(self) -> None:
        self.tenants: dict[str, Tenant] = {}
        self.users: dict[str, User] = {}
        self.projects: dict[str, Project] = {}
        self.requests: dict[str, Request] = {}
        self.work_items: dict[str, WorkItem] = {}
        self.resources: dict[str, Resource] = {}
        self._next = 0

    def _id(self, prefix: str) -> str:
        self._next += 1
        return f"{prefix}-{self._next:04d}"

    # -- tenancy ---------------------------------------------------------
    def _check_access(self, user: User, tenant_id: str) -> None:
        if user.role == "staff":
            return  # internal view sees all tenants
        if user.tenant_id != tenant_id:
            raise PermissionDenied(
                f"{user.name} belongs to a different tenant")

    def _get_request(self, user: User, request_id: str) -> Request:
        req = self.requests.get(request_id)
        if req is None:
            raise NotFound(f"request {request_id} not found")
        self._check_access(user, req.tenant_id)
        return req

    # -- seed helpers ----------------------------------------------------
    def add_tenant(self, tenant: Tenant) -> None:
        self.tenants[tenant.id] = tenant

    def add_user(self, user: User) -> None:
        self.users[user.id] = user

    def add_project(self, project: Project) -> None:
        self.projects[project.id] = project

    def add_resource(self, resource: Resource) -> None:
        self.resources[resource.id] = resource

    # -- requests --------------------------------------------------------
    def list_requests(self, user: User, tenant_id: str) -> list[Request]:
        self._check_access(user, tenant_id)
        return [r for r in self.requests.values() if r.tenant_id == tenant_id]

    def submit_request(self, user: User, project_id: str, title: str,
                       body: str, kind: str = "bug") -> Request:
        project = self.projects.get(project_id)
        if project is None:
            raise NotFound(f"project {project_id} not found")
        self._check_access(user, project.tenant_id)
        req = Request(id=self._id("req"), tenant_id=project.tenant_id,
                      project_id=project_id, title=title, body=body, kind=kind)
        item = WorkItem(id=self._id("work"), title=f"[{project.name}] {title}")
        req.work_item_id = item.id
        self.requests[req.id] = req
        self.work_items[item.id] = item
        return req

    def add_comment(self, user: User, request_id: str, body: str) -> Comment:
        req = self._get_request(user, request_id)
        comment = Comment(author_id=user.id, author_name=user.name, body=body)
        req.comments.append(comment)
        item = self.work_items[req.work_item_id]
        item.comments.append(comment)  # sync: same comment, both views
        return comment

    def set_status(self, user: User, request_id: str, status: str,
                   from_work_item: bool = False) -> Request:
        req = self._get_request(user, request_id)
        if status not in REQUEST_TO_WORK:
            raise ValueError(f"unknown status: {status}")
        req.status = status
        item = self.work_items[req.work_item_id]
        item.status = REQUEST_TO_WORK[status]
        return req

    def set_work_item_status(self, user: User, work_item_id: str,
                             status: str) -> WorkItem:
        if user.role != "staff":
            raise PermissionDenied("only staff change work items")
        item = self.work_items.get(work_item_id)
        if item is None:
            raise NotFound(f"work item {work_item_id} not found")
        if status not in WORK_TO_REQUEST:
            raise ValueError(f"unknown status: {status}")
        item.status = status
        req = next(r for r in self.requests.values()
                   if r.work_item_id == work_item_id)
        req.status = WORK_TO_REQUEST[status]  # sync back to the request
        return item

    # -- resources -------------------------------------------------------
    def reveal_resource(self, user: User, resource_id: str,
                        ttl: timedelta = timedelta(hours=1)) -> RevealToken:
        resource = self.resources.get(resource_id)
        if resource is None:
            raise NotFound(f"resource {resource_id} not found")
        project = self.projects[resource.project_id]
        self._check_access(user, project.tenant_id)
        return RevealToken(
            token=secrets.token_urlsafe(24), resource_id=resource_id,
            tenant_id=project.tenant_id,
            expires_at=datetime.now(timezone.utc) + ttl)

    def branding(self, user: User, tenant_id: str) -> Tenant:
        self._check_access(user, tenant_id)
        tenant = self.tenants.get(tenant_id)
        if tenant is None:
            raise NotFound(f"tenant {tenant_id} not found")
        return tenant
