Cross-node conventions
Reserved metadata envelope (optional, same for all nodes)
type MetaCommon = {
  name?: string;                 // display label for the node card
  description?: string;          // human note
  timeout_ms?: number;           // soft exec limit (node-specific services may respect it later)
  retry?: number;                // local override; if unset, workflow-level retry applies
  on_error?: "fail" | "skip" | "continue"; // execution policy (used later, stored now)
  tags?: string[];
};


Store MetaCommon fields alongside node-specific keys (flat object).

All fields not explicitly listed below are forbidden (validator surfaces “unknown key” errors).

JSONata-capable fields are marked with 🧪 JSONata below. They accept expressions like input.orders[*].id, and templating in strings like Hello {{ base.time }} where relevant.

JSON editors & validation (frontend)

Use a monospace code editor for JSON/JSONata fields with:

live lint, brace matching, and “Test expression” button that evaluates against Available Data.

error surfacing with the exact path (e.g., mapping.total: JSONata error: ...).

“Available Data” drawer shows merged predecessor shapes and example values.

AI
1) Job

Purpose: LLM call whose response must match a structured output.

Metadata schema (DB)
type MetaJob = MetaCommon & {
  prompt: string;                // may include {{ base.* }} and 🧪 JSONata on {{ input.* }}
  model_name: string;            // e.g., "gpt-4o-mini", "claude-3-haiku"
  temperature?: number;          // 0..2
  max_tokens?: number;           // >0
  stop?: string[];               // optional stop sequences
  system?: string;               // optional system prompt
};


Example (stored):

{
  "name": "Summarize order",
  "prompt": "Summarize {{ input.customer.name }}'s last order at {{ base.time }}.",
  "model_name": "gpt-4o-mini",
  "temperature": 0.2,
  "max_tokens": 512
}

Frontend form

Section: Model

Model (select)

Temperature (slider 0–2, step 0.1)

Max tokens (number)

Stop sequences (chips input)

Section: Prompts

System (textarea, optional)

Prompt (textarea, required) with templating helper; Preview button shows rendered text with sample data.

Section: Advanced

Timeout (ms), Retry (#), On error (radio)

Structured Output editor (separate panel): JSON shape/schema editor with “Validate” button.

2) Embed

Purpose: Create vector embeddings for selected text and upsert to a store.

Metadata schema (DB)
type MetaEmbed = MetaCommon & {
  vector_store_id: string;       // your store handle
  namespace?: string;            // optional logical bucket
  model_name?: string;           // embedding model id (optional now)
  input_selector: string;        // 🧪 JSONata → string | string[] (text(s) to embed)
  id_selector?: string;          // 🧪 JSONata → string per item (doc id)
  metadata_map?: Record<string, string>; // values are 🧪 JSONata expressions
  upsert?: boolean;              // default true
};


Example:

{
  "vector_store_id": "vs_customers",
  "namespace": "orders",
  "input_selector": "input.order.items[*].description",
  "id_selector": "input.order.id",
  "metadata_map": { "customer": "input.customer.id", "total": "input.order.total" },
  "upsert": true
}

Frontend form

Section: Store

Vector store (select), Namespace (text), Embedding model (select, optional)

Section: Inputs

Input selector (🧪 JSONata editor, required)

Document ID selector (🧪 JSONata, optional)

Metadata map (key/value table; values are 🧪 JSONata)

Section: Behavior

Upsert (switch), Timeout/Retry/On error

Resources
3) Guru

Purpose: Query Guru knowledge (space/collection) with optional filters.

Metadata schema (DB)
type MetaGuru = MetaCommon & {
  space: string;                 // Guru space/collection id or slug
  query_template: string;        // may include {{ base.* }} and 🧪 JSONata on {{ input.* }}
  top_k?: number;                // default 5
  filters?: Record<string, string | number | boolean>;
};


Example:

{
  "space": "support-faqs",
  "query_template": "FAQ for {{ input.topic }}",
  "top_k": 5,
  "filters": { "language": "en" }
}

Frontend form

Section: Source

Space (select/search)

Section: Query

Query template (textarea with templating)

Top K (number), Filters (key/value table)

Section: Advanced

Timeout/Retry/On error

4) GET API

Purpose: HTTP GET with mapped query params/headers from data.

Metadata schema (DB)
type MetaGetAPI = MetaCommon & {
  url: string;                   // http(s)://...
  headers?: Record<string, string>;     // literal values or {{ }} templated
  query_map?: Record<string, string>;   // values are 🧪 JSONata → string/number/bool
  auth_preset?: string;          // optional named credential (future)
  timeout_ms?: number;
};


