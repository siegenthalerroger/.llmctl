---
name: "helm-values"
description: "Authoring values.yaml in Helm charts with mandatory helm-docs documentation comments and helm-schema type annotations. ALWAYS invoke when creating or editing values.yaml, adding value descriptions, generating values.schema.json or README docs, setting up helm-docs/helm-schema pre-commit hooks, or reviewing values for missing annotations. Do not add or edit a values.yaml entry without this skill — every value needs its annotation; for chart structure use helm-charts, for templates/ use helm-templates. Keywords: helm, values.yaml, helm-docs, helm-schema, values.schema.json, annotations, documentation, schema, pre-commit."
metadata:
  provenance:
    authoritativeSpec:
      - https://github.com/norwoodj/helm-docs
      - https://github.com/dadav/helm-schema
---

# Helm Values Authoring

Conventions for `values.yaml` files in charts that use the helm-docs / helm-schema toolchain.

## When to apply the annotation rules

Apply the annotation rules below ONLY when the chart already uses this tooling. Detect it first:

- `values.schema.json` exists, OR
- a generated values table is present in `README.md`, OR
- existing keys already carry `# @schema` / `# --` comments.

If none hold, the chart uses plain comments — match that existing style and add a plain `# comment` above new keys. Do NOT introduce `# @schema` / `# --` annotations onto a handful of keys in a chart that has none; piecemeal annotations imply tooling that is not wired up and read as inconsistent. New value blocks must read like the surrounding values, not like a different chart.

## Core Rule

Every key in `values.yaml` must have:

1. A **helm-schema annotation block** (`# @schema` … `# @schema`) for any key where type constraints are meaningful
2. A **helm-docs description comment** (`# -- description text`) immediately preceding the key

Both comments must appear directly above the key they describe, in this order: `@schema` block first, then `# --` line, then the key itself.

```yaml
# @schema
# type: integer
# minimum: 1
# @schema
# -- Number of pod replicas
replicaCount: 1
```

When no schema constraint is needed (e.g. a free-form object), omit the `@schema` block but keep the `# --` line:

```yaml
# -- Additional pod annotations
podAnnotations: {}
```

See the [helm-docs comment spec](./references/helm-docs-comments.md) and [helm-schema annotation spec](./references/helm-schema-annotations.md) for full syntax.

## Values Structure Conventions

Group values in this order:

1. **Replica / scale** — `replicaCount`
2. **Image** — `image.repository`, `image.tag`, `image.pullPolicy`, `imagePullSecrets`
3. **Service account** — `serviceAccount.*`
4. **Pod metadata** — `podAnnotations`, `podLabels`
5. **Security** — `podSecurityContext`, `securityContext`
6. **Service / networking** — `service.*`, `ingress.*`
7. **Resources** — `resources.requests`, `resources.limits`
8. **Autoscaling** — `autoscaling.*`
9. **Scheduling** — `nodeSelector`, `tolerations`, `affinity`
10. **Application config** — chart-specific values
11. **Escape hatches** — `extraEnv`, `extraVolumes`, `extraVolumeMounts`, `extraContainers`
12. **Sub-chart config** — sub-chart name as top-level key

Always provide sensible non-empty defaults for `resources.requests` and `resources.limits`.
Use `enabled: false` as the default for optional features (ingress, autoscaling, metrics).

## Automation

### Generating documentation (helm-docs)

```bash
helm-docs --chart-search-root=.
```

Regenerate after any `values.yaml` change. The generated `README.md` must be committed alongside `values.yaml`.

### Generating schema (helm-schema)

```bash
helm-schema
```

Regenerate after any `values.yaml` change. The generated `values.schema.json` must be committed.

### Pre-commit hooks

Add both hooks to `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/norwoodj/helm-docs
    rev: ""  # pin to a release tag
    hooks:
      - id: helm-docs
  - repo: https://github.com/dadav/helm-schema
    rev: ""  # pin to a release tag
    hooks:
      - id: helm-schema
```

### IDE schema validation

Add this line at the top of `values.yaml` to enable IDE completion and validation:

```yaml
# yaml-language-server: $schema=values.schema.json
```

Use `helm-schema -r` to add this automatically if it's missing.

## References

- [helm-docs comment syntax](./references/helm-docs-comments.md)
- [helm-schema annotation syntax](./references/helm-schema-annotations.md)