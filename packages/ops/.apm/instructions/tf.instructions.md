---
name: "Load TF Standards"
description: "Loads the Terraform/OpenTofu standards skill before any edit, plus the operational skill for state, plan/apply and provider-upgrade work. Applies when writing, editing or reviewing .tf or .tofu files."
# Copilot
applyTo: "**/*.tofu, **/*.tf"
# Claude Code
paths: ["**/*.tofu", "**/*.tf"]
---

# TF Development

When working with `.tf` or `.tofu` files, load and read the following skill **before making any edits**. Do not defer loading until a later turn.

- [TF Standards and Patterns](../skills/tf-standards/SKILL.md) — authoring conventions for the source text.

Also load the `terraform-skill` skill when the task touches execution or operational risk: state operations, plan/apply/destroy safety, CI drift, module testing, or provider upgrades.
