<!-- L9_META
l9_schema: 1
parent: l9-kubernetes-deploying
origin: skill-hardening extract
tags: [kubernetes, kubectl, ops]
status: active
/L9_META -->

# kubectl Commands

```bash
# Apply manifests
kubectl apply -f k8s/

# Check deployment status
kubectl rollout status deployment/my-app

# View pods
kubectl get pods -l app=my-app

# View logs
kubectl logs -f deployment/my-app

# Execute into a pod
kubectl exec -it <pod-name> -- /bin/sh

# Scale
kubectl scale deployment/my-app --replicas=5

# Rollback
kubectl rollout undo deployment/my-app

# Port forward for local debugging
kubectl port-forward svc/my-app 3000:80
```

## Health checks

Always set both:

- **livenessProbe** — process healthy; restarts pod on failure
- **readinessProbe** — can handle traffic; removes from Service on failure

Probe types: `httpGet`, `exec`, `tcpSocket`
