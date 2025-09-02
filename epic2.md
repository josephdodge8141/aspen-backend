Epic E2 — Security & Auth

Goal: make external API-key auth (for Services) and internal JWT auth (for Members/Users) work; add reusable permission checks for Team ownership, plus a small rate-limit stub. No business endpoints yet—these are cross-cutting guards the rest of the app will reuse.

T2.1 — Password & API-key utilities

Why: Consistent credential handling.

Files & Deliverables

app/security/passwords.py

import bcrypt
def hash_password(plain: str) -> str: ...
def verify_password(plain: str, hashed: str) -> bool: ...


app/security/apikeys.py

import secrets, hashlib
def generate_api_key() -> tuple[str, str, str]:
    # returns (plaintext_key, api_key_hash, last4)
def hash_api_key(plaintext: str) -> str:
    # sha256 or stronger; hex digest


Update docs/context.md → short section “How we store API keys” (store only hash + last4; plaintext shown once at creation time).

AC

 hash_password / verify_password round-trip tested.

 generate_api_key returns 40+ char high-entropy key; hashing is deterministic.

 Docs updated.

Tests

tests/security/test_passwords.py

tests/security/test_apikeys.py

T2.2 — JWT auth for internal users (Members)

Why: Admin/owner actions use JWT.

Files & Deliverables

app/security/jwt.py

import jwt, datetime as dt
from pydantic import BaseModel

class TokenData(BaseModel):
    sub: str  # user_id
    exp: int
    scopes: list[str] = []

def create_access_token(user_id: int, *, scopes: list[str]=[], expires_minutes: int) -> str: ...
def decode_access_token(token: str) -> TokenData: ...


Uses env: JWT_SECRET, JWT_ALG=HS256, ACCESS_TOKEN_EXPIRE_MINUTES=60.

app/api/auth.py (router)

@router.post("/auth/login")
def login(email: EmailStr, password: str) -> {"access_token": str, "token_type": "bearer"}:
    # look up User joined to Member by email, verify password, return JWT


app/api/deps.py

def get_current_user(...) -> User:  # reads Authorization: Bearer <token>


AC

 /auth/login returns 401 for bad creds.

 Valid token yields User via get_current_user.

 Token expires according to env config.

Tests

tests/api/test_auth_login.py: success + failure + expiry.

T2.3 — API-key auth dependency for external callers

Why: Services call the platform with X-API-Key.

Files & Deliverables

app/api/deps.py

from fastapi import Header, HTTPException
from app.models.services import Service

class CallerContext(BaseModel):
    service: Optional[Service] = None
    user: Optional[User] = None

async def get_caller(
    x_api_key: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> CallerContext: ...


Behavior:

If X-API-Key present → resolve Service by api_key_hash; set CallerContext.service.

Else if Authorization: Bearer present → resolve User; set CallerContext.user.

Else → 401.

Index on services.api_key_hash added in E1 (if missing, add migration).

AC

 Valid X-API-Key gives CallerContext.service.

 Invalid key → 401 Problem+JSON.

 Mutual exclusivity not required; if both provided, prefer JWT for admin endpoints and X-API-Key for ingestion (documented in code comment).

Tests

tests/api/test_apikey_auth.py

T2.4 — Team role permission helpers

Why: Reusable enforcement across endpoints.

Files & Deliverables

app/security/permissions.py

from app.models.team import TeamMember, TeamRole
def require_team_member(session: Session, user: User, team_id: int) -> None: ...
def require_team_admin(session: Session, user: User, team_id: int) -> None: ...


Raise HTTPException(status_code=403, detail="forbidden") on failure.

AC

 Helpers used in E3 (Experts) for create/update/archive.

 Unit tests cover positive/negative paths.

Tests

tests/security/test_permissions.py

T2.5 — Rate-limit stub for API keys

Why: Prevent abuse early (simple in-memory stub).

Files & Deliverables

app/middleware/ratelimit.py

# naive token-bucket per api_key_hash in memory; 60 req/min default
# reads X-API-Key; skips JWT calls


Register middleware in app/main.py behind env flag ENABLE_RATELIMIT=true.

AC

 Requests with same X-API-Key beyond threshold → 429 Problem+JSON.

 Off by default in tests; doc comments note stateless prod replacement later (Redis).

Tests

tests/middleware/test_ratelimit.py (mark flaky-safe, low thresholds)

T2.6 — OpenAPI security & docs

Why: Make it discoverable for FE and integrators.

Files & Deliverables

In app/main.py add security schemes:

http bearer for JWT

apiKey in header X-API-Key

Tag descriptions in routers: Auth, Experts, Workflows, Services.

AC

 /openapi.json includes both schemes.

 Swagger UI shows how to set headers.

Tests

tests/api/test_openapi.py sanity check.

Definition of Done (E2)

Both auth modes work with clear errors.

Permission helpers available and used by later epics.

Minimal rate limiting guard exists (disabled by default).

Tests pass in CI.