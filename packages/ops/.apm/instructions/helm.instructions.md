---
name: "Load Helm Skills"
description: "Loads the Helm chart, template and values skills before any edit. Applies when creating, editing or reviewing Chart.yaml, values.yaml, _helpers.tpl or chart templates."
# Copilot
applyTo: "**/Chart.yaml, **/*.tpl, **/values.yaml, **/templates/**/*.yaml"
# Claude Code
paths: ["**/Chart.yaml", "**/*.tpl", "**/values.yaml", "**/templates/**/*.yaml"]
---

# Helm Development

When working with Helm chart files, load and read the following skills **before making any edits**. Do not defer loading until a later turn.

- [Helm Charts](../skills/helm-charts/SKILL.md) — chart structure, dependency management, troubleshooting
- [Helm Templates](../skills/helm-templates/SKILL.md) — `_helpers.tpl` conventions, named templates, whitespace control, hooks
- [Helm Values](../skills/helm-values/SKILL.md) — `values.yaml` authoring with `helm-docs` annotations and `helm-schema` type annotations
