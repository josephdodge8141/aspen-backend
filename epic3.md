Epic E3 — Experts (APIs & Service Layer)

Goal: fully CRUD Experts; attach to Workflows & Services; return list DTOs with counts; validate input_params as JSON; “preflight render” to check template placeholders (syntax only, not LLM).

Schemas (reference for all tasks)

Table experts (from E1).

Joins: expert_workflow, expert_service (from E1).

Status enum: draft | active | archive | historical.

T3.1 — Pydantic/SQLModel schemas for Experts

Why: Clear contracts for requests/responses.

Files & Deliverables

app/schemas/experts.py

from typing import Optional
from sqlmodel import SQLModel
from app.models.common import ExpertStatus

class ExpertBase(SQLModel):
    name: str
    prompt: str
    model_name: str
    status: ExpertStatus = ExpertStatus.draft
    input_params: dict

class ExpertCreate(ExpertBase):
    team_id: int

class ExpertUpdate(SQLModel):
    name: Optional[str] = None
    prompt: Optional[str] = None
    model_name: Optional[str] = None
    status: Optional[ExpertStatus] = None
    input_params: Optional[dict] = None

class ExpertRead(SQLModel):
    id: int
    uuid: str
    name: str
    prompt: str
    model_name: str
    status: ExpertStatus
    input_params: dict
    team_id: int

class ExpertListItem(SQLModel):
    id: int
    name: str
    model_name: str
    status: ExpertStatus
    prompt_truncated: str
    workflows_count: int
    services_count: int
    team_id: int


Truncation rule in mapper: prompt limited to first 120 chars + … if longer.

AC

 Schemas import cleanly; mypy OK.

Tests

tests/schemas/test_expert_schemas.py

T3.2 — Repo functions for list/detail with counts

Why: Efficient queries backing UI.

Files & Deliverables

app/repos/experts_repo.py add:

def list_with_counts(session: Session, *, team_id: int | None = None, status: list[ExpertStatus] | None = None) -> list[ExpertListItem]: ...
def get_with_expanded(session: Session, expert_id: int) -> dict:
    # returns ExpertRead + arrays: workflows[{id,name}], services[{id,name,environment}]


Implement with SQL joins/aggregates; avoid N+1.

AC

 Returns correct counts for joins.

 Filtering by team_id and status works.

Tests

tests/repos/test_experts_repo.py with seed fixtures.

T3.3 — Experts router: CRUD + list

Why: Primary endpoints for Experts page.

Files & Deliverables

app/api/experts.py

router = APIRouter(prefix="/api/v1/experts", tags=["Experts"])

@router.get("") -> list[ExpertListItem]
@router.post("") -> ExpertRead
@router.get("/{expert_id}") -> dict  # expanded (expert + workflows + services)
@router.patch("/{expert_id}") -> ExpertRead
@router.post("/{expert_id}:archive") -> ExpertRead


Dependencies & permissions:

GET "" accepts optional team_id, status[] query; anyone with JWT may list (team filter optional).

POST "" requires JWT; require_team_admin(team_id).

PATCH requires JWT; require_team_admin(expert.team_id).

:archive sets status="archive", same permission as PATCH.

Input validation:

input_params must be JSON object (dict), else 422.

AC

 All endpoints return 200/201 with defined schemas.

 Archive idempotent (archiving an archived expert keeps status).

 Permission errors return 403 Problem+JSON.

Tests

tests/api/test_experts_crud.py: create, list, get, patch, archive, permissions.

T3.4 — Manage Expert ↔ Workflow links

Why: Populate the chips/multiselects.

Files & Deliverables

Endpoints in same router:

@router.post("/{expert_id}/workflows")  # body: {"workflow_ids": [int,...]} -> returns updated expanded view
@router.delete("/{expert_id}/workflows/{workflow_id}") -> 204


Behavior:

POST upserts links for provided ids (add missing, leave existing); does not remove unspecified.

DELETE removes a single link.

Permissions: JWT + team admin of expert.team_id.

AC

 Linking an unknown workflow_id → 404.

 Duplicate insert is a no-op.

 Expanded view reflects new counts.

Tests

