#!/usr/bin/env python3
"""Validate frontmatter of customization files after an Edit/Write.

Wired as a PostToolUse hook (matcher: Edit|Write). Reads the hook event JSON
on stdin, inspects the written file, and — only for customization files
(*.agent.md, SKILL.md, *.prompt.md, *.instructions.md) — checks the
repository's required frontmatter conventions.

Exit codes (Claude Code PostToolUse contract):
  0  no hard errors (warnings, if any, are printed to stderr and surfaced)
  2  hard errors found — stderr is fed back to the agent so it self-corrects

Dependency-free: extracts only the `name`/`description` fields with light
parsing rather than requiring a YAML library. Multi-line folded/block values
are not fully parsed; such cases are treated as present.
"""
import json
import os
import re
import sys

RESERVED = ("anthropic", "claude", "copilot", "openai")
KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def read_event():
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}


def customization_kind(path):
    base = os.path.basename(path)
    if base == "SKILL.md":
        return "skill"
    if base.endswith(".agent.md"):
        return "agent"
    if base.endswith(".prompt.md"):
        return "prompt"
    if base.endswith(".instructions.md"):
        return "instruction"
    return None


def extract_frontmatter(text):
    """Return the raw frontmatter block, or None if absent."""
    if not text.startswith("---"):
        return None
    # split on the first two '---' fences
    parts = text.split("\n")
    if parts[0].strip() != "---":
        return None
    for i in range(1, len(parts)):
        if parts[i].strip() == "---":
            return "\n".join(parts[1:i])
    return None


def field(frontmatter, key):
    """Extract a top-level scalar field value (quoted or bare). None if absent."""
    m = re.search(rf"(?m)^{re.escape(key)}:\s*(.*)$", frontmatter)
    if not m:
        return None
    val = m.group(1).strip()
    if val == "" or val in ("|", ">", "|-", ">-"):
        # block scalar or empty inline — treat as "present but unparsed"
        return "" if val == "" else "<block>"
    if (val.startswith('"') and val.endswith('"')) or (
        val.startswith("'") and val.endswith("'")
    ):
        val = val[1:-1]
    return val


def reserved_hits(value):
    low = value.lower()
    return [w for w in RESERVED if re.search(rf"\b{w}\b", low)]


def validate(path, kind, text):
    errors, warnings = [], []
    fm = extract_frontmatter(text)
    if fm is None:
        errors.append("missing YAML frontmatter (no leading `---` block)")
        return errors, warnings

    name = field(fm, "name")
    desc = field(fm, "description")

    if not name:
        errors.append("frontmatter is missing a non-empty `name`")
    if not desc:
        errors.append("frontmatter is missing a non-empty `description`")

    if kind == "skill" and name:
        parent = os.path.basename(os.path.dirname(os.path.abspath(path)))
        if name != parent:
            errors.append(
                f"skill `name` ('{name}') must match its parent directory ('{parent}')"
            )
        if len(name) > 64:
            errors.append("skill `name` exceeds 64 characters")
        if not KEBAB.match(name):
            errors.append(
                "skill `name` must be lowercase letters/numbers/hyphens, "
                "no leading/trailing or doubled hyphens"
            )

    # Reserved words are disallowed in the `name` (identifier/namespace) for all
    # types. Descriptions are intentionally NOT checked: cross-tool steering
    # files must name the harnesses they target (e.g. "Claude Code", "Copilot").
    if name:
        hits = reserved_hits(name)
        if hits:
            errors.append("`name` contains reserved word(s): " + ", ".join(hits))

    # filename kebab-case (skip SKILL.md — dir name is the identifier)
    if kind != "skill":
        stem = re.sub(r"\.(agent|prompt|instructions)\.md$", "", os.path.basename(path))
        if not KEBAB.match(stem):
            warnings.append(
                f"filename stem '{stem}' is not kebab-case (lowercase + hyphens)"
            )

    return errors, warnings


def main():
    event = read_event()
    tool_input = event.get("tool_input") or {}
    path = tool_input.get("file_path") or tool_input.get("path")
    if not path:
        sys.exit(0)

    kind = customization_kind(path)
    if not kind:
        sys.exit(0)

    try:
        with open(path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        sys.exit(0)

    errors, warnings = validate(path, kind, text)
    rel = os.path.relpath(path)

    if warnings:
        for w in warnings:
            print(f"[customization-frontmatter] warning: {rel}: {w}", file=sys.stderr)

    if errors:
        print(
            f"[customization-frontmatter] {rel} has frontmatter errors that must be "
            f"fixed (see meta-{kind} skill):",
            file=sys.stderr,
        )
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
