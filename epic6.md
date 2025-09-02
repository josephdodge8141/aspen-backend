Epic E6 — Chat & Execution

Goal: Power the Chat page: run an Expert (render prompt + stub LLM) or run a Workflow (step-through using node services). Provide structured, stream-like logs for the right-hand “log panel” without adding new DB tables (ephemeral in-memory runs). Enforce permissions: JWT for admins; X-API-Key for service invocations; service access must be allowed via expert_services / workflow_services.

Shared conventions (E6)

Base path: /api/v1/chat

No new DB tables. Use an in-memory run registry with TTL for logs.

If request comes from a Service (X-API-Key), only experts/workflows linked to that service may be executed.

If request comes from an Admin/JWT, user must be team member; updates require team admin (reuse E2 helpers).

T6.1 — In-memory run registry (ephemeral logs)

Why: Stream logs to UI without DB.

Files

app/services/runs/registry.py

import time, queue, threading, uuid
from dataclasses import dataclass, field
from typing import Any

@dataclass
class RunEvent:
    ts: float
    level: str  # "info" | "warn" | "error"
    message: str
    data: dict[str, Any] = field(default_factory=dict)

@dataclass
class RunState:
    run_id: str
    kind: str  # "expert" | "workflow"
    started_at: float
    finished_at: float | None = None
    events: list[RunEvent] = field(default_factory=list)
    q: "queue.Queue[RunEvent]" = field(default_factory=queue.Queue)

class RunRegistry:
    def __init__(self, ttl_seconds: int = 900): ...
    def create(self, kind: str) -> RunState: ...
    def get(self, run_id: str) -> RunState | None: ...
    def append(self, run_id: str, event: RunEvent) -> None: ...
    def finish(self, run_id: str) -> None: ...
    def pop_next(self, run_id: str, timeout: float = 20.0) -> RunEvent | None: ...
    def gc(self) -> None: ...  # background thread to delete finished/old runs
REGISTRY = RunRegistry()


Start a daemon GC thread in app/main.py.

AC

 create/get/append/finish/pop_next work; GC cleans after TTL.

 Thread-safe.

Tests

tests/services/runs/test_registry.py: create, append, concurrent producers/consumers, TTL cleanup (use small TTL in test).

T6.2 — Common logging facade for runs

Why: Consistent event shape from expert/workflow runs.

Files

app/services/runs/logger.py

from .registry import REGISTRY, RunEvent
def log_info(run_id: str, msg: str, **data): ...
def log_warn(run_id: str, msg: str, **data): ...
def log_error(run_id: str, msg: str, **data): ...
def finish(run_id: str): ...


AC

 Writes to both list buffer and queue.

 Errors include exception field when passed.

Tests

Extend test_registry.py.

T6.3 — SSE endpoint for run events

Why: Feed the right-hand “auto-scroll log panel”.

Files

app/api/chat.py

router = APIRouter(prefix="/api/v1/chat", tags=["Chat"])
@router.get("/runs/{run_id}/events", response_class=EventSourceResponse)
async def stream_run_events(run_id: str): ...


Use sse-starlette (or lightweight manual text/event-stream) to stream events from REGISTRY.pop_next() until finished. Send initial backlog first, then new ones. Heartbeat every ~20s.

AC

 Client receives event: log lines with JSON payload: {ts, level, message, data}.

 On finish, send event: done.

Tests

tests/api/test_chat_sse.py (mark as integration; simulate two events + finish).

T6.4 — Render prompt (base + input) utility

Why: Expert “pre-render” for Chat.

Files

app/services/prompt_render.py

import re
from app.lib.jsonata import evaluate

def render_prompt(template: str, base: dict, input_data: dict) -> str:
    # Replace {{ ... }} with values from base/* or input/* via JSONata


Rules:

{{ base.foo }} → lookup in base

{{ input.some[*].id }} → evaluate with input_data as root

Unknown → leave placeholder and record a warning (returned by API, not thrown)

AC

 Handles multiple placeholders; preserves text elsewhere.

Tests

