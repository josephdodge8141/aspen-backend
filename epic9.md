Epic E9 — Cron Orchestration (Code + Terraform)

Goal: Keep Workflows.cron_schedule as the source of truth. Emit outbox rows on changes. A publisher Lambda reads outbox and manages EventBridge Scheduler schedules (create/update/delete). A runner Lambda is the target of schedules and calls our app to execute workflows. Provide an invoke endpoint in our app with idempotency.

Shared conventions

Scheduler target = Runner Lambda (not direct HTTP).

Schedule name: wf-{workflow_id}-{ENV} (stable).

Default timezone: UTC (future: extend table if you add tz column).

Idempotency key = workflow_id + scheduled_time_iso.

T9.1 — App DB: Outbox table + model

Why: Durable change feed for cron.

Files

app/models/outbox.py

class OutboxEvent(SQLModel, table=True):
    __tablename__ = "outbox_events"
    id: Optional[int] = Field(default=None, primary_key=True)
    aggregate_type: str  # "workflow"
    aggregate_id: int    # workflow_id
    op: str              # "upsert" | "delete"
    payload: dict = Field(sa_column=Column(JSON, nullable=False, server_default="{}"))
    created_on: datetime = Field(default_factory=datetime.utcnow, nullable=False)
    processed_on: datetime | None = None
    attempt_count: int = 0
    error_message: str | None = None


Alembic migration creating table + indexes:

idx_outbox_unprocessed on (processed_on) WHERE processed_on IS NULL

idx_outbox_created_on on (created_on)

AC

 Migration applies; insert works.

Tests

tests/models/test_outbox.py basic CRUD.

T9.2 — Emit outbox events on workflow changes

Why: Detect cron updates.

Files

app/services/workflows_events.py

def emit_workflow_upsert(session: Session, wf: Workflow) -> None: ...
def emit_workflow_delete(session: Session, workflow_id: int) -> None: ...


payload should include: cron_schedule, is_api, team_id.

Hook into POST /api/v1/workflows and PATCH:

After commit, emit upsert if cron_schedule is not None OR if a previously set cron becomes None (still upsert; the publisher decides delete vs create).

Hook into archive and delete (if you expose delete later).

AC

 Creating/updating/removing a cron_schedule yields an outbox row.

 Multiple rapid updates coalesce naturally (publisher processes in order).

Tests

tests/services/test_workflow_outbox.py: create, update schedule, clear schedule → three rows.

T9.3 — Invoke endpoint (called by Runner Lambda)

Why: Entry point for schedules.

Files

app/api/cron.py

router = APIRouter(prefix="/api/v1/cron", tags=["Cron"])

class CronInvokeBody(BaseModel):
    scheduled_time: datetime

@router.post("/workflows/{workflow_id}:invoke")
def invoke_workflow(workflow_id: int, body: CronInvokeBody, caller: CallerContext = Depends(get_caller)):
    # Auth: must be called with a special Service API key (e.g., "scheduler")
    # Idempotency: ignore if (workflow_id, scheduled_time) seen recently
    # Execute: call existing run_workflow logic with starting_inputs={}


Idempotency cache: simple in-memory LRUCache with TTL 30 minutes keyed by (workflow_id, scheduled_time.isoformat()).

AC

 Requires X-API-Key belonging to Service “scheduler”.

 Returns 202 with {"accepted": true, "run_id": "..."}.

 Duplicate invoke within TTL returns 200 {"accepted": false, "reason":"duplicate"}.

Tests

tests/api/test_cron_invoke.py.

T9.4 — Lambda: Publisher (reads outbox → manages schedules)

Why: Bridge DB → Scheduler.

Files

infra/lambda/scheduler_publisher/handler.py

import os, json, time
import psycopg, boto3
from botocore.config import Config

SCHED = boto3.client("scheduler", config=Config(retries={"max_attempts": 5}))
ENV = os.environ["ENV"]                # dev|stage|prod
DB_DSN = os.environ["DB_DSN"]          # e.g., "postgresql://user:pass@host:5432/db?sslmode=require"
RUNNER_LAMBDA_ARN = os.environ["RUNNER_LAMBDA_ARN"]

def schedule_name(wf_id: int) -> str:
    return f"wf-{wf_id}-{ENV}"