tests/api/test_experts_workflow_links.py

T3.5 — Manage Expert ↔ Service links

Why: Control which services can use an expert.

Files & Deliverables

Endpoints:

@router.post("/{expert_id}/services")  # body: {"service_ids": [int,...]} -> expanded view
@router.delete("/{expert_id}/services/{service_id}") -> 204


Permissions: JWT + team admin of expert.team_id.

Validate service ids exist.

AC

 Adds/removes links; counts update.

 Rejects non-existent service with 404.

Tests

tests/api/test_experts_service_links.py

T3.6 — Preflight template validation

Why: Let UI validate prompts and inputs before saving or chatting.

Files & Deliverables

app/services/templates.py

import re
TEMPLATE_RE = re.compile(r"\{\{\s*(.*?)\s*\}\}")
def extract_placeholders(text: str) -> list[str]: ...
def validate_placeholders(placeholders: list[str]) -> list[str]:
    # returns list of warnings/errors for unsupported patterns (syntax only)


Endpoint:

@router.post("/{expert_id}:preflight")
# body: {"prompt": str, "input_params": dict}
# returns: {"placeholders": [...], "warnings": [...], "errors": [...]}


NOTE: Do not execute JSONata—syntax check only (e.g., ensure base. or input. roots, braces closed).

AC

 Malformed {{ / }} reported as error.

 Unknown roots (not base/input) reported as warning.

 Returns 200 with arrays even if errors exist (client can render).

Tests

tests/services/test_templates.py

tests/api/test_experts_preflight.py

T3.7 — DTO mappers & truncation logic

Why: Keep responses consistent.

Files & Deliverables

app/mappers/experts.py

def to_list_item(expert: Expert, workflows_count: int, services_count: int) -> ExpertListItem: ...
def to_read(expert: Expert) -> ExpertRead: ...


Use in repo/router.

AC

 Prompt truncation exactly at 120 chars with ellipsis when needed.

 No internal fields leak (e.g., timestamps can be added later but not required now).

Tests

tests/mappers/test_experts_mapper.py

T3.8 — Seed & Postman collection (dev support)

Why: Make manual QA quick.

Files & Deliverables

Update scripts/seed_dev.py:

Add one Expert and link to a Workflow and a Service.

docs/postman/experts.postman_collection.json:

Requests for CRUD, link/unlink, preflight.

AC

 Running seed creates visible expert in DB.

 Postman import works; /healthz and all endpoints reachable locally.

Tests

N/A (manual QA artifact)

Example API Contracts (for FE & QA)

List Experts

GET /api/v1/experts?team_id=12&status=active&status=draft
→ 200 [
  {
    "id": 1, "name": "ResidentExpert", "model_name": "gpt-4o-mini",
    "status": "active", "prompt_truncated": "Hello {{ base.time }} ...",
    "workflows_count": 2, "services_count": 1, "team_id": 12
  }
]


Get Expert (expanded)

GET /api/v1/experts/1
→ 200 {
  "expert": { ... ExpertRead ... },
  "workflows": [{"id": 5, "name": "LeaseFlow"}],
  "services": [{"id": 3, "name": "TenantPortal", "environment": "prod"}]
}


Create Expert

POST /api/v1/experts
{
  "name": "ResidentExpert",
  "prompt": "Hi {{ base.time }} {{ input.user.name }}",
  "model_name": "gpt-4o-mini",
  "status": "draft",
  "input_params": {"user": {"type": "object"}},
  "team_id": 12
}
→ 201 { ... ExpertRead ... }


Link Workflows

POST /api/v1/experts/1/workflows
{ "workflow_ids": [5,6] }
→ 200 { expanded ... }


Preflight

POST /api/v1/experts/1:preflight
{ "prompt": "Hello {{ base.time }} {{ input.a[*].id }}", "input_params": {"a": []} }
→ 200 { "placeholders": ["base.time","input.a[*].id"], "warnings": [], "errors": [] }

Definition of Done (E3)

Experts CRUD and link management endpoints work with permissions.

List endpoint returns count-enriched DTOs.

Preflight validates placeholder syntax.

Comprehensive tests green in CI.