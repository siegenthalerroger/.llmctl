"""Check the frontmatter conventions every customization file has to hold to.

Two entry points over one implementation: `--hook` validates the single file a
PostToolUse event names, so a mistake is reported while the author is still in
the file; `--all` validates the whole tree, which is what the `frontmatter`
gate runs. The hook only ever sees files edited in a session, so drift in
untouched files, edits made from another harness, and rules added after a file
was written are the batch pass's to catch.

Exit codes differ by mode, because the hook's contract is not the CI one:
`--hook` exits 2 on errors, so the harness feeds stderr back to the agent to
self-correct; every other mode exits 1, like the rest of the gates.

The authoring rationale behind each rule belongs to the meta-steering skill,
which owns all four of the file kinds validated here.
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Literal, NamedTuple

import typer

from . import provenance as prov
from . import workspace

Kind = Literal["skill", "agent", "prompt", "instruction"]

# Reserved in both `name` (an identifier, and a namespace) and `description`.
# Discovery runs off domain keywords, so a harness name is never what routes a
# request to the right file.
RESERVED = ("anthropic", "claude", "copilot", "openai")
KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

# agentskills.io's per-field `description` limit; Claude Code truncates the
# combined `description` + `when_to_use` discovery entry past 1536 characters;
# Anthropic's authoritative SKILL.md ceiling is under 500 lines (and <5000
# tokens).
NAME_MAX = 64
DESC_MAX = 1024
DISCOVERY_MAX = 1536
SKILL_LINE_CEILING = 500


class Report(NamedTuple):
    """What one pass over the tree found. `errors` fail the gate; `warnings` do not."""

    errors: list[tuple[str, str]]
    warnings: list[tuple[str, str]]
    files: list[str]


def kind_of(path: str | Path) -> Kind | None:
    """Which of the four primitive-defining types a path is, if any."""
    name = Path(path).name
    if name == "SKILL.md":
        return "skill"
    if name.endswith(".agent.md"):
        return "agent"
    if name.endswith(".prompt.md"):
        return "prompt"
    if name.endswith(".instructions.md"):
        return "instruction"
    return None


def discover(root: str | Path) -> Iterator[str]:
    """Every customization file under `packages/` and `.apm/`, in a stable order."""
    return (path for path in prov.iter_files(root) if kind_of(path))


# --- Frontmatter reading ---------------------------------------------------
#
# Deliberately raw text rather than a YAML parse, even though the package has
# one: half these rules are about the shape of the value as written -- a block
# scalar, an unclosed quote, a length in characters -- and a parse normalises
# exactly what they exist to catch.


def extract(text: str) -> str | None:
    """The raw frontmatter block, or None when there is no leading `---` fence."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return "\n".join(lines[1:index])
    return None


def field_raw(frontmatter: str, key: str) -> str | None:
    """The unstripped remainder of a top-level field's line. None if absent."""
    found = re.search(rf"(?m)^{re.escape(key)}:\s*(.*)$", frontmatter)
    return found.group(1) if found else None


def field(frontmatter: str, key: str) -> str | None:
    """A top-level scalar value, unquoted. `<block>` for a block scalar."""
    raw = field_raw(frontmatter, key)
    if raw is None:
        return None
    value = raw.strip()
    if value == "" or value in ("|", ">", "|-", ">-"):
        return "" if value == "" else "<block>"
    if value[:1] in ('"', "'") and value.endswith(value[:1]) and len(value) > 1:
        value = value[1:-1]
    return value


def is_multiline(raw: str | None) -> bool:
    """True for a block scalar or an inline quote left unclosed on the line."""
    if raw is None:
        return False
    value = raw.strip()
    if value[:1] in ("|", ">"):
        return True
    if value[:1] in ('"', "'"):
        return not (len(value) > 1 and value.endswith(value[0]))
    return False


def reserved_hits(value: str) -> list[str]:
    low = value.lower()
    return [word for word in RESERVED if re.search(rf"\b{word}\b", low)]


def skill_name_rules(path: str | Path, name: str) -> list[str]:
    """A skill is addressed by its directory, so its `name` is not free text."""
    errors = []
    parent = Path(path).resolve().parent.name
    if name != parent:
        errors.append(f"skill `name` ('{name}') must match its parent directory ('{parent}')")
    if len(name) > NAME_MAX:
        errors.append(f"skill `name` exceeds {NAME_MAX} characters")
    if not KEBAB.match(name):
        errors.append(
            "skill `name` must be lowercase letters/numbers/hyphens, "
            "no leading/trailing or doubled hyphens"
        )
    return errors


def skill_budget_rules(frontmatter: str, description: str | None, text: str) -> list[str]:
    """The two discovery budgets a skill has to fit inside."""
    warnings = []
    when_to_use = field(frontmatter, "when_to_use")
    if description and when_to_use and when_to_use != "<block>":
        combined = len(description) + len(when_to_use)
        if combined > DISCOVERY_MAX:
            warnings.append(
                f"`description` + `when_to_use` is {combined} characters; Claude Code "
                f"truncates the discovery entry at {DISCOVERY_MAX} -- trim it, or move "
                f"the detail into the body"
            )
    lines = text.count("\n") + 1
    if lines > SKILL_LINE_CEILING:
        warnings.append(
            f"SKILL.md is {lines} lines; the upstream ceiling is under "
            f"{SKILL_LINE_CEILING} lines (and <5000 tokens) -- split detail into "
            f"references/ (house style targets ~200)"
        )
    return warnings


