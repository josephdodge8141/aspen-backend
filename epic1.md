Epic E1 — Domain Models & Migrations (detailed tickets)

Goal: define all SQLModel models matching the schema you provided, enums, indexes, constraints; generate migrations; seed minimal lookup data. No business endpoints yet—just data layer.

Conventions (apply in all tickets)

SQLModel classes in app/models/*.py

Use table=True, explicit __tablename__

Primary keys: id: Optional[int] = Field(default=None, primary_key=True)

Add uuid where specified (UUID4, default generated in app, DB column type uuid)

Mix in TimestampMixin for timestamps

Enums: Python Enum + DB CHECK constraints or native ENUM (Postgres)

Index/Unique names: idx_<table>_<cols>, uq_<table>_<cols>

T1.1 — Enums & mixins

Why: Shared types and timestamps.
Deliverables:

app/models/common.py

from enum import Enum
class ExpertStatus(str, Enum): draft="draft"; active="active"; archive="archive"; historical="historical"
class TeamRole(str, Enum): admin="admin"; member="member"
class Environment(str, Enum): dev="dev"; stage="stage"; prod="prod"
class NodeType(str, Enum):
    job="job"; embed="embed"; guru="guru"; get_api="get_api"; post_api="post_api"; vector_query="vector_query"
    filter="filter"; map="map"; if_else="if_else"; for_each="for_each"; merge="merge"; split="split"
    advanced="advanced"; return_="return"; workflow="workflow"
class TimestampMixin(SQLModel):
    created_on: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    updated_on: datetime = Field(default_factory=datetime.utcnow, nullable=False)


Add SQLAlchemy event to auto-touch updated_on on update.
AC:

Importable enums; mixin usable by all models
Tests:

Simple instantiation and enum round-trip test

T1.2 — Team, Member, TeamMember models + migration

Why: Ownership/permissions base.
Deliverables:

app/models/team.py:

Team(id, name)

Member(id, first_name, last_name, email UNIQUE)

TeamMember(id, team_id FK->teams.id, member_id FK->members.id, role)

Indexes:

uq_team_members_team_member on (team_id, member_id)

Alembic migration creating the three tables with FKs and unique.
AC:

Autogenerate shows correct DDL; upgrade works
Tests:

Insert Member, Team, TeamMember; assert unique constraint violation on duplicate assignment

T1.3 — Experts & ExpertService/ExpertWorkflow models + migration

Why: Experts core.
Deliverables:

app/models/experts.py:

Expert(id, uuid, prompt TEXT, name, model_name, status, input_params JSONB, team_id FK->teams.id)

ExpertService(id, expert_id FK->experts.id, service_id FK->services.id)

ExpertWorkflow(id, expert_id FK->experts.id, workflow_id FK->workflows.id)

Unique:

uq_expert_service on (expert_id, service_id)

uq_expert_workflow on (expert_id, workflow_id)

Indexes: (team_id), (status)

Migration: create tables (note: references to services/workflows will be deferred until those exist—split migration or use op.create_table ordering carefully).
AC:

Migrations apply cleanly with FK ordering handled
Tests:

Insert Expert with JSON input_params and different statuses; assert enum validation

T1.4 — Services & ServiceSegment models + API key storage

Why: Tenancy and auth for external callers.
Deliverables:

app/models/services.py:

Service(id, name, environment, api_key_hash, api_key_last4) // store hash only, not plaintext

ServiceSegment(id, service_id FK->services.id, name)

Unique:

uq_service_name_env on (name, environment)

uq_service_segment_name on (service_id, name)

Migration creates both with constraints.
AC:

Unique name+env enforced; segments unique per service
Tests:

Create two services with same name but different env → allowed; same env → rejected

T1.5 — Users & ServiceUsers models

Why: Internal users vs bound external identities.
Deliverables:

app/models/users.py:

User(id, member_id FK nullable, password_hash nullable, service_user_id FK nullable)

ServiceUser(id, user_id FK->users.id, segment_key JSONB NOT NULL, segment_hash BYTEA UNIQUE, service_id FK->services.id, version INT NOT NULL)

segment_hash computed later in E7; for now column present + unique index

Constraints:

Check: either password_hash or service_user_id present (not both null); (soft for now: document to enforce in service layer)

Migration creates both.
AC:

Insert internal user (with password) and external user (with service_user link) succeeds
Tests:

Verify FK integrity; JSONB stored

T1.6 — Workflows, Nodes, NodeNode models + DAG constraints

Why: Core workflow storage.
Deliverables:

app/models/workflows.py:

Workflow(id, uuid, name, description, input_params JSONB, is_api BOOL, cron_schedule TEXT nullable, team_id FK->teams.id)

Node(id, workflow_id FK, node_type, metadata JSONB, structured_output JSONB)

NodeNode(id, parent_id FK->nodes.id, child_id FK->nodes.id)

Constraints:

Unique index on (workflow_id, id) is implicit by PK; add:

uq_node_edge_pair on (parent_id, child_id)

Check: parent_id <> child_id

Migration creates all three.
AC:

Migrations apply; basic inserts work
Tests:

Creating duplicate edge fails; self-edge fails

T1.7 — WorkflowService join model + migration

Why: Visibility mapping for services.
Deliverables:

app/models/workflow_services.py:

WorkflowService(id, workflow_id FK, service_id FK)

uq_workflow_service on (workflow_id, service_id)

Migration creates table.
AC:

Unique enforced; FK integrity
Tests:

Double insert rejected

T1.8 — Repository layer skeletons

Why: Consistent DB access for future endpoints.
Deliverables:

app/repos/__init__.py

app/repos/experts_repo.py, workflows_repo.py, services_repo.py, users_repo.py, teams_repo.py

Each exposes CRUD skeleton with signatures, using SQLModel sessions

Example:

class ExpertsRepo:
    def create(self, session: Session, expert: Expert) -> Expert: ...
    def get(self, session: Session, expert_id: int) -> Optional[Expert]: ...
    def list(self, session: Session, *, team_id: Optional[int]=None) -> list[Expert]: ...


AC:

Imports resolve; mypy/ruff clean
Tests:

Minimal round-trip tests inserting and reading one entity per repo

T1.9 — Base seed & fixtures

Why: Make local testing instant.
Deliverables:

scripts/seed_dev.py: creates one team, two members, a service per env, one expert, one workflow

tests/conftest.py: db_session fixture (transactional), client fixture (TestClient)
AC:

python scripts/seed_dev.py runs inside compose
Tests:

N/A (script smoke test acceptable)

T1.10 — Migrations integrity & docs

Why: Confidence & onboarding.
Deliverables:

docs/migrations.md: how to create, review, and run migrations; naming scheme (YYYYMMDDHHMM_<short>.py)

CI step to alembic upgrade head against ephemeral Postgres service
AC:

CI passes with migrations applied
Tests:

Already covered by pipeline

Definition of Done for E1

All models defined with enums, constraints, FKs, indexes

Alembic migrations apply cleanly from empty DB

Minimal seed script works

Repos compile and basic tests pass