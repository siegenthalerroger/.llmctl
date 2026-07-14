# helm-schema Annotation Syntax

Reference for annotating `values.yaml` so `helm-schema` can generate `values.schema.json` (JSON Schema Draft 7).

Upstream docs: https://github.com/dadav/helm-schema

## Block Format

Wrap annotation YAML between two `# @schema` markers, placed **immediately above** the key:

```yaml
# @schema
# type: integer
# minimum: 1
# @schema
replicaCount: 1
```

The block must be the last comment block before the key. If using `helm-docs` together, the `# --` description line goes **between** the closing `# @schema` and the key:

```yaml
# @schema
# type: integer
# minimum: 1
# @schema
# -- Number of replicas
replicaCount: 1
```

## Root-Level Annotations

Apply schema properties to the root document object using `# @schema.root`:

```yaml
# @schema.root
# additionalProperties: false
# @schema.root
```

Must appear before the first key with no blank lines after it.

## Common Annotations

| Annotation | Values | Notes |
|---|---|---|
| `type` | `string`, `integer`, `number`, `boolean`, `array`, `object`, `null` | Multiple: `[string, integer]` |
| `required` | `true` / `false` | All properties required by default unless `-k required` flag used |
| `enum` | YAML array | Restricts to allowed values |
| `minimum` / `maximum` | number | Inclusive bounds for numeric types |
| `exclusiveMinimum` / `exclusiveMaximum` | number | Exclusive bounds |
| `pattern` | regex string | Validates string format |
| `format` | `idn-email`, `ipv4`, `idn-hostname`, `date-time`, `uri`, … | JSON Schema format keywords |
| `default` | any | Shown prominently in IDE autocomplete |
| `deprecated` | `true` / `false` | Marks field as deprecated in IDE |
| `additionalProperties` | `true` / `false` or schema | Default `false` for non-empty objects |
| `items` | schema object | Schema for array items |
| `properties` | map of schemas | Inline property definitions for objects |
| `minLength` / `maxLength` | integer | String length bounds |
| `minItems` / `maxItems` | integer | Array length bounds |
| `examples` | array | IDE autocomplete examples |
| `$comment` | string | Maintainer note, not shown to users |
| `description` | string | Overrides comment-parsed description |

## Common Patterns

### Enum / allowed values

```yaml
# @schema
# enum: [Always, IfNotPresent, Never]
# @schema
# -- Image pull policy
pullPolicy: IfNotPresent
```

### Optional string (nullable)

```yaml
# @schema
# type: [string, "null"]
# @schema
# -- Override the full name
fullnameOverride: ""
```

### Typed array items

```yaml
# @schema
# type: array
# items:
#   type: string
# @schema
# -- List of image pull secrets
imagePullSecrets: []
```

### Free-form map (e.g. annotations)

```yaml
# @schema
# additionalProperties: true
# @schema
# -- Extra pod annotations
podAnnotations: {}
```

### Deprecated key

```yaml
# @schema
# deprecated: true
# @schema
# -- Deprecated: use image.repository instead
imageName: ""
```

### Numeric bounds

```yaml
# @schema
# type: integer
# minimum: 1
# maximum: 100
# @schema
# -- Number of replicas
replicaCount: 1
```

## IDE Validation

Add this line at the top of `values.yaml` to enable schema validation in VS Code (requires the YAML extension):

```yaml
# yaml-language-server: $schema=values.schema.json
```

## Running helm-schema

```bash
# Generate values.schema.json in current directory
helm-schema

# Dry-run (print to stdout)
helm-schema --dry-run

# Recursively from a root
helm-schema --chart-search-root=charts/

# Add yaml-language-server reference if missing
helm-schema -r

# Skip auto-generating additionalProperties
helm-schema -k additionalProperties
```

For advanced patterns (anyOf, oneOf, allOf, if/then/else, $ref, definitions, patternProperties) see the [upstream README](https://github.com/dadav/helm-schema#annotations).
