What we’re building (one paragraph)

A multi-tenant platform where teams define Experts (chat personas with prompts, models, and input params) and compose Workflows (directed acyclic graphs of nodes) that call AI jobs, external resources, and data-manipulation steps. Users can experiment via Chat, ops can register Services (with API keys) to post chat events and resolve their end-users via Segments, and the system can execute workflows by API or on schedules (CRON).

Core pages (UI requirements drive backend)

Experts: list, expand, edit modal, link to chat; show counts of attached workflows/services.

Workflows: list, expand; editor subpage for DAG (nodes + edges), triggers (API/CRON), retry; validate DAG (no cycles, proper fan-in).

Chat: run an expert (with visible prompt + input params JSON), or run a workflow and watch step-by-step logs.

Services: register service per environment, generate API key, define segments (keys that disambiguate external users), view counts.

Teams/Dashboard: placeholders for now.

Data model (your canonical entities)

All tables include created_on and updated_on timestamps.

experts: id, uuid, prompt, name, model_name, status[draft|active|archive|historical], input_params(JSON), team_id(FK)

workflows: id, uuid, name, description, input_params(JSON), is_api(bool), cron_schedule(text|null), team_id(FK)

expert_workflow: id, expert_id(FK), workflow_id(FK)

nodes: id, workflow_id(FK), node_type(enum), metadata(JSON), structured_output(JSON)

node_node: id, parent_id(FK nodes.id), child_id(FK nodes.id) // edges

teams: id, name

members: id, first_name, last_name, email

team_members: id, team_id(FK), member_id(FK), role[admin|member]

services: id, name, environment[dev|stage|prod], api_key (stored hashed+last4)

service_segments: id, service_id(FK), name (named segment schemas; see below)

users: id, member_id(FK|null), password (hashed|null), service_user_id(FK|null) // internal auth OR bound to a service user

service_users: id, user_id(FK users.id), segment_key(JSON) // { "version": 1, "properties": { "user_id": "abc", "client_id": "123" } }

expert_services: id, expert_id(FK), service_id(FK)

workflow_services: id, workflow_id(FK), service_id(FK)

Note on segments: a service can define one or more service_segments (named schemas). A service_user holds a segment_key JSON (with version + key/value properties) used to uniquely identify end-users from that service. Enforce uniqueness via a canonical hash over (service_id, version, sorted properties).

Node types (must match UI palette)

AI: job, embed

Resources: guru, get_api, post_api, vector_query

Actions: filter, map, if_else, for_each, merge, split, advanced, return, workflow (call sub-workflow)

Node contract (execution layer, later epic)

All node services implement:

class NodeService(Protocol):
    def validate(self, metadata: dict, structured_output: dict) -> None: ...
    def plan(self, inputs: dict) -> dict: ...  # mock output shape
    def execute(self, inputs: dict, metadata: dict) -> dict: ...  # returns data matching structured_output


Node metadata is type-specific; structured_output is a JSON schema (or plain shape) used for validation and planning.

Templating & JSONata

Prompts and mapping fields support {{ base.* }} and {{ input.* }} with JSONata expressions inside braces.

Examples:

Hello {{ base.time }}

{{ input.customer.orders[*].id }}

API conventions

Base: /api/v1

Auth: services call with X-API-Key; admins/internal with JWT (future).

JSON field names: snake_case.

Errors: Problem+JSON (type, title, status, detail, instance, optional errors[]).

How we store API keys

API keys are generated with high entropy (40+ characters) and stored securely. Only the SHA256 hash and last 4 characters are persisted in the database. The plaintext key is shown to the user once at creation time and never stored or retrievable afterward. This ensures that even if the database is compromised, the actual API keys cannot be recovered.

Scheduling (CRON) architecture (summary)

DB is source of truth for workflows.cron_schedule.

Outbox pattern → tiny Lambda publisher → EventBridge Scheduler Create/Update/DeleteSchedule.

Target: HTTPS POST to our API (API Destination or public endpoint).

Worker idempotency key: workflow_id + scheduled_for.

Environments & deployment (summary)

Infra: Terraform for ECR (app + FastMCP), ECS Fargate (app), Fargate (FastMCP), RDS Postgres, VPC, NLB, Route53, S3 (FE), CloudFront, EventBridge, Lambda (publisher), CloudWatch.

CI/CD: GitHub Actions builds images, runs Alembic, deploys ECS, uploads FE to S3 + CF invalidation.

Epics (overview)

E0 — Dev Environment & Scaffolding
Repo bootstrap; Dockerfile; docker-compose (API + Postgres); Alembic; Makefile; logging; error handling; JSONata stub; CI.

E1 — Domain Models & Migrations
Define SQLModel models for all entities; enums; constraints; Alembic migrations; seed data; repository layer skeletons.

E2 — Security & Auth
Hash & manage API keys (Service); minimal internal User auth (password hash) + team role checks; dependency wires.

E3 — Experts APIs & Services
CRUD for Experts; join tables to Workflows/Services; DTOs for list and details; JSON validation for input_params.

E4 — Workflows & DAG APIs
CRUD for Workflows, Nodes, Edges; DAG validation (acyclic, fan-in rules); trigger validation; “plan” endpoint.

E5 — Node Service Implementations
Base interface + registry; one ticket per node type (validate/plan/execute stubs, schema checks).

E6 — Chat & Execution
Sessions/messages minimal model or in-memory; run expert with prompt rendering; run workflow step-through; streaming logs (server-sent events stub).

E7 — Services & Segments
CRUD for Service, ServiceSegment, ServiceUser; uniqueness via canonical segment hash; resolve helper endpoint.

E8 — FastMCP Integration
App endpoint to list workflows for an expert; Fargate FastMCP image that fetches and exposes tool annotations.

E9 — Cron Orchestration (Code + TF)
DB outbox, publisher Lambda, EventBridge Scheduler wiring, invocation endpoint, idempotency.

E10 — Terraform (Core Infra)
VPC, subnets, SGs; RDS; ECR; ECS services; NLB; Route53; S3/CloudFront; Secrets/SSM; CW logs/alarms.

E11 — Deployments (CI/CD)
GitHub Actions pipelines (build, scan, push, migrate, deploy, FE publish), env promotion, smoke checks.

E12 — Observability & Ops
Structured logging, request IDs, metrics counters, alarms, basic runbooks.