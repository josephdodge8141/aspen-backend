Epic E11 — Deployments (CI/CD)

Goal: GitHub Actions pipelines to build/push images, run migrations, deploy ECS updates, publish frontend to S3/CloudFront, and optionally run Terraform with OIDC-based AWS auth. Include versioning, smoke tests, and rollbacks.

Repo prerequisites
.github/
  workflows/
    backend.yml
    mcp.yml
    frontend.yml
    terraform.yml
scripts/
  migrate.sh            # wraps alembic upgrade head
  render_taskdef.py     # inject image tag/env into ECS taskdef JSON (optional)
docs/
  deployments.md

T11.1 — AWS OIDC for GitHub Actions

Why: Keyless deploys.

Deliverables

AWS IAM: Create an IAM role per env with trust to GitHub OIDC provider (org/repo + branch conditions).

Least-privilege policies:

Backend/MCP: ECR (push), ECS (update service/register task), Logs (read), SSM/Secrets (read).

Frontend: S3 put, CloudFront invalidation.

Terraform: broader (apply), gated by manual approval.

AC

 aws-actions/configure-aws-credentials@v4 can assume role in workflows.

Tests

Dry-run aws sts get-caller-identity step prints expected account.

T11.2 — Backend pipeline (build → push → migrate → deploy)

Why: Automate API deployments.

Deliverables

.github/workflows/backend.yml

Triggers: on push to main, on tags api-v*.

Jobs:

build

Setup Python, cache deps, run tests, lint.

Build Docker image api:${GIT_SHA}.

Log in to ECR, push :sha and :branch-latest, optionally :semver.

migrate (needs build)

Run container with env DATABASE_URL from AWS Secrets (via OIDC).

scripts/migrate.sh executes alembic upgrade head.

deploy (needs migrate)

Render new taskdef (or update container image in existing taskdef).

aws ecs update-service --force-new-deployment.

Wait for service stable.

Smoke test: curl https://api.<domain>/healthz (retry 5×).

If smoke fails, rollback: update service to previous taskdef (store ARN as artifact).

Secrets/vars:

Per-env: ECR repo URI, ECS cluster/service, region, domain, Secrets ARNs.

AC

 On push, image lands in ECR; service updates; smoke returns 200.

 Failing smoke triggers rollback step (manual approval optional).

Artifacts/Logs

Upload taskdef JSON and endpoint logs for debugging.

T11.3 — MCP pipeline (build → push → deploy)

Deliverables

.github/workflows/mcp.yml

Similar to backend but no migration step.

Update ECS service ${app}-mcp.

AC

 MCP image pushed and service rolled out; basic HTTP /healthz succeeds (run via one-shot task or service internal check).

T11.4 — Frontend pipeline (build → upload → invalidate)

Deliverables

.github/workflows/frontend.yml

Triggers: on push to main in frontend/ or tags fe-v*.

Steps:

Setup Node, cache.

npm ci && npm run build → outputs in frontend/dist/.

aws s3 sync frontend/dist s3://fe-<app>-<env>/ --delete

aws cloudfront create-invalidation --distribution-id <id> --paths "/*"

Smoke: curl -I https://app.<domain>/ expecting 200.

AC

 Files uploaded; CF invalidated.

T11.5 — Terraform pipeline (plan/apply with approval)

Deliverables

.github/workflows/terraform.yml

Triggers: on PR (plan), manual dispatch (apply).

Steps:

Configure AWS via OIDC.

terraform init (remote state)

terraform fmt -check, validate

terraform plan -var-file=envs/${ENV}/terraform.tfvars → upload plan artifact

apply job requires environment approval.

AC

 PR shows plan summary; apply gated.

T11.6 — Versioning & release metadata

Deliverables

Stamp /version using build args: VERSION, GIT_SHA.

Create tag flows: when tagging api-vX.Y.Z, workflow sets :X.Y.Z tag on image and annotates ECS service with ECS_DEPLOYMENT_VERSION env var (optional).

AC

 GET /version returns semver+sha matching deployment.

T11.7 — Rollout strategy & rollback

Deliverables

ECS service settings:

Rolling update: minimumHealthyPercent=100, maximumPercent=200 (dev lower).

In workflow:

Save previous taskdef ARN before update.

If smoke fails, run aws ecs update-service --task-definition <previous-arn>.

AC

 Verified rollback path in a test deploy (dev).

T11.8 — Post-deploy smoke tests & canaries

Deliverables

Script scripts/smoke.sh:

Checks /healthz, /openapi.json, and one authenticated 401 check (e.g., /api/v1/experts returns 401 without auth).

GH Action runs smoke with retries/backoff.

AC

 Pipeline fails fast on broken deploys.

T11.9 — Documentation & onboarding

Deliverables

docs/deployments.md:

How pipelines work, required AWS roles, secrets, manual hotfix, rollback, and how to run a one-off migration.

Update README.md with badges/links.

AC

 New engineer can ship to dev end-to-end by following docs.

E11 DoD

Back-end, MCP, and Front-end have reliable CI/CD to AWS using OIDC (no static keys).

Back-end migrations run automatically.

Smoke tests and rollback guard deployments.

Terraform pipelines produce plans and gated applies.