Example:

{
  "url": "https://api.example.com/search",
  "headers": { "X-Client": "workflow-engine" },
  "query_map": { "q": "input.query", "limit": "5" }
}

Frontend form

Section: Request

URL (text, required)

Headers (key/value)

Query map (key → 🧪 JSONata)

Section: Advanced

Auth preset (select), Timeout/Retry/On error

5) POST API

Purpose: HTTP POST with JSON body generated by mapping.

Metadata schema (DB)
type MetaPostAPI = MetaCommon & {
  url: string;
  headers?: Record<string, string>;
  body_map?: Record<string, any>;       // object where leaves are 🧪 JSONata or literals
  content_type?: "application/json" | "application/x-www-form-urlencoded";
  auth_preset?: string;
  timeout_ms?: number;
};


Example:

{
  "url": "https://api.example.com/orders",
  "headers": { "Authorization": "Bearer {{ base.service_token }}" },
  "content_type": "application/json",
  "body_map": {
    "user_id": "input.user.id",
    "items": "input.cart.items[*]",
    "total": "input.cart.items.sum($.price)"
  }
}

Frontend form

Section: Request

URL (text), Headers (key/value), Content-Type (segmented)

Section: Body

Body map (JSON editor where leaf values can be 🧪 JSONata)

“Render sample body” button (evaluates with Available Data)

Section: Advanced

Auth preset, Timeout/Retry/On error

6) Query Vector Store

Purpose: Retrieve nearest vectors.

Metadata schema (DB)
type MetaVectorQuery = MetaCommon & {
  vector_store_id: string;
  namespace?: string;
  query_template: string;        // string with templating or 🧪 JSONata → string
  top_k?: number;                // default 5
  filters?: Record<string, string | number | boolean>;
};


Example:

{
  "vector_store_id": "vs_customers",
  "namespace": "orders",
  "query_template": "input.question",
  "top_k": 3
}

Frontend form

Section: Store

Vector store (select), Namespace (text)

Section: Query

Query template (🧪/templated text), Top K (number), Filters (key/value)

Advanced: Timeout/Retry/On error

Actions
7) Filter

Purpose: Filter arrays by a boolean predicate.

Metadata schema (DB)
type MetaFilter = MetaCommon & {
  items_selector?: string;       // 🧪 JSONata → array; default is root input if array
  where: string;                 // 🧪 JSONata → boolean; evaluated per item (item in $)
};


Example:

{
  "items_selector": "input.items",
  "where": "$.price > 20"
}

Frontend form

Section: Source

Items selector (🧪, optional; autodetect if root is array)

Section: Predicate

Where (🧪 boolean, required), inline “Test” → shows count kept/dropped on sample.

8) Map

Purpose: Create a new object from prior data.

Metadata schema (DB)
type MetaMap = MetaCommon & {
  mapping: Record<string, string | number | boolean>; // values are 🧪 JSONata expressions or literals
};


Example:

{
  "mapping": {
    "customer_id": "input.customer.id",
    "name": "input.customer.name",
    "total": "input.items.sum($.price)"
  }
}

Frontend form

Section: Mapping

Table: Key (text) → Value (🧪 editor)

“Preview result” renders object with sample data

Validation: at least one key; keys unique; values non-empty

9) If/Else

Purpose: Branch execution flow.

Metadata schema (DB)
type MetaIfElse = MetaCommon & {
  predicate: string;             // 🧪 JSONata → boolean
};


Example:

{ "predicate": "input.total > 100" }

Frontend form

Single field Predicate (🧪).

Edge rule: Outgoing edges must be labeled "true" and "false"; UI hints this in node tips.

10) For Each

Purpose: Iterate over array items.

Metadata schema (DB)
type MetaForEach = MetaCommon & {
  items_selector: string;        // 🧪 JSONata → array (required)
  concurrency?: number;          // optional future use; store now
  flatten?: boolean;             // default true (merge results into one array)
};


Example:

{
  "items_selector": "input.orders[*]",
  "flatten": true
}

Frontend form

Section: Items

Items selector (🧪, required), Test button shows length and first 3 items

Section: Behavior

Flatten (switch), Concurrency (number, disabled if not supported yet)

11) Merge

Purpose: Combine multiple parent outputs.

Metadata schema (DB)
type MetaMerge = MetaCommon & {
  strategy?: "union" | "concat" | "prefer_left";  // default "union"
  expected_parents?: number;                       // optional hint, not enforced
};


Example:

{ "strategy": "union" }

Frontend form

Strategy (select with help text):

union: shallow merge objects (later keys overwrite)

concat: arrays concatenated; objects union

