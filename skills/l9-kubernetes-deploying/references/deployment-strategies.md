<!-- L9_META
l9_schema: 1
parent: l9-kubernetes-deploying
origin: skill-hardening extract
tags: [kubernetes, deployment, hpa, scaling]
status: active
/L9_META -->

# Deployment Strategies and Scaling

## Strategies

| Strategy | How | When |
|----------|-----|------|
| Rolling update (default) | Replace pods one at a time | Most deployments |
| Recreate | Kill all old pods, start new | Cannot run two versions |
| Blue/green | Two environments, switch traffic | Instant rollback |
| Canary | Small % traffic to new version | High-risk changes |

Rolling update config:

```yaml
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
```

## Horizontal Pod Autoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: my-app
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-app
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

## Tips

- Always set resource requests and limits
- Use namespaces to isolate environments (`dev`, `staging`, `prod`)
- Never put secrets in plaintext YAML committed to git
- Tag images with specific versions — never `:latest` in production
- Set `PodDisruptionBudget` for high-availability workloads