tests/services/test_prompt_render.py.

T6.5 — Run Expert endpoint (stubbed assistant)

Why: Power Expert mode in Chat.

Files

app/api/chat.py

class RunExpertBody(BaseModel):
    expert_id: int
    input_params: dict = {}
    base: dict = {}  # optional overrides for base values

@router.post("/experts:run")
def run_expert(body: RunExpertBody, caller: CallerContext = Depends(get_caller)):
    # Permissions:
    # - If caller.service: expert must be linked via expert_services
    # - If caller.user: require_team_member(expert.team_id)
    # Flow:
    # - Fetch expert
    # - Render prompt via render_prompt(template, base_defaults, body.input_params)
    # - Emit run_id and first events (prompt rendered, model_name, input size)
    # - Return single reply stub: {"run_id": str, "messages": [{"role":"user","content":...}, {"role":"assistant","content":"(stubbed)"}]}


Base defaults: current ISO timestamp, timezone name; maybe preferred words placeholder.

AC

 Returns 200 with run_id and messages.

 Writes at least two log events (prompt_rendered, assistant_stub_sent).

 Permissions enforced (403/404 as appropriate).

Tests

tests/api/test_chat_run_expert.py: team user ok; service allowed only if linked; forbidden otherwise.

T6.6 — Run Workflow endpoint (step-through with logs)

Why: Power Workflow mode in Chat.

Files

app/api/chat.py

class RunWorkflowBody(BaseModel):
    workflow_id: int
    starting_inputs: dict = {}

@router.post("/workflows:run")
def run_workflow(body: RunWorkflowBody, caller: CallerContext = Depends(get_caller)):
    # Permissions:
    # - If caller.service: workflow must be linked via workflow_services
    # - If caller.user: require_team_member(workflow.team_id)
    # Flow:
    # - Create run_id
    # - Load nodes+edges; validate DAG (reuse E4)
    # - Topo order; per node:
    #     log_info(..., "node_start", node_id=..., node_type=...)
    #     derive inputs from available-data map
    #     get_service(node.node_type).execute(inputs, node.metadata)  # stub returns minimal dict
    #     log_info(..., "node_output", node_id=..., output=...)
    # - Finish and return {"run_id": str, "steps": [{"node_id":..., "output": {...}}, ...]}


Important: do not resolve JSONata here yet (actions that require expressions will be exercised later when JSONata integration is complete); stubs can no-op or echo shapes.

AC

 Returns steps in topo order with outputs (even if empty).

 Logs per node start/end; overall summary log at finish.

 Permissions enforced.

Tests

tests/api/test_chat_run_workflow.py: happy path + permission failure.

T6.7 — Available-data resolution for node execution

Why: Provide each node the merged predecessors’ outputs (transitively).

Files

Reuse app/services/dag_available.py from E4; add:

def resolve_inputs_for_node(node_id: int, outputs_by_node: dict[int, dict]) -> dict: ...


Execution uses resolve_inputs_for_node() before calling the node service.

AC

 For diamonds, D receives union of A,B,C outputs.

Tests

Extend T4 tests or add tests/services/test_available_for_execution.py.

T6.8 — Guardrails for service invocations

Why: Enforce expert_services / workflow_services.

Files

app/security/guardrails.py

def ensure_service_can_use_expert(session, service_id: int, expert_id: int) -> None: ...
def ensure_service_can_use_workflow(session, service_id: int, workflow_id: int) -> None: ...


Use in run_expert and run_workflow.

AC

 403 if not linked; 404 if resource not found.

Tests

In existing API tests.

T6.9 — Postman collection & docs

Files

docs/postman/chat.postman_collection.json covering:

POST /chat/experts:run

POST /chat/workflows:run

GET /chat/runs/{id}/events (SSE)

docs/chat.md short “how to test locally”.

AC

 Manual test yields live logs in SSE.

E6 Definition of Done

Expert/Workflow run endpoints operational with permission checks.

SSE event stream feeds the log panel.

No DB persistence required; ephemeral runs cleaned up by TTL.

Tests passing in CI.