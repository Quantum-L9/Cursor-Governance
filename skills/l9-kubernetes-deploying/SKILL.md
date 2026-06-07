---
name: l9-kubernetes-deploying
description: deploy applications to Kubernetes — Deployments, Services, Ingress, ConfigMaps, Secrets, health checks, and scaling. use when writing or debugging Kubernetes manifests, deploying to a cluster, or configuring scaling/health checks.
skill_schema: 1
layer: control_plane
role: skill_entrypoint
tags: [l9, kubernetes, k8s, deployment, ops]
owner: igor_beylin
status: active
version: 1.1.0
updated: 2026-06-06
disable-model-invocation: true
---

# Kubernetes Deploying

## Purpose

Deploy and manage applications on Kubernetes: core manifests, rollout commands, health checks, scaling, and deployment strategies. Explicit-only skill — load when the user asks for k8s deploy help.

## Core Contract

| Task | Load |
|------|------|
| Manifest templates | [references/core-manifests.md](references/core-manifests.md) |
| kubectl operations | [references/kubectl-commands.md](references/kubectl-commands.md) |
| Rollout strategies + HPA | [references/deployment-strategies.md](references/deployment-strategies.md) |

## Authority Order

1. Explicit user cluster context, namespace, and image/tag.
2. Existing manifests in repo — extend, do not replace silently.
3. Kubernetes API conventions for the cluster version.
4. This skill's references.
5. `Unknown` — ask before applying to production namespaces.

## Compact Workflow

1. **Confirm** — namespace, image tag (never `:latest` in prod), secrets source.
2. **Manifest** — Deployment + Service + Ingress + ConfigMap/Secret per refs.
3. **Health** — liveness + readiness probes on every Deployment.
4. **Apply** — `kubectl apply -f`; verify rollout status.
5. **Validate** — pods ready, probes passing, ingress reachable.

## Resource Map

- [references/core-manifests.md](references/core-manifests.md) — Deployment, Service, Ingress, ConfigMap, Secret YAML.
- [references/kubectl-commands.md](references/kubectl-commands.md) — apply, rollout, logs, scale, port-forward.
- [references/deployment-strategies.md](references/deployment-strategies.md) — rolling/recreate/blue-green/canary, HPA, tips.

## Validation

Resource requests and limits MUST be set. Secrets MUST NOT appear in committed plaintext YAML — use Sealed Secrets, SOPS, or external managers. Production images MUST use specific version tags.

## Failure Handling

- Rollout stuck → `kubectl describe pod`, check probes and image pull.
- CrashLoopBackOff → logs first; do not scale up blindly.
- Missing cluster access → STOP; ask for kubeconfig context.
- Secret values in chat → redact; never echo credentials.
