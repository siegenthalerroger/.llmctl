# helm-docs Comment Syntax

Reference for annotating `values.yaml` so `helm-docs` can generate a values table in `README.md`.

Upstream docs: https://github.com/norwoodj/helm-docs

## Basic Format

Place a comment **immediately above** the key it describes. Use the new-style `# --` prefix (preferred over old-style path-based comments):

```yaml
# -- Whether to enable the ingress resource
enabled: false
```

Multi-line descriptions: continue on the next line(s) **without** the `--`. Lines are joined with a space:

```yaml
# -- How many API pods the Deployment keeps running.
# Values below 2 lose availability during a rolling update.
replicaCount: 3
```

## Type Annotation

Override the inferred type shown in the values table:

```yaml
# -- (string) Image tag. Defaults to the chart appVersion
tag: ""

# -- (int) Number of replicas
replicas:
```

## Custom Default Text

When the real default is computed inside the chart, override the displayed default:

```yaml
# -- Service annotations
# @default -- chart will add internal annotations automatically
annotations: []
```

The `# --` description line must come **before** the `@default` line.

## Ignoring a Value

Exclude a key from the generated table entirely:

```yaml
# @ignored
internalKey: value
```

## Which Values Are Documented

- **Leaf nodes** (`string`, `int`, `float`, `bool`, empty `[]`, empty `{}`) are included automatically, even without a comment
- **Non-empty lists and maps** are included **only** if they have a `# --` comment
- Adding a `# --` comment to a non-empty list/map suppresses automatic documentation of its leaf children — document both explicitly if both rows are needed

```yaml
# -- Configure the liveness probe
livenessProbe:
  httpGet:
    # -- Liveness check endpoint path
    path: /healthz
    port: http   # no comment → not in table (parent comment suppresses it)
```

## Nil Values with Type Hints

Document a key that has no default:

```yaml
# -- (string) Override the chart name
nameOverride:
```

## helm-docs + helm-schema Together

When using both tools, place the `@schema` block **before** the `# --` line so helm-docs doesn't include schema annotations in the description:

```yaml
# @schema
# type: integer
# minimum: 1
# @schema
# -- Number of replicas
replicaCount: 1
```

If the `@schema` block appears **after** the `# --` line the schema annotations get captured as part of the description text.

## Running helm-docs

```bash
# Generate README.md in current chart directory
helm-docs

# Search recursively from a root
helm-docs --chart-search-root=charts/

# Dry-run (print to stdout)
helm-docs --dry-run

# Fail on undocumented values
helm-docs --strict
```