prefer_left: take first non-null per key/parent order

Validation: warn if indegree < 2 (not useful)

12) Split

Purpose: Partition a collection into groups or chunks.

Metadata schema (DB)
type MetaSplit = MetaCommon & {
  by: string;                    // 🧪 JSONata → array of groups OR a key selector (string)
  mode?: "group_by" | "chunk";   // default "group_by"
  chunk_size?: number;           // required if mode="chunk"
};


Example:

{ "by": "input.items[*].category", "mode": "group_by" }

Frontend form

Mode (segmented: Group by / Chunk)

If Group by:

By (🧪 returns group keys or grouping expression)

If Chunk:

Chunk size (number > 0)

Preview sample partitions count.

13) Advanced Data Manipulation

Purpose: Arbitrary transform with JSONata.

Metadata schema (DB)
type MetaAdvanced = MetaCommon & {
  expression: string;            // 🧪 JSONata, returns any
};


Example:

{ "expression": "{ ids: input.items[*].id, total: input.items.sum($.price) }" }

Frontend form

Single Expression (JSONata editor) + Run preview.

Strong warnings: this can reshape data arbitrarily.

14) Return

Purpose: Define the workflow’s outward response.

Metadata schema (DB)
type MetaReturn = MetaCommon & {
  payload_selector: string;      // 🧪 JSONata → any (what to return)
  content_type?: "application/json" | "text/plain"; // default json
  status_code?: number;          // default 200 (advisory)
};


Example:

{
  "payload_selector": "{ answer: input.answer, steps: input.steps }",
  "content_type": "application/json"
}

Frontend form

Payload selector (🧪), content type (select), status code (number)

Validation: no outgoing edges allowed after Return; show inline warning if edges exist.

DAG rule reminder: Return cannot be under For Each (validator will catch).

15) Workflow (sub-workflow)

Purpose: Invoke another workflow as a step.

Metadata schema (DB)
type MetaWorkflowCall = MetaCommon & {
  workflow_id: number;           // child workflow id
  input_mapping?: Record<string, string>; // key → 🧪 JSONata to build child's starting_inputs
  propagate_identity?: boolean;  // default true (for service/user identity contexts)
  wait?: "sync";                 // future-proof (only 'sync' for now)
};


Example:

{
  "workflow_id": 42,
  "input_mapping": {
    "question": "input.user_question",
    "context": "{ items: input.items }"
  },
  "propagate_identity": true
}

Frontend form

Section: Target

Workflow (searchable select)

Section: Inputs

Input mapping builder (key → 🧪 JSONata)

Preview “Child starting_inputs” with sample data

Section: Behavior

Propagate identity (switch)

Wait (displayed as “Synchronous” and disabled for now)

Structured Output editor (shared UI)

Although your question focuses on metadata, nearly all nodes pair with a Structured Output. For each node’s modal:

Right pane: Structured Output JSON editor with:

“Use example” button to insert a sensible default shape for that node type.

“Validate against recent sample” (uses the node’s Plan result).

Store this separately in node.structured_output (as you already planned).

Validation summary (backend mirror)

Presence/format checks per schema above (types, ranges, URL formats).

JSONata test hooks: backend validate() should attempt to parse expressions but not execute them (syntax check). Execution preview/testing remains optional and safe.

Action-specific DAG rules (already in your validator): if_else requires edges labeled true/false, return outdegree==0, non-merge nodes indegree≤1.

Quick reference: union types (for docs or codegen)
type NodeMetadata =
  | ({ kind: "job" }            & MetaJob)
  | ({ kind: "embed" }          & MetaEmbed)
  | ({ kind: "guru" }           & MetaGuru)
  | ({ kind: "get_api" }        & MetaGetAPI)
  | ({ kind: "post_api" }       & MetaPostAPI)
  | ({ kind: "vector_query" }   & MetaVectorQuery)
  | ({ kind: "filter" }         & MetaFilter)
  | ({ kind: "map" }            & MetaMap)
  | ({ kind: "if_else" }        & MetaIfElse)
  | ({ kind: "for_each" }       & MetaForEach)
  | ({ kind: "merge" }          & MetaMerge)
  | ({ kind: "split" }          & MetaSplit)
  | ({ kind: "advanced" }       & MetaAdvanced)
  | ({ kind: "return" }         & MetaReturn)
  | ({ kind: "workflow" }       & MetaWorkflowCall);


If you want, I can convert these to JSON Schema files you can validate server-side (and use to auto-render forms on the frontend). Or I can draft the exact React form components (shadcn/ui + code editor) with field-level validators and “Available Data” integration.