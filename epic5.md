Epic E5 — Node Services (interfaces, schemas, per-type implementations)

Goal: A pluggable node service layer that validates node metadata/outputs, returns mock shapes for planning, and (later) executes. For now, execute() can be a stub that returns empty or schema-shaped data.

Shared conventions for E5

Each node type has:

metadata schema (Pydantic models per type)

structured_output schema (dict / JSON Schema-lite)

Service implementing validate(), plan(), execute()

A central registry maps NodeType → service.

T5.1 — Base interfaces, errors, and registry

Files

app/services/nodes/base.py

class NodeValidationError(ValueError): ...
class NodeExecutionError(RuntimeError): ...

class NodeService(Protocol):
    def validate(self, metadata: dict, structured_output: dict) -> None: ...
    def plan(self, metadata: dict, inputs_shape: dict, structured_output: dict) -> dict: ...
    def execute(self, inputs: dict, metadata: dict) -> dict: ...

REGISTRY: dict[NodeType, NodeService] = {}

def get_service(node_type: NodeType) -> NodeService: ...


app/services/nodes/util.py

JSON Schema-lite validator (or use jsonschema lib) for structured_output.

Helper to coerce structured_output into a “shape” (keys only).

AC

 Importable; placeholder default service raises clear error.

Tests

tests/services/nodes/test_registry.py.

T5.2 — Metadata models & docs

Files

app/services/nodes/models.py (Pydantic models)

AI.Job: prompt:str, model_name:str, temperature:float|None, stop:list[str]|None

AI.Embed: vector_store_id:str, namespace:str|None, input_selector:str (JSONata)

Res.Guru: space:str, filters:dict|None

Res.GetAPI: url:HttpUrl, headers:dict[str,str]|None, query_map:dict|None (JSONata per field)

Res.PostAPI: url:HttpUrl, headers:dict[str,str]|None, body_map:dict|None (JSONata per field)

Res.VectorQuery: vector_store_id:str, query_template:str, top_k:int=5, filters:dict|None

Act.Filter: where:str (JSONata boolean)

Act.Map: mapping:dict (values are JSONata expressions)

Act.IfElse: predicate:str (JSONata)

Act.ForEach: items_selector:str (JSONata array path)

Act.Merge: strategy:str="union" (enum: union, concat, prefer_left)

Act.Split: by:str (JSONata returns array of groups or keys)

Act.Advanced: expression:str (JSONata returns any)

Act.Return: payload_selector:str (JSONata)

Act.Workflow: workflow_id:int

docs/nodes.md: one page spec per type incl. examples.

AC

 Pydantic models validate fields as expected.

 Docs exist with 1–2 examples per node.

Tests

tests/services/nodes/test_metadata_models.py.

T5.3 — Wire node validation into Nodes CRUD

Files

app/api/workflows.py (T4.4)

On create/update: get_service(node_type).validate(metadata, structured_output)

app/services/nodes/base_validators.py

Common checks: structured_output must be a dict; empty allowed.

AC

 422 on bad metadata with precise error messages.

Tests

Extended in tests/api/test_nodes_crud.py.

T5.4 — Implement AI.Job service

Files

app/services/nodes/ai_job.py

class JobService(NodeService): ...


Validate

prompt non-empty; model_name non-empty.

structured_output dict (keys describe expected shape).
Plan

Return structured_output as output shape (or { "text": "string" } if empty).
Execute (stub)

Return {} or echo shape keys with None.

AC

 Validator errors are actionable.

 Plan returns keys matching structure.

Tests

tests/services/nodes/test_ai_job.py.

T5.5 — Implement AI.Embed service

Files

app/services/nodes/ai_embed.py
Validate

vector_store_id present; input_selector present.
Plan

{ "embedded": True, "count": "number" }
Execute (stub)

{ "embedded": True, "count": 1 }

Tests: test_ai_embed.py.

T5.6 — Implement Resources: Guru, GetAPI, PostAPI, VectorQuery

Files

app/services/nodes/resources/guru.py, get_api.py, post_api.py, vector_query.py
Validate

Required fields; URL validation; for maps, ensure values are strings (JSONata exprs).
Plan

Return indicative shapes:

Guru: { "items": [] }

Get: { "status": "number", "body": {} }

Post: same as Get

VectorQuery: { "results": [{"id": "string", "score": "number", "payload": {}}] }
Execute (stub)

Return empty/placeholder.

Tests

Each module’s validator & plan unit tests.

T5.7 — Implement Actions: Filter, Map, IfElse, ForEach, Merge, Split, Advanced, Return, Workflow

Files

app/services/nodes/actions/*.py
Validate (high level)

Filter: where required.

Map: mapping non-empty dict.

IfElse: predicate required.

ForEach: items_selector required.

Merge: strategy in enum.

Split: by required.

Advanced: expression required.

Return: payload_selector required.

Workflow: workflow_id exists (check via repo).
Plan

Treat actions as pass-through with transformed shapes:

Filter: input → output unchanged shape.

Map: output shape = keys of mapping.

IfElse: output shape = union of potential branches (annotate notes).

ForEach: output shape = item shape (annotate notes for array).

Merge: union of parent shapes.

Split: output = array of groups.

Advanced: unknown; echo {"result": {}}.

Return: echo selected payload shape if derivable else {}.

Workflow: output shape = child workflow’s declared output (stub {}) with note.
Execute (stub)

Return {} or minimal.

Tests

Per action validator test; plan behavior for shape.

T5.8 — JSONata integration glue (evaluate safely)

Files

app/lib/jsonata.py (complete implementation)

Use chosen python JSONata lib; add timeout; catch and wrap errors.

Update services to call evaluate() in plan when safe (or skip; execution will use in E6).

AC

 Library errors surfaced with expression and path context.

Tests

tests/lib/test_jsonata_eval.py.

T5.9 — Registry registration

Files

app/services/nodes/__init__.py

Register all services in REGISTRY at import time.

Ensure app/api/workflows.py imports registry side-effect.

AC

 get_service(NodeType.job) returns JobService etc.

Tests

Extended registry test.

T5.10 — Docs: nodes & examples

Files

docs/nodes.md (expanded)

For each type: metadata example, structured_output example, sample “available data” JSONata snippet.

AC

 Docs render properly; links from docs/context.md.

E5 DoD

All node types validated with helpful messages.

Planning works end-to-end using node services.

Execution stubs present (to be wired in E6).

Tests green.