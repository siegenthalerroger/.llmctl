---
name: "Load TF Standards"
description: "Forces loading of TF standards and patterns for .tf and .tofu files"
# Copilot
applyTo: "**/*.tofu, **/*.tf"
# Claude Code
paths: ["**/*.tofu", "**/*.tf"]
---

# TF Development

When working with `.tf` or `.tofu` files, load and read the following skill **before making any edits**. Do not defer loading until a later turn.

- [TF Standards and Patterns](../skills/tf-standards/SKILL.md) — authoring conventions for the source text.

Also load the `terraform-skill` skill when the task touches execution or operational risk: state operations, plan/apply/destroy safety, CI drift, module testing, or provider upgrades.