def description_rules(
    frontmatter: str, description: str | None, kind: Kind
) -> tuple[list[str], list[str], bool]:
    """(errors, warnings, multiline) for the one field discovery runs off."""
    errors: list[str] = []
    warnings: list[str] = []
    # A multi-line or block `description` is valid YAML that some skill loaders
    # (Claude Code among them) silently drop, leaving the skill undiscoverable.
    multiline = is_multiline(field_raw(frontmatter, "description"))
    if multiline:
        warnings.append(
            "`description` spans multiple lines or uses a block scalar "
            "(`|`/`>`); keep it on a single line -- some loaders silently "
            "ignore multi-line descriptions"
        )
    elif description and kind == "skill" and len(description) > DESC_MAX:
        # Length only means anything for a value that parsed in full.
        errors.append(
            f"skill `description` is {len(description)} characters; the "
            f"agentskills.io limit is {DESC_MAX}"
        )
    return errors, warnings, multiline


def validate(path: str | Path, kind: Kind, text: str) -> tuple[list[str], list[str]]:
    """Every rule, over one file's text -> (errors, warnings)."""
    errors: list[str] = []
    warnings: list[str] = []

    frontmatter = extract(text)
    if frontmatter is None:
        return ["missing YAML frontmatter (no leading `---` block)"], warnings

    name = field(frontmatter, "name")
    description = field(frontmatter, "description")

    if not name:
        errors.append("frontmatter is missing a non-empty `name`")
    if not description:
        errors.append("frontmatter is missing a non-empty `description`")
    if kind == "skill" and name:
        errors.extend(skill_name_rules(path, name))

    for label, value in (("name", name), ("description", description)):
        hits = reserved_hits(value) if value else []
        if hits:
            errors.append("`{}` contains reserved word(s): {}".format(label, ", ".join(hits)))

    found, noted, multiline = description_rules(frontmatter, description, kind)
    errors.extend(found)
    warnings.extend(noted)

    if kind == "skill":
        if not multiline:
            warnings.extend(skill_budget_rules(frontmatter, description, text))
    else:
        # A skill is identified by its directory, so only the other three are
        # named by their file.
        stem = re.sub(r"\.(agent|instructions|prompt)\.md$", "", Path(path).name)
        if not KEBAB.match(stem):
            warnings.append(f"filename stem '{stem}' is not kebab-case (lowercase + hyphens)")

    return errors, warnings


def check(root: str | Path, paths: Iterator[str] | list[str] | None = None) -> Report:
    """Validate a whole workspace, or the paths given. check.py imports this."""
    root = Path(root)
    report = Report([], [], [])
    for path in discover(root) if paths is None else paths:
        kind = kind_of(path)
        if not kind:
            continue
        rel = os.path.relpath(path, root).replace("\\", "/")
        report.files.append(rel)
        try:
            text = Path(path).read_text(encoding="utf-8")
        except OSError as error:
            report.errors.append((rel, str(error)))
            continue
        errors, warnings = validate(path, kind, text)
        report.errors.extend((rel, message) for message in errors)
        report.warnings.extend((rel, message) for message in warnings)
    return report


def summary(report: Report) -> str:
    return f"checked {len(report.files)} file(s)"


def display_path(path: str, root: Path) -> str:
    """The path as a reader of this workspace knows it, or as given when the
    file sits outside it -- a hook fires on whatever was edited."""
    try:
        rel = os.path.relpath(path, root)
    except ValueError:  # another drive, on Windows
        return str(path)
    return str(path) if rel.startswith("..") else rel


def run_hook(root: Path) -> int:
    """Validate the one file a PostToolUse event names. Returns an exit code."""
    try:
        event = json.load(sys.stdin)
    except Exception:
        return 0

    tool_input = event.get("tool_input") or {}
    path = tool_input.get("file_path") or tool_input.get("path")
    kind = kind_of(path) if path else None
    if not path or not kind:
        return 0

    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return 0

    errors, warnings = validate(path, kind, text)
    rel = display_path(path, root)

    for warning in warnings:
        print(f"[customization-frontmatter] warning: {rel}: {warning}", file=sys.stderr)
    if not errors:
        return 0

    print(
        f"[customization-frontmatter] {rel} has frontmatter errors that must be fixed "
        "(see the meta-steering skill):",
        file=sys.stderr,
    )
    for error in errors:
        print(f"  - {error}", file=sys.stderr)
    # The PostToolUse contract: 2 is what feeds stderr back to the agent.
    return 2


def main(
    repo: Path = workspace.REPO_OPTION,
    files: list[Path] = typer.Argument(
        None, metavar="[FILE]...", help="Validate these files instead of the tree."
    ),
    hook: bool = typer.Option(
        False,
        "--hook",
        help="Read a PostToolUse event on stdin and validate the file it names. Exits 2 on errors.",
    ),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output on stdout."),
) -> None:
    """Check customization frontmatter, over one file or a whole workspace."""
    root = repo.resolve()
    if hook:
        raise typer.Exit(run_hook(root))

    report = check(root, [str(path) for path in files] if files else None)

    if json_out:
        print(
            json.dumps(
                {
                    "files": report.files,
                    "errors": [{"file": f, "message": m} for f, m in report.errors],
                    "warnings": [{"file": f, "message": m} for f, m in report.warnings],
                },
                indent=2,
            )
        )
        raise typer.Exit(1 if report.errors else 0)

    for rel, message in report.warnings:
        print(f"warning: {rel}: {message}", file=sys.stderr)
    for rel, message in report.errors:
        print(f"error: {rel}: {message}", file=sys.stderr)
    print(summary(report))
    if report.errors:
        print(f"{len(report.errors)} error(s)", file=sys.stderr)
        raise typer.Exit(1)
    print("frontmatter OK")


def cli() -> None:
    typer.run(main)