def handler(event, context):
    # 1) connect DB, select a batch of unprocessed outbox rows (FOR UPDATE SKIP LOCKED)
    # 2) for each row:
    #    - load current workflow row to get latest cron_schedule
    #    - if cron_schedule is None: DeleteSchedule(name) if exists
    #    - else: CreateSchedule or UpdateSchedule with:
    #         ScheduleExpression = f"cron({cron_expr})"
    #         ScheduleExpressionTimezone = "UTC"
    #         FlexibleTimeWindow = {"Mode":"OFF"}
    #         Target = {"Arn": RUNNER_LAMBDA_ARN, "RoleArn": <scheduler-invoke-role>, "Input": json.dumps({"workflow_id": wf_id})}
    # 3) mark outbox row processed or store error_message + increment attempt_count
    return {"processed": n}


AC

 Idempotent: creating an existing schedule results in update (handle ResourceAlreadyExists).

 Deletes when cron removed.

 Paginates/limits work per invocation (~100 rows).

Tests

Unit tests for schedule_name and basic branch logic (no AWS calls).

(Integration covered by TF smoke in E10; here keep unit-level).

T9.5 — Lambda: Runner (target of schedules)

Why: Execute workflows on schedule.

Files

infra/lambda/scheduler_runner/handler.py

import os, json, urllib.request
APP_BASE_URL = os.environ["APP_BASE_URL"]
SCHEDULER_API_KEY = os.environ["SCHEDULER_API_KEY"]

def handler(event, context):
    wf_id = event.get("workflow_id")
    scheduled_time = event.get("time") or event.get("scheduled_time") or context.get("time")  # pass through from Scheduler if possible
    body = json.dumps({"scheduled_time": scheduled_time})
    req = urllib.request.Request(
        f"{APP_BASE_URL}/api/v1/cron/workflows/{wf_id}:invoke",
        data=body.encode("utf-8"),
        headers={"Content-Type":"application/json", "X-API-Key": SCHEDULER_API_KEY},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return {"status": resp.status}


AC

 Posts to app with API key, propagates scheduled time.

 Handles network errors with retry by Lambda (config later in TF).

Tests

Small unit test for URL build (no network).

T9.6 — Terraform (core cron bits)

Note: You’ll finish broader infra in E10. Here we ship the cron-specific pieces so engineering can end-to-end cron a dev workflow.

Files

infra/terraform/cron/ module

Inputs: env, VPC + subnets, RDS conn info/secret, app base URL, scheduler service API key (Secret), IAM ARNs.

Resources:

IAM role + policy for Publisher Lambda (SecretsManager read, RDS connect via SG, scheduler:*Schedule perms).

Publisher Lambda (zip from infra/lambda/scheduler_publisher/).

CloudWatch EventBridge rule to run publisher every minute (rate(1 minute)).

IAM role + policy for Runner Lambda (permission to be invoked by Scheduler, VPC if needed to reach app privately; else public).

Runner Lambda (zip from infra/lambda/scheduler_runner/).

EventBridge Scheduler IAM role that allows invoking the Runner (this role ARN is referenced by publisher when creating schedules).

(Optional dev) Security groups for Lambda ↔ RDS if publisher queries RDS directly.

AC

 terraform apply creates both lambdas, rule for publisher, and IAM wiring.

 Outputs include runner_lambda_arn consumed by publisher env.

Tests

terraform validate and a tiny terratest (optional) or manual smoke:

Create workflow with cron via API → see schedule appear in AWS console (dev).

T9.7 — App: cron utils & docs

Files

docs/cron.md

Explains DB source of truth, outbox flow, schedule naming, idempotency.

app/lib/cron.py

Add normalize_cron(expr: str) -> str (strip whitespace), reuse is_valid_cron.

Integrate normalize_cron on save/update in Workflows router.

AC

 Cron strings normalized before persisting.

Tests

Extend cron lib tests.

T9.8 — Operational guardrails

Files

Publisher Lambda:

Backoff on throttling; DLQ (SQS) configured in TF.

Max attempts per outbox row (e.g., 10) then mark failed; CloudWatch metric.

Runner Lambda:

Timeout 15s; concurrency limit small to avoid stampedes.

Metric filter for non-200 responses from app.

AC

 DLQ and metrics created by TF.

 Limits documented in docs/cron.md.

E9 DoD

App emits outbox rows on cron changes.

Publisher Lambda creates/updates/deletes EventBridge Scheduler schedules.

Runner Lambda invokes app /cron/...:invoke with idempotency.

Terraform module stands up both lambdas + rule + IAM (dev).