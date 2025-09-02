Epic E7 — Services & Segments

Goal: CRUD for Service and ServiceSegment; API key lifecycle; link Services to Experts/Workflows; helper endpoints for FE (counts, exposure lists). We’ll keep segments simple per your schema: ServiceSegment is a named grouping, ServiceUser.segment_key (JSON) remains for future identity work; here we won’t add DB columns beyond your structures.

Shared conventions (E7)

Base path: /api/v1/services

Admin (JWT) required for management; X-API-Key unauth only for later ingestion (not covered here).

API key is stored hashed; plaintext shown once on creation/rotation.

T7.1 — Schemas for Service & ServiceSegment

Files

app/schemas/services.py

class ServiceBase(SQLModel):
    name: str
    environment: Environment

class ServiceCreate(ServiceBase): ...
class ServiceRead(SQLModel):
    id: int
    name: str
    environment: Environment
    api_key_last4: str | None = None

class ServiceRotateKeyRead(SQLModel):
    id: int
    name: str
    environment: Environment
    api_key_plaintext: str  # ONLY on rotation response
    api_key_last4: str

class ServiceSegmentBase(SQLModel):
    name: str

class ServiceSegmentCreate(ServiceSegmentBase): ...
class ServiceSegmentRead(SQLModel):
    id: int
    service_id: int
    name: str


AC

 Importable; mypy clean.

T7.2 — Service router: create/list/read/delete + rotate key

Files

app/api/services.py

router = APIRouter(prefix="/api/v1/services", tags=["Services"])

@router.post("") -> ServiceRead  # returns with last4; plus separate plaintext in header?
@router.get("") -> list[ServiceRead]
@router.get("/{service_id}") -> ServiceRead
@router.delete("/{service_id}") -> 204
@router.post("/{service_id}:rotate-key") -> ServiceRotateKeyRead


Key creation/rotation:

On create: generate key via generate_api_key(), store hash + last4, return ServiceRead and include plaintext in a separate response field only when explicitly requested: we’ll follow ServiceRotateKeyRead pattern but also return plaintext on initial create in a "api_key_plaintext" field (document: show once).

Do not log plaintext.

Permissions:

JWT required. Team scoping not applied to Service (org-level); if you want team tie-in later, we’ll add team_id to Service—not part of this epic.

AC

 Plaintext key visible only on create/rotate responses.

 List/read never expose plaintext; show api_key_last4 only.

 Delete removes service and cascades segments and links (FKs).

Tests

tests/api/test_services_crud.py: create/list/read/delete; rotation returns new plaintext and updates last4.

T7.3 — ServiceSegments router: CRUD

Files

In app/api/services.py:

@router.post("/{service_id}/segments") -> ServiceSegmentRead
@router.get("/{service_id}/segments") -> list[ServiceSegmentRead]
@router.delete("/{service_id}/segments/{segment_id}") -> 204


Unique constraint: (service_id, name) enforced by E1.

AC

 Duplicate segment name rejected (409).

 Deleting non-existent id → 404.

Tests

tests/api/test_service_segments.py.

T7.4 — Link Service ↔ Expert/Workflow

Why: Controls what a service can access.

Files

In app/api/services.py:

@router.post("/{service_id}/experts")      # body {"expert_ids":[...]} -> returns {"linked":[...]}
@router.delete("/{service_id}/experts/{expert_id}") -> 204

@router.post("/{service_id}/workflows")    # body {"workflow_ids":[...]} -> returns {"linked":[...]}
@router.delete("/{service_id}/workflows/{workflow_id}") -> 204


Check existence; upsert semantics (no duplicate links); return updated link lists.

AC

 Linking an id not found → 404.

 No duplicates inserted.

 Deleting absent link is a no-op 204.

Tests

tests/api/test_service_links.py.

T7.5 — Exposure helper endpoints (for FE chips)

Files

In app/api/services.py:

@router.get("/{service_id}/exposure")
# -> {"experts":[{"id","name"}], "workflows":[{"id","name"}], "counts": {"experts":N,"workflows":M}}


Optimized join queries; no N+1.

AC

 Returns stable ordering by name.

Tests

tests/api/test_service_exposure.py.

T7.6 — Guard for X-API-Key → Service resolution

Why: Align with E2 dependency and ensure index.

Files

Confirm services.api_key_hash indexed.

app/api/deps.py: already returns CallerContext.service (E2).

Add smoke route for integrators (dev only):

@router.get("/whoami")
def whoami(caller: CallerContext = Depends(get_caller)):
    # if service, return {service_id, name, environment, segments:[...]}
    # if user, return {user_id, email}


AC

 GET /api/v1/services/whoami works with either auth mode.

Tests

tests/api/test_services_whoami.py.

T7.7 — Postman & docs

Files

docs/postman/services.postman_collection.json: CRUD, segments, linking, exposure, whoami.

docs/services.md: “how to register a Service, get API key, and link to Experts/Workflows”.

AC

 Manual QA: full flow works.

E7 Definition of Done

Services & segments managed via APIs; secure key lifecycle in place.

Service exposure to Experts/Workflows managed and queryable.

X-API-Key resolution tested and documented