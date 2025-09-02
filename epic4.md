Epic E4 — Workflows & DAG (CRUD, validation, planning)

Goal: Everything needed to power the Workflows list + editor UI: CRUD for workflows, nodes, and edges; DAG validation (no cycles, rules), trigger validation (API/CRON), and a “plan” endpoint that returns topological order + mock output shapes and “available data”.

Shared conventions for E4

Paths use /api/v1/workflows/*.

Permissions: all write paths require JWT + team admin of the workflow’s team_id.

Problem+JSON errors; 404s for missing resources, 409 for graph conflicts.

T4.1 — Pydantic schemas for workflows, nodes, edges

Files

app/schemas/workflows.py

class WorkflowBase(SQLModel):
    name: str
    description: str | None = None
    input_params: dict = Field(default_factory=dict)
    is_api: bool = False
    cron_schedule: str | None = None   # validated separately
    team_id: int

class WorkflowCreate(WorkflowBase): ...
class WorkflowUpdate(SQLModel):
    name: str | None = None
    description: str | None = None
    input_params: dict | None = None
    is_api: bool | None = None
    cron_schedule: str | None = None

class WorkflowListItem(SQLModel):
    id: int
    uuid: str
    name: str
    description_truncated: str | None
    experts: list[dict]      # [{"id": int, "name": str}] (first 5)
    experts_count: int
    services_count: int

class WorkflowRead(SQLModel):
    id: int
    uuid: str
    name: str
    description: str | None
    input_params: dict
    is_api: bool
    cron_schedule: str | None
    team_id: int

class NodeCreate(SQLModel):
    node_type: NodeType
    metadata: dict = Field(default_factory=dict)
    structured_output: dict = Field(default_factory=dict)

class NodeUpdate(SQLModel):
    node_type: NodeType | None = None
    metadata: dict | None = None
    structured_output: dict | None = None

class NodeRead(SQLModel):
    id: int
    node_type: NodeType
    metadata: dict
    structured_output: dict

class EdgeCreate(SQLModel):
    parent_id: int
    child_id: int
    branch_label: str | None = None

class EdgeRead(SQLModel):
    id: int
    parent_id: int
    child_id: int
    branch_label: str | None


AC

 Importable with mypy clean.

T4.2 — Repo methods (list/detail with joins)

Files

app/repos/workflows_repo.py

def list_with_counts(session: Session, *, team_id: int | None=None) -> list[WorkflowListItem]: ...
def get_expanded(session: Session, workflow_id: int) -> dict:
    # {"workflow": WorkflowRead, "nodes": [NodeRead...], "edges": [EdgeRead...],
    #  "experts": [{"id","name"}], "services": [{"id","name","environment"}]}


Details

Efficient aggregation for experts_count, services_count.

Return first 5 expert names for list (for chips).

Truncate description to 120 chars with ellipsis for list item.

AC

 Single SELECT (or two) approach—no N+1.

 Filters by team_id when provided.

Tests

tests/repos/test_workflows_repo.py: counts, truncation, ordering stable.

T4.3 — Workflows router (CRUD + archive)

Files

app/api/workflows.py

router = APIRouter(prefix="/api/v1/workflows", tags=["Workflows"])
@router.get("") -> list[WorkflowListItem]
@router.post("") -> WorkflowRead
@router.get("/{workflow_id}") -> dict        # expanded
@router.patch("/{workflow_id}") -> WorkflowRead
@router.post("/{workflow_id}:archive") -> WorkflowRead


Behavior

archive sets a soft status later (for now, keep record; UI will hide by convention).

Validate cron_schedule with croniter if not None (see T4.6).

Permissions

Create: team admin of team_id.

Patch/archive: team admin of workflow.team_id.

AC

 201 on create; 200 on reads; 400 on invalid cron.

 403 on insufficient role.

Tests

tests/api/test_workflows_crud.py.

T4.4 — Nodes CRUD

Files

Add to app/api/workflows.py:

@router.post("/{workflow_id}/nodes") -> NodeRead
@router.patch("/{workflow_id}/nodes/{node_id}") -> NodeRead
@router.delete("/{workflow_id}/nodes/{node_id}") -> Response 204


Behavior

On create/update, call node service validate() (stubbed in E5) to validate metadata and structured_output.

Deleting a node also deletes incident edges (FK cascade or explicit).

AC

 Invalid node metadata/schema → 422 with error details from validator.

 Delete removes edges touching the node.

Tests

tests/api/test_nodes_crud.py.

T4.5 — Edges CRUD

Files

Add to app/api/workflows.py:

@router.post("/{workflow_id}/edges") -> EdgeRead
@router.delete("/{workflow_id}/edges/{edge_id}") -> 204


Behavior

On create: verify both nodes belong to workflow.

Reject self-edge and duplicate edge (DB unique).

AC

 400 on self-edge; 409 on duplicate.

Tests

tests/api/test_edges_crud.py.

T4.6 — DAG validation service (cycles, fan-in rules, triggers)

Files

app/services/dag_validate.py

class DagValidationResult(BaseModel):
    errors: list[str]
    warnings: list[str]
    topo_order: list[int]  # node ids if valid

def validate_dag(nodes: list[Node], edges: list[NodeNode]) -> DagValidationResult: ...


Rules

Acyclic (Kahn or DFS). If cycle, list a cycle path (ids).

Multi-parent rule: Only nodes of type merge may have indegree > 1. Others → error.

Return rule: return nodes must have indegree ≥ 1 and outdegree == 0. If nested under a for_each path (any ancestor is for_each) → error. (Precompute ancestors by reversing edges; if any ancestor node_type == for_each.)

Isolated nodes allowed (act as additional entry points).

Branch labels: if parent is if_else, its outgoing edges must have branch_label in {"true","false"}; any other parent must have branch_label is None → else error.

Triggers (cron_schedule): if set, must be valid Cron (use croniter); if not set and is_api is False → warning (“No trigger configured”).

Router

@router.post("/{workflow_id}:validate")
# returns {"errors": [...], "warnings": [...], "topo_order": [node_ids]}


AC

 Cycles caught with clear path.

 Non-merge multi-parent rejected.

 Return rules enforced.

 Cron validated.

Tests

tests/services/test_dag_validate.py (happy + failing graphs).

T4.7 — “Plan” endpoint (topo + mock shapes + available data)

Files

app/services/dag_plan.py

class PlannedNode(BaseModel):
    node_id: int
    node_type: NodeType
    input_shape: dict
    output_shape: dict
    notes: list[str] = []

def plan_workflow(nodes, edges, *, starting_inputs: dict) -> list[PlannedNode]: ...


Compute topological order; propagate shapes:

input_shape for node = merged dict union of all parent output_shapes (for merge, union; for others, union with collision note).

output_shape = from node’s structured_output or the node service’s plan() (E5).

Collect notes on collisions or missing fields.

Router

@router.post("/{workflow_id}:plan")
# body: {"starting_inputs": dict}  -> {"steps": [PlannedNode...]}


AC

 Returns steps in topo order with shapes (no execution).

 Works for isolated nodes (treated as entry points).

Tests

tests/services/test_dag_plan.py.

T4.8 — “Available Data” helper endpoint (for node config UI)

Files

app/services/dag_available.py

def available_data_map(nodes, edges) -> dict[int, dict]:
    # For each node_id: merged outputs of all *predecessors* transitively


Router

@router.get("/{workflow_id}/available-data")
# -> {"by_node_id": { "<id>": { ...shape... } } }


AC

 For a diamond shape A→B, A→C, B→D, C→D, available for D includes A,B,C outputs.

Tests

tests/services/test_dag_available.py.

T4.9 — Seed + Postman (workflows)

Files

Extend scripts/seed_dev.py: one workflow with 3 nodes and 2 edges.

docs/postman/workflows.postman_collection.json.

AC

 Import, CRUD, validate, plan all work locally.

T4.10 — Cron parsing utility

Files

app/lib/cron.py

def is_valid_cron(expr: str) -> bool: ...  # croniter


AC

 Unit tests with valid/invalid expressions.

E4 DoD

Full CRUD for workflows/nodes/edges with validations.

Validate & Plan endpoints operational with tests.

Repo/DTOs power list/editor UI needs.