---
name: l9-setting-up-terraform
description: set up Terraform infrastructure-as-code for cloud resources, including provider configuration, modules, state management, and CI integration. use when bootstrapping Terraform IaC, structuring modules/state, or wiring Terraform into CI.
disable-model-invocation: true
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, terraform, iac, infrastructure, ops]
owner: igor_beylin
status: active
version: 1.0.1
updated: 2026-06-06
---

# Setup Terraform

## Purpose

Bootstrap Terraform IaC: project structure, provider config, variables, modules, remote state, gitignore rules, and optional CI plan/apply pipeline.

## Core Contract

| Step | Artifact |
|------|----------|
| Structure | `main.tf`, `variables.tf`, `outputs.tf`, `providers.tf` |
| State | Remote backend + locking |
| Secrets | `.tfvars` gitignored — never committed |
| CI | fmt, validate, plan on PR; apply on merge with gate |
| Modules | Reusable patterns under `modules/` |

## Authority Order

1. Explicit cloud provider, region, and environment separation model.
2. Existing `infra/` or Terraform files in repo.
3. Provider documentation for pinned versions.
4. This skill's steps below.
5. `Unknown` — ask before `terraform apply` to production state.

## Steps

1. **Initialize the project structure**

   ```
   infra/
   ├── main.tf
   ├── variables.tf
   ├── outputs.tf
   ├── terraform.tfvars      # (gitignored)
   ├── providers.tf
   └── modules/
   ```

2. **Configure the provider** — in `providers.tf`:

   ```hcl
   terraform {
     required_version = ">= 1.5"
     required_providers {
       aws = {
         source  = "hashicorp/aws"
         version = "~> 5.0"
       }
     }
     backend "s3" {
       bucket = "my-terraform-state"
       key    = "prod/terraform.tfstate"
       region = "us-east-1"
     }
   }

   provider "aws" {
     region = var.aws_region
   }
   ```

   Adapt the provider for the user's cloud (AWS, GCP, Azure).

3. **Define variables** — in `variables.tf`, define inputs with types, descriptions, and defaults:

   ```hcl
   variable "aws_region" {
     type        = string
     default     = "us-east-1"
     description = "AWS region for resources"
   }

   variable "environment" {
     type        = string
     description = "Deployment environment (dev, staging, prod)"
   }
   ```

4. **Create resources** — in `main.tf`, define the infrastructure the user needs (VPC, RDS, ECS, S3, Lambda, etc.). Extract reusable patterns into modules under `modules/`.

5. **Configure remote state** — use an S3 bucket (AWS), GCS bucket (GCP), or Azure Storage for state. Enable state locking with DynamoDB (AWS).

6. **Add to `.gitignore`**

   ```
   *.tfstate
   *.tfstate.*
   .terraform/
   terraform.tfvars
   *.tfvars
   ```

7. **Add CI pipeline** — create a GitHub Actions workflow that runs `terraform fmt -check`, `terraform validate`, and `terraform plan` on PRs, with `terraform apply` on merge to main (with approval gate).

## Notes

- Never commit state files or `.tfvars` with secrets.
- Use workspaces or separate state files for dev/staging/prod.
- Pin provider versions to avoid breaking changes.
- Run `terraform fmt` before committing.

## Resource Map

No `references/` folder — structure templates and CI notes live in this file.

## Validation

Provider versions MUST be pinned. State files and `.tfvars` with secrets MUST be gitignored. Remote state MUST have locking enabled. `terraform fmt -check` and `validate` MUST pass before apply.

## Failure Handling

- Provider/cloud unknown → ask user; do not assume AWS.
- Existing state → import or migrate plan required; never init duplicate state for same env.
- Secrets in `.tfvars` committed → STOP; rotate secrets and fix gitignore.
- Apply requested without plan review → run plan first; require explicit approval for prod.
