---
name: "helm-templates"
description: "Conventions for authoring Helm chart templates: _helpers.tpl named templates, template patterns, whitespace control, hooks, and testing. Use when creating or modifying files in templates/, writing _helpers.tpl, using Go template functions, implementing Helm hooks, or linting/unit-testing chart templates. Keywords: helm, templates, _helpers.tpl, named templates, Go template, include, toYaml, nindent, hooks, helm lint."
license: ""
metadata:
  provenance:
    authoritativeSpec:
      - https://helm.sh/docs/chart_template_guide/
      - https://helm.sh/docs/chart_template_guide/function_list/
---

# Helm Template Authoring

Conventions for writing templates that are readable, reusable, and correct.

## `_helpers.tpl` Conventions

All charts must (at a minimum) define these named templates in `_helpers.tpl`. Use `include` (not `template`) everywhere so output can be piped:

| Template name                | Purpose                                                  |
| ---------------------------- | -------------------------------------------------------- |
| `<chart>.name`               | Chart name, truncated to 63 chars                        |
| `<chart>.fullname`           | Release-scoped full name, truncated to 63 chars          |
| `<chart>.chart`              | `name-version` label value                               |
| `<chart>.labels`             | Full set of recommended labels                           |
| `<chart>.selectorLabels`     | Selector-safe subset (name + instance only)              |
| `<chart>.serviceAccountName` | Resolves service account name with create flag           |
| `<chart>.image`              | Renders `repository:tag`, defaulting tag to `appVersion` |

Enforce the 63-char Kubernetes label limit on all name templates:

```
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
```

## Template Patterns

### Namespaces — never hardcode

```yaml
namespace: {{ .Release.Namespace }}
```

### Optional blocks with `with`

```yaml
{{- with .Values.podAnnotations }}
annotations:
  {{- toYaml . | nindent 4 }}
{{- end }}
```

### Structured value passthrough

```yaml
resources:
  {{- toYaml .Values.resources | nindent 2 }}
```

### Required values — fail fast

```yaml
image: {{ required "image.repository is required" .Values.image.repository }}
```

### Default values

```yaml
port: {{ .Values.port | default 8080 }}
```

### ConfigMap checksum — trigger rolling restart on config change

```yaml
annotations:
  checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
```

### Conditional resource file

```yaml
{{- if .Values.ingress.enabled -}}
apiVersion: networking.k8s.io/v1
kind: Ingress
...
{{- end }}
```

## Whitespace Control

- Use `{{-` to trim leading whitespace/newlines; use `-}}` to trim trailing
- Prefer `nindent N` over `indent N` — it adds a leading newline which keeps YAML structure correct when the block is non-empty
- Always use `nindent` after `toYaml` to avoid off-by-one indentation bugs

## Hooks

Annotate hook resources with `helm.sh/hook` and always set a delete policy:

```yaml
annotations:
  "helm.sh/hook": pre-install,pre-upgrade
  "helm.sh/hook-weight": "-5"           # lower = runs first
  "helm.sh/hook-delete-policy": before-hook-creation,hook-succeeded
```

Common hook use cases: database migrations (`pre-upgrade`), secret seeding (`pre-install`), cleanup jobs (`post-delete`).

## Testing and Linting

```bash
# Lint for errors and best practices
helm lint mychart/

# Render templates locally
helm template myrelease mychart/ -f values.yaml

# Simulate upgrade (server-side dry-run)
helm upgrade myrelease mychart/ -f values.yaml --dry-run --debug
```

For template function reference, consult the [Helm template function list](https://helm.sh/docs/chart_template_guide/function_list/) and the bundled [Sprig functions](https://masterminds.github.io/sprig/).