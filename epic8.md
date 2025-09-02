Epic E8 — FastMCP Integration

Goal: Ship a tiny MCP-compatible service that (1) fetches the set of Workflows exposed to a given Expert from our app and (2) presents them as tool annotations to the AI runtime. Also expose a small app endpoint that returns those tool descriptors. Package the MCP as a separate image (Fargate) with env-based config.

Shared conventions

MCP service is stateless, reads APP_BASE_URL, APP_API_KEY, MCP_PORT, ENV.

App exposes a read-only endpoint that returns tool descriptors for an expert: one tool per workflow the expert is linked to.

Each tool’s call maps to POST /api/v1/workflows/{id}:execute (from E4/E6).

T8.1 — App endpoint to list “tools” for an Expert

Why: Source of truth for MCP server.

Files

app/api/mcp.py

router = APIRouter(prefix="/api/v1/mcp", tags=["MCP"])
@router.get("/experts/{expert_id}/tools")
def list_tools_for_expert(expert_id: int, caller: CallerContext = Depends(get_caller)) -> dict:
    """
    Returns a list of tool descriptors for workflows linked to expert.
    Permissions:
      - JWT: require_team_member(expert.team_id)
      - X-API-Key (Service): ensure_service_can_use_expert
    """


Tool descriptor (contract returned by app)

{
  "expert": {"id": 1, "name": "ResidentExpert"},
  "tools": [
    {
      "name": "workflow_42",
      "title": "LeaseFlow Execute",
      "description": "Executes workflow LeaseFlow via API.",
      "args_schema": { "type":"object", "properties": { "starting_inputs": { "type":"object" } }, "required": [] },
      "invoke": { "method":"POST", "path": "/api/v1/workflows/42:execute" }
    }
  ]
}


AC

 Returns 200 with one tool per linked workflow (expert_workflow).

 Permissions enforced (JWT team member OR service linked to expert).

 Stable tool name is workflow_{id}.

Tests

tests/api/test_mcp_tools.py: JWT happy path, service happy path, 403 denied.

T8.2 — MCP server (separate service) scaffolding

Why: Standalone service to adapt app tools to MCP protocol.

Files

New folder: mcp-server/

mcp-server/app.py (FastAPI or small HTTP server)

mcp-server/client_app.py (adapter that calls our main app)

mcp-server/requirements.txt

mcp-server/Dockerfile (slim python image)

mcp-server/README.md

Behavior (HTTP façade for MCP)

GET /healthz → 200

GET /tools?expert_id=<id>

Calls our app /api/v1/mcp/experts/{id}/tools using APP_API_KEY in X-API-Key.

Adapts to MCP tool JSON if needed (see below).

POST /call with body:

{ "tool_name": "workflow_42", "arguments": { "starting_inputs": { ... } } }


Translates to POST {APP_BASE_URL}/api/v1/workflows/42:execute

Streaming/logging not required; returns whatever our app returns.

If your runtime expects strict MCP wire protocol (WebSocket/STDIO), keep this HTTP façade and later add the transport shim; for now we keep juniors on HTTP where they can test easily.

AC

 Local MCP server can list tools and call them against the local app (via compose).

 Errors from app pass through with status + message.

Tests

mcp-server/tests/test_tools_and_call.py (pytest, using httpx).

T8.3 — MCP server config & Docker

Files

mcp-server/Dockerfile (multi-stage, non-root)

mcp-server/.env.example: APP_BASE_URL, APP_API_KEY, MCP_PORT=8080, ENV=dev

docker-compose.yml (extend root) with profile mcp:

services:
  mcp:
    build: ./mcp-server
    ports: ["8080:8080"]
    environment:
      - APP_BASE_URL=http://api:8000
      - APP_API_KEY=${APP_API_KEY}
      - MCP_PORT=8080
      - ENV=dev
    depends_on: [api]


AC

 docker compose --profile mcp up brings up app+db+mcp; GET /tools?expert_id=1 returns tools.

Tests

Manual curl accepted; smoke test script in mcp-server/README.md.

T8.4 — Wiring: service account for MCP

Why: Secure app calls.

Files

Seed script: create Service(name="mcp", environment="dev") and capture plaintext key to console (dev only).

Infra/TF (later E10) will create real Service + SSM/Secrets for prod/stage.

AC

 MCP server uses X-API-Key header with the seed key in dev.

Tests

N/A (documented).

T8.5 — Observability

Files

mcp-server/app.py logs every outbound call with latency, status.

Add X-Request-ID passthrough to our app; generate if missing.

AC

 Logs show correlation IDs across MCP → App.

Tests

Unit check for header propagation.

E8 DoD

App endpoint publishes tool descriptors for expert.

MCP server lists tools and forwards calls to our app.

Dev compose works; image builds; basic tests pass.