Epic E10 — Terraform Core Infra

Goal: Stand up AWS infra for the app and MCP service: VPC, networking, ECR, ECS (Fargate), RDS Postgres, NLB + Route53 for API, S3+CloudFront for the frontend, Secrets/SSM, CloudWatch logs. Per-env (dev/stage/prod) configuration with remote TF state.

Folder layout (scaffold first)
infra/
  terraform/
    modules/
      vpc/
      ecr/
      ecs_service/
      rds_postgres/
      nlb/
      dns/
      s3_static_site/
      cloudfront/
      secrets/
    envs/
      dev/
        main.tf
        variables.tf
        terraform.tfvars
      stage/
        ...
      prod/
        ...
    backend.tf              # remote state backend (S3 + DynamoDB lock)
    providers.tf            # aws ~> 5.x, region var
    versions.tf             # TF version & provider constraints
Makefile                    # tf-init/plan/apply wrappers

T10.1 — Remote state backend (S3 + DynamoDB)

Why: Safe, shared TF state with locking.

Deliverables

infra/terraform/backend.tf (no secrets committed):

Backend: s3 with bucket <org>-tfstate, key platform/<env>.tfstate, region, dynamodb_table <org>-tf-locks.

Bootstrap script infra/scripts/bootstrap_state.sh (creates bucket & table once).

providers.tf, versions.tf with AWS provider ~> 5.x.

AC

 ./infra/scripts/bootstrap_state.sh dev creates bucket/table (idempotent).

 terraform init -reconfigure uses remote backend.

Tests

terraform validate passes; state saved in S3 (manual check).

T10.2 — VPC module (2 AZs, public/private, NAT)

Why: Network foundation for ECS/RDS.

Deliverables

modules/vpc:

Inputs: cidr_block, az_count, enable_nat_gw_per_az (bool).

Resources: VPC, 2× public subnets, 2× private subnets, IGW, NAT(s), routes, tags.

Outputs: vpc_id, public_subnet_ids, private_subnet_ids, vpc_cidr.

envs/*/main.tf uses module (dev: 1 NAT; prod: 2 NAT).

AC

 Public subnets have default route to IGW; private subnets route to NAT.

 Tags: Name, Env, App.

Tests

terraform plan shows expected counts; terraform validate ok.

T10.3 — ECR repos (app + mcp)

Why: Push Docker images from CI.

Deliverables

modules/ecr:

Create repos: ${app_name}, ${app_name}-mcp.

Image scan on push; immutable tags; lifecycle rules (keep last 30).

Hook module in envs/*/main.tf.

AC

 ecr:GetAuthorizationToken not needed in TF; repos created with scanning.

Tests

terraform plan shows 2 repos; after apply, visible in console.

T10.4 — RDS Postgres (single-AZ dev; multi-AZ prod)

Why: Persistent DB.

Deliverables

modules/rds_postgres:

Inputs: engine_version=15, instance_class, allocated_storage, max_allocated_storage, multi_az (bool), db_name, username, vpc_security_group_ids, db_subnet_ids, backup_retention_days, publicly_accessible=false.

Generate password via random_password → stored in Secrets Manager (see T10.7).

Create parameter group (optional).

Security groups:

rds_sg: inbound 5432 from ECS task SG (from T10.6); no public ingress.

AC

 Dev: db.t4g.medium, single-AZ, 7-day backups.

 Prod: db.m6g.large, multi-AZ, 14-day backups, deletion protection on.

 Outputs: endpoint, port, secret_arn.

Tests

terraform plan matches env; connect from ECS in smoke later.

T10.5 — Secrets / SSM parameters

Why: Store DB creds & app secrets.

Deliverables

modules/secrets:

Secrets Manager secrets: db_credentials (username/password/json), jwt_secret, scheduler_api_key, mcp_app_api_key.

KMS key (optional; default AWS managed).

Inject secrets’ ARNs in outputs.

AC

 Secrets created and retrievable by IAM principals we define in ECS tasks/Lambdas.

Tests

terraform plan shows secrets; manual retrieval gated by IAM.

T10.6 — ECS cluster, roles, and log groups

Why: Run app & MCP on Fargate.

Deliverables

modules/ecs_service (shared):

Create (or reuse) ECS cluster ${app_name}-${env}.

IAM roles:

Task execution role (pull from ECR, write logs, get secrets).

Task role (runtime permissions e.g., SSM/Secrets read).

CloudWatch log group per service (/ecs/${service}) with 30-day retention.

Expose: function service(...) to declare each ECS service (see T10.8, T10.11).

AC

 Cluster exists; log groups created.

Tests

terraform plan ok.

T10.7 — API app ECS service + task definition

Why: Deploy backend API.

Deliverables

In envs/*/main.tf, declare app service via ecs_service module:

Task definition:

Container: ${app_name} on port 8000

Image: from ECR repo

Env: APP_ENV, LOG_LEVEL, VERSION (from CI), REGION

Secrets: DATABASE_URL (compose from RDS secret + endpoint), JWT_SECRET, SCHEDULER_API_KEY

Health check: CMD-SHELL curl localhost:8000/healthz (or container-level HTTP check).

Desired count: dev=1, stage=2, prod=3.

Autoscaling (prod): CPU target 60%, min=3, max=8.

Security group: ecs_app_sg (egress all; inbound from NLB target group subnets—see note below).

Subnets: private.

Note on NLB and SGs: NLB doesn’t use SGs; targets are IPs (ECS tasks). Restrict inbound on task SG to VPC CIDRs of public subnets hosting NLB (coarse but practical). Add comment in TF.

AC

 Task can read secrets; logs to CloudWatch; health check passes.

Tests

Deploy in dev later; curl /healthz via NLB.

T10.8 — NLB + target group + TLS listener + Route53

Why: Public entry for API.

Deliverables

modules/nlb:

NLB in public subnets.

Target group (IP target type) to port 8000, health check /healthz via HTTP on 8000.

TLS listener on 443 with ACM cert ARN; forward to target group.

(Optional) TCP:80 listener → forward (or skip; frontend uses CF).

modules/dns:

ACM certificate for api.<domain> (in same region as NLB).

Route53 alias api.<domain> → NLB.

Wire from envs/*/main.tf.

AC

 NLB healthy; targets register; api.<domain> resolves and returns 200 /healthz.

Tests

Manual smoke after deploy; TF outputs include hostname.

T10.9 — MCP ECS service (internal)

Why: Host the FastMCP server.

Deliverables

Use ecs_service.service again:

Container ${app_name}-mcp on port 8080.

No public LB. Desired count dev=1/prod=2.

Security group: allow egress to API app NLB DNS or API private IPs; allow no inbound (not internet-facing).

Env: APP_BASE_URL (API NLB URL), APP_API_KEY (from secrets).

Logs to CloudWatch.

AC

 MCP tasks can call API via NLB; no inbound exposure.

Tests

Curl from a bastion or run a one-shot task to hit /tools?expert_id=1 (manual).

T10.10 — S3 + CloudFront for frontend

Why: Host FE bundle, CDN, TLS.

Deliverables

modules/s3_static_site:

Private bucket fe-<app>-<env>, block public access.

modules/cloudfront:

OAC (Origin Access Control) to access bucket.

Distribution with default root index.html, cache policies, gzip/brotli on.

ACM cert in us-east-1 for app.<domain>.

modules/dns:

CNAME app.<domain> → CloudFront.

AC

 CF origin access enforced; 403 if direct S3 GET.

 HTTPS on app.<domain>.

Tests

Manual: upload index.html, see 200 via CF.

T10.11 — Outputs & per-env variables

Why: Feed CI/CD and docs.

Deliverables

Outputs in env main.tf:

api_url, cf_url, ecr_repo_urls, rds_endpoint, secrets_arns.

envs/*/terraform.tfvars with sane defaults; document override keys.

AC

 terraform output -json returns required values.

T10.12 — Makefile & TF hygiene

Deliverables

Makefile targets: tf-init ENV=dev, tf-plan ENV=dev, tf-apply ENV=dev.

Pre-commit hook adds terraform fmt -recursive.

docs/infra.md quickstart.

AC

 One-liners work locally.

E10 DoD

terraform apply in envs/dev brings up: VPC, ECR, ECS cluster, API service behind NLB+Route53, RDS, Secrets, MCP service (no public ingress), S3+CF for FE.

Outputs ready for CI/CD.

Docs explain how to run and verify.