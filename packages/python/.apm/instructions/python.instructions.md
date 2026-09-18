---
name: "Load Python Skills"
description: "Forces loading of Python authoring standards and script discipline for .py files and Python project manifests"
# Copilot
applyTo: "**/*.py, **/*.pyi, **/pyproject.toml"
# Claude Code
paths: ["**/*.py", "**/*.pyi", "**/pyproject.toml"]
---

# Python Development

When working with Python files, load and read the following skills **before making any edits**. Do not defer loading until a later turn.

- [Python Standards and Patterns](../skills/python-standards/SKILL.md) — how the source is written: typing, data modelling, boundaries, errors, resources, logging, concurrency. Applies to every `.py` file, including the body of a script.
- [Python Script Standards](../skills/python-scripts/SKILL.md) — additionally, whenever the file is a standalone script rather than part of a package: PEP 723 inline dependency metadata, shebang, exit codes, and when a script must become a project.

Also load the `modern-python` skill when the task touches project tooling rather than source text: `pyproject.toml` setup, uv commands, linter or type-checker configuration, dependency groups, packaging, pre-commit, CI, or migration off pip/Poetry/black/mypy.
