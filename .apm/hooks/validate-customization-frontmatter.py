#!/usr/bin/env python3
"""Validate frontmatter of customization files after an Edit/Write.

Wired as a PostToolUse hook (matcher: Edit|Write). Reads the hook event JSON
on stdin, inspects the written file, and — only for customization files
(*.agent.md, SKILL.md, *.prompt.md, *.instructions.md) — checks the
repository's required frontmatter conventions.

Also runs as a batch check, over one implementation rather than two:

  python validate-customization-frontmatter.py --all [--repo PATH]
  python validate-customization-frontmatter.py FILE [FILE ...]

The hook only ever fires on a file edited in a Claude session, so drift in
untouched files, edits made from another harness, and rules added after a file
was written all go unnoticed until a deploy misbehaves. `--all` is what CI runs,
and it applies exactly the same rules to the whole tree.

Exit codes (Claude Code PostToolUse contract):
  0  no hard errors (warnings, if any, are printed to stderr and surfaced)
  2  hard errors found — stderr is fed back to the agent so it self-corrects

Exit codes in batch mode, which follow the CI convention instead:
  0  no hard errors      1  hard errors found

Checks (see the meta-steering skill for the authoring rationale behind each;
it owns all four of the file kinds this validates):
  errors (exit 2)   missing frontmatter/name/description; skill name↔dir and
                    kebab/length rules; reserved words in name/description;
                    skill `description` over the 1024-char agentskills.io limit
  warnings (exit 0) multi-line/block-scalar `description` (silently dropped by
                    some skill loaders — keep it single-line); SKILL.md over the
                    ~500-line upstream ceiling; `description`+`when_to_use` over
                    Claude Code's 1536-char discovery truncation; non-kebab filename

Dependency-free: extracts only top-level scalar fields with light parsing
rather than requiring a YAML library. Block/folded values cannot be measured
for length, so they are flagged as multi-line warnings instead.
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


def field_raw(frontmatter, key):
    """Return the unstripped remainder of a top-level field line. None if absent."""
    m = re.search(rf"(?m)^{re.escape(key)}:\s*(.*)$", frontmatter)
    return m.group(1) if m else None


def is_multiline_description(raw):
    """True if the description value is a block scalar or an unclosed inline quote."""
    if raw is None:
        return False
    s = raw.strip()
    if s[:1] in ("|", ">"):
        return True
    if s[:1] in ("\"", "'"):
        return not (len(s) > 1 and s.endswith(s[0]))
    return False


# agentskills.io per-field `description` limit; Claude Code truncates the
# combined `description` + `when_to_use` discovery entry past 1536 chars;
# Anthropic's authoritative SKILL.md ceiling is under 500 lines (and <5000 tokens).
DESC_MAX = 1024
DISCOVERY_MAX = 1536
SKILL_LINE_CEILING = 500


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

    # Reserved words are disallowed in both the `name` (identifier/namespace)
    # and the `description`. Discovery runs off domain keywords, so a harness
    # name is never required to route to the right file.
    if name:
        hits = reserved_hits(name)
        if hits:
            errors.append("`name` contains reserved word(s): " + ", ".join(hits))
    if desc:
        hits = reserved_hits(desc)
        if hits:
            errors.append("`description` contains reserved word(s): " + ", ".join(hits))

    # A multi-line/block `description` is spec-valid YAML but some skill loaders
    # (notably Claude Code) silently drop it, making the skill undiscoverable.
    multiline_desc = is_multiline_description(field_raw(fm, "description"))
    if multiline_desc:
        warnings.append(
            "`description` spans multiple lines or uses a block scalar (`|`/`>`); "
            "keep it on a single line — some loaders silently ignore multi-line descriptions"
        )
    elif desc and kind == "skill" and len(desc) > DESC_MAX:
        # Length is only meaningful for a fully-parsed single-line value.
        errors.append(
            f"skill `description` is {len(desc)} characters; the agentskills.io limit is {DESC_MAX}"
        )

    if kind == "skill":
        when_to_use = field(fm, "when_to_use")
        if (
            not multiline_desc
            and desc
            and when_to_use
            and when_to_use not in ("<block>",)
        ):
            combined = len(desc) + len(when_to_use)
            if combined > DISCOVERY_MAX:
                warnings.append(
                    f"`description` + `when_to_use` is {combined} characters; Claude Code truncates "
                    f"the discovery entry at {DISCOVERY_MAX} — trim or move detail into the body"
                )
        line_count = text.count("\n") + 1
        if line_count > SKILL_LINE_CEILING:
            warnings.append(
                f"SKILL.md is {line_count} lines; the upstream ceiling is under {SKILL_LINE_CEILING} "
                "lines (and <5000 tokens) — split detail into references/ (house style targets ~200)"
            )

    # filename kebab-case (skip SKILL.md — dir name is the identifier)
    if kind != "skill":
        stem = re.sub(r"\.(agent|prompt|instructions)\.md$", "", os.path.basename(path))
        if not KEBAB.match(stem):
            warnings.append(
                f"filename stem '{stem}' is not kebab-case (lowercase + hyphens)"
            )

    return errors, warnings


# Kept in step with provenance.py's `iter_files`, but not shared with it: this
# file is deployed standalone by APM into each harness's hooks directory, where
# nothing else from scripts/ is on disk.
SKIP_DIRS = {".git", "apm_modules", "build", "node_modules", "__pycache__",
             ".claude", ".agents", "LICENSES"}


def discover(root):
    """Every customization file under packages/ and .apm/, in a stable order."""
    found = []
    for base in ("packages", ".apm"):
        top = os.path.join(root, base)
        if not os.path.isdir(top):
            continue
        for dirpath, dirnames, filenames in os.walk(top):
            dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
            for name in sorted(filenames):
                path = os.path.join(dirpath, name)
                if customization_kind(path):
                    found.append(path)
    return found


def batch(argv):
    """Validate many files at once. Returns a process exit code."""
    root, paths, everything = os.getcwd(), [], False
    rest = list(argv)
    while rest:
        argument = rest.pop(0)
        if argument == "--repo" and rest:
            root = rest.pop(0)
        elif argument == "--all":
            everything = True
        elif not argument.startswith("-"):
            paths.append(argument)
    if everything:
        paths = discover(root)
    failed = 0
    for path in paths:
        kind = customization_kind(path)
        if not kind:
            continue
        try:
            with open(path, "r", encoding="utf-8") as fh:
                text = fh.read()
        except OSError as error:
            print(f"[customization-frontmatter] error: {path}: {error}",
                  file=sys.stderr)
            failed += 1
            continue
        errors, warnings = validate(path, kind, text)
        rel = os.path.relpath(path, root)
        for w in warnings:
            print(f"[customization-frontmatter] warning: {rel}: {w}", file=sys.stderr)
        for e in errors:
            print(f"[customization-frontmatter] error: {rel}: {e}", file=sys.stderr)
        failed += 1 if errors else 0

    print(f"[customization-frontmatter] checked {len(paths)} file(s)")
    if failed:
        print(f"[customization-frontmatter] {failed} file(s) with errors",
              file=sys.stderr)
        return 1
    return 0


def main():
    if len(sys.argv) > 1:
        sys.exit(batch(sys.argv[1:]))

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
            "fixed (see the meta-steering skill):",
            file=sys.stderr,
        )
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
