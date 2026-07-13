---
name: "helm-charts"
description: "Helm chart structure, dependency management, library charts, and install/upgrade troubleshooting. ALWAYS invoke when creating or adapting chart structure (Chart.yaml, subcharts), managing chart dependencies, using third-party or library charts, or debugging why a Helm install/upgrade isn't taking effect. Do not hand-edit Chart.yaml, add a dependency, or diagnose a failed release without this skill — for templates/ authoring use helm-templates, for values.yaml use helm-values. Keywords: helm, chart, Chart.yaml, dependencies, library chart, helm install, helm upgrade, helm template, troubleshoot."
license: ""
metadata:
  provenance:
    authoritativeSpec:
      - https://helm.sh/docs/topics/charts/
      - https://helm.sh/docs/helm/
---

# Helm Charts

Guidelines for chart structure conventions, dependency management, and the verification workflow to follow before making configuration changes.

## Chart Structure Conventions

- `Chart.yaml`: use `type: application` for deployable charts, `type: library` for shared named-template-only charts
- `values.yaml`: all values must be documented with helm-docs comments and helm-schema annotations — see the [helm-values](../helm-values/SKILL.md) skill
- `templates/_helpers.tpl`: all repeated fragments (labels, names, selectors) must be named templates — see the [helm-templates](../helm-templates/SKILL.md) skill
- `values.schema.json`: always present and generated from `values.yaml` annotations via `helm-schema`
- `README.md`: always generated from `values.yaml` via `helm-docs`
- Commit `Chart.lock` to source control; never commit unpackaged dependency tarballs

## Dependency Management

- Declare dependencies in `Chart.yaml` under `dependencies:` with a `condition` field so sub-charts are opt-in by default
- Use pessimistic constraint operator (`~`) for patch-level ranges (`~12.1.0` = `12.1.x`); use `^` only when major API compatibility is guaranteed
- Run `helm dependency update` after changing `Chart.yaml`; commit the updated `Chart.lock`
- For umbrella charts that compose multiple application charts, prefer explicit sub-chart values namespacing over `import-values`
- Library charts (`type: library`) are merged at the parent schema level by `helm-schema` — avoid property name collisions

## Verification Workflow

Before configuring or troubleshooting any Helm deployment, follow these steps in order:

1. [ ] **Inspect available values** — `helm show values <repo>/<chart>` or `helm show values <release>` — never assume a chart exposes all Kubernetes fields
2. [ ] **Check current values** — `helm get values <release> -n <namespace> --all`
3. [ ] **Render templates** — `helm template <release> <chart> -f values.yaml | grep -A10 <target-field>` — verify the field actually appears in rendered output
4. [ ] **Make informed changes** — only configure fields confirmed to exist in the chart's value schema
5. [ ] **Apply and validate** — `helm upgrade <release> <chart> -f values.yaml -n <namespace> --dry-run` before live apply

If a required Kubernetes field is not exposed by the chart, prefer `kubectl patch` over fighting the chart:

```bash
kubectl patch deployment <name> -n <namespace> --type=merge \
  -p '{"spec":{"template":{"spec":{"securityContext":{"runAsUser":1000}}}}}'
```

## Common Pitfalls

- **Never hardcode namespaces** in templates — use `{{ .Release.Namespace }}`
- **Always use `--atomic`** in CI/CD `helm upgrade` calls — without it a failed release leaves resources in a broken state
- **No secrets in `values.yaml`** — use External Secrets, Sealed Secrets, or `--set` injection from CI vault
- **Always set resource requests/limits** in default `values.yaml` — workloads without constraints are deprioritized by the scheduler
- **Chart templates are not transparent passthroughs** — only fields the template author explicitly wired up are configurable via values
