---
name: "k8s-standards"
description: "Configuration standards for Kubernetes manifests: resource naming, labeling, annotations, security contexts, resource requests/limits, probes, and rollout strategies. ALWAYS invoke when creating, reviewing, or modifying Kubernetes YAML (manifests, Helm chart templates, Kustomize overlays) under k8s/, manifests/, deploy/, or charts/ — any file with apiVersion/kind. Do not write or review a Kubernetes manifest without this skill. Keywords: kubernetes, k8s, manifest, apiVersion, kind, security context, probes, resource limits, labels, rollout."
metadata:
  provenance:
    adaptedFrom:
      - url: "https://github.com/github/awesome-copilot/blob/main/instructions/kubernetes-deployment-best-practices.instructions.md"
        took: "Inspiration only. The topic coverage — labels and metadata, security context, probes, resource requests."
      - url: "https://github.com/github/awesome-copilot/blob/main/instructions/kubernetes-manifests.instructions.md"
        took: "Inspiration only. The manifest-authoring framing."
---

# Kubernetes Standards and Patterns

Standards for authoring Kubernetes manifests that are secure, reliable, and production-ready. Prioritize security, then reliability, then operational convenience.

## Labeling and Metadata

Apply Kubernetes-recommended labels consistently:

- `app.kubernetes.io/name`
- `app.kubernetes.io/instance`
- `app.kubernetes.io/version`
- `app.kubernetes.io/component`
- `app.kubernetes.io/part-of`
- `app.kubernetes.io/managed-by`

Add workload context labels where applicable (`environment`, `team`, `cost-center`).
Use annotations for ownership, monitoring hints (`prometheus.io/scrape`, `prometheus.io/port`), and change tracking.

✅ **GOOD**:
```yaml
metadata:
  name: order-service
  labels:
    app.kubernetes.io/name: order-service
    app.kubernetes.io/instance: order-service-prod
    app.kubernetes.io/version: "1.4.2"
    app.kubernetes.io/component: api
    app.kubernetes.io/part-of: commerce-platform
    app.kubernetes.io/managed-by: helm
```

❌ **BAD**:
```yaml
metadata:
  name: order-service
  labels:
    app: order-service   # Non-standard label scheme
```

## Workload and Exposure Patterns

- Use `Deployment` for stateless services.
- Set `replicas` to at least `2` for production workloads unless explicitly single-instance.
- Prefer `RollingUpdate` and tune `maxSurge` / `maxUnavailable` for service continuity.
- Use `Service` with the correct type (`ClusterIP` for internal defaults, `LoadBalancer` for external access).
- Use `Ingress` for HTTP/HTTPS routing and TLS termination where needed.
- Avoid deploying standalone Pods directly for long-lived workloads.

## Security Baseline

### Pod and Container Security Context

Use secure defaults unless a justified exception exists:

- `runAsNonRoot: true`
- Explicit non-root `runAsUser` / `runAsGroup`
- `seccompProfile.type: RuntimeDefault`
- `allowPrivilegeEscalation: false`
- `readOnlyRootFilesystem: true` when feasible
- `capabilities.drop: [ALL]` and add back only required capabilities

✅ **GOOD**:
```yaml
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 1000
    fsGroup: 2000
    seccompProfile:
      type: RuntimeDefault
  containers:
    - name: app
      securityContext:
        allowPrivilegeEscalation: false
        readOnlyRootFilesystem: true
        capabilities:
          drop: [ALL]
```

❌ **BAD**:
```yaml
spec:
  containers:
    - name: app
      # No securityContext — runs as root by default
```

### Cluster and Network Security

- Enforce least-privilege RBAC via `Role` / `ClusterRole` and bindings.
- Apply `NetworkPolicy` with deny-by-default posture and explicit allows.
- Use Pod Security Admission (`Restricted` preferred in production namespaces).

### Image and Supply Chain Security

- Pin images to specific immutable tags; do not use `:latest`.
- Prefer minimal trusted base images.
- Integrate image vulnerability scanning and signing/verification in CI/CD.

## Configuration and Secret Handling

- Store non-sensitive settings in `ConfigMap`.
- Store credentials, keys, and tokens in `Secret` resources.
- Do not put sensitive values in `ConfigMap`.
- Prefer external secret managers/operators for production environments.

## Health, Reliability, and Scaling

- Configure `livenessProbe`, `readinessProbe`, and `startupProbe` as appropriate.
- Set realistic probe timings (`initialDelaySeconds`, `periodSeconds`, `timeoutSeconds`, thresholds).
- Define CPU and memory `requests` and `limits` for every container.
- Prefer `Guaranteed` or `Burstable` QoS; avoid `BestEffort` in production.
- Add HPA for variable load and consider VPA where right-sized resources are hard to predict.
- Use Pod Disruption Budgets and anti-affinity for high availability.

## Validation and Rollout

- Validate all manifests before apply using dry-run and schema validation (e.g. `kubeconform -strict`).
- For Helm, validate rendered output: `helm template <chart> | kubeconform -strict`.
- Use policy validation tools (OPA Conftest, Kyverno) where available.
- Configure `RollingUpdate` strategy; set `maxUnavailable: 0` for zero-downtime deployments.
- Set `terminationGracePeriodSeconds` to allow graceful shutdown.

## Manifest Review Checklist

- [ ] Resource `apiVersion` and `kind` are correct
- [ ] Naming and label selectors are consistent
- [ ] Standard labels and required annotations are present
- [ ] Replicas, rollout strategy, and availability controls are defined
- [ ] Requests/limits are set for every container
- [ ] Liveness/readiness/startup probes are configured correctly
- [ ] Secrets are in `Secret` resources, not `ConfigMap`
- [ ] Pod/container security contexts meet baseline hardening
- [ ] Image tags are pinned and supply-chain controls are considered
- [ ] Validation checks pass before apply
- [ ] Network policy and RBAC are least privilege

## Notes

- Prefer cluster policy and platform team standards when they are stricter than this document.
- Keep manifests concise; avoid unnecessary fields and duplicated configuration.
- When troubleshooting workload failures, inspect in order: Pod events → container logs → probe config → selector mismatches → resource pressure.
