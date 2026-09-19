"""Which steering files were last touched before the guidance that governs them.

`meta-steering` and `meta-harness` say how every other steering file should be
written. When one of them moves, the files it governs may no longer match it,
and nothing announces that. This asks git which guidance commits landed after
a file was last touched, and prints them.

**A commit is evidence, not a verdict.** A cosmetic change to the guidance
marks every file it governs `behind`, and an edit to a file for an unrelated
reason clears the flag without anyone having re-read it. So the gap commits are
printed rather than counted: one look at their subjects usually settles it.
Deciding what the gap means is the `meta-review-steering` skill's job.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import NamedTuple, Sequence

import typer

from . import workspace
from .workspace import WorkspaceError, git

# What governs what. The guidance is one skill per column of the repository's
# own type table: `meta-steering` owns what the model reads, `meta-harness`
# what the harness executes. Each entry maps a file's kind to the guidance
# paths it must agree with -- the router plus the reference pages for that kind,
# never the whole directory, so an edit to the agent pages does not mark every
# SKILL.md behind.
STEERING = "packages/core/.apm/skills/meta-steering"
HARNESS = "packages/core/.apm/skills/meta-harness"

GOVERNED: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("SKILL.md", "skill", (
        "%s/SKILL.md" % STEERING,
        "%s/references/skills.md" % STEERING,
        "%s/references/skill-body.md" % STEERING,
        "%s/references/skill-frontmatter.md" % STEERING,
        "%s/references/skill-spec.md" % STEERING,
        "%s/references/skill-structure.md" % STEERING,
    )),
    ("*.agent.md", "agent", (
        "%s/SKILL.md" % STEERING,
        "%s/references/agents.md" % STEERING,
        "%s/references/agent-frontmatter.md" % STEERING,
        "%s/references/agent-handoff.md" % STEERING,
        "%s/references/agent-patterns.md" % STEERING,
        "%s/references/agent-subagent.md" % STEERING,
        "%s/references/agent-tools.md" % STEERING,
    )),
    ("*.instructions.md", "instructions", (
        "%s/SKILL.md" % STEERING,
        "%s/references/instructions.md" % STEERING,
        "%s/references/instruction-bootstrapping.md" % STEERING,
    )),
    ("*.prompt.md", "prompt", (
        "%s/SKILL.md" % STEERING,
        "%s/references/prompts.md" % STEERING,
    )),
    ("*.hook.json", "hook", (
        "%s/SKILL.md" % HARNESS,
        "%s/references/hooks.md" % HARNESS,
    )),
)

# Where authored steering lives. `apm_modules/` is somebody else's content and
# the deploy mirrors are copies, so neither is ours to hold to this standard.
ROOTS = ("packages", ".apm")
SKIP_DIRS = {".git", "apm_modules", "build", "node_modules", "__pycache__",
             ".claude", ".agents", ".codex", "LICENSES"}

# `apm.yml` is deliberately absent, though meta-harness governs its MCP block:
# a manifest's newest commit is nearly always a pin bump, so measuring it here
# would report drift that has nothing to do with the guidance.


class Stamp(NamedTuple):
    """A path's newest commit."""

    sha: str
    date: str


class Row(NamedTuple):
    """One governed file, and the guidance commits it has not seen."""

    path: str
    kind: str
    stamp: Stamp
    guidance: Stamp
    gap: tuple[str, ...]

    @property
    def status(self) -> str:
        if not self.stamp.date:
            return "uncommitted"
        return "behind" if self.gap else "current"


def newest(repo: Path, paths: Sequence[str]) -> Stamp:
    """The newest commit touching any of `paths`, or an empty stamp."""
    out = git(["log", "-1", "--format=%H%x1f%cI", "--", *paths], repo, check=False)
    sha, _, date = out.partition("\x1f")
    return Stamp(sha.strip(), date.strip())


def unseen(repo: Path, paths: Sequence[str], seen: str) -> tuple[str, ...]:
    """Guidance commits not reachable from `seen`, newest first.

    Reachability rather than dates. A rebase gives every commit it replays the
    same second, so a file touched in the same rebase as the guidance reads as
    older than it by the clock while being demonstrably later in history.
    """
    if not seen:
        return ()
    out = git(["log", "--format=%h %s", "HEAD", "--not", seen, "--", *paths],
              repo, check=False)
    return tuple(line for line in out.split("\n") if line.strip())


def governed_files(repo: Path) -> list[tuple[Path, str, tuple[str, ...]]]:
    """Every authored steering file, with its kind and the guidance over it."""
    found = []
    for root in ROOTS:
        top = repo / root
        if not top.is_dir():
            continue
        for path in sorted(top.rglob("*")):
            if not path.is_file() or SKIP_DIRS & set(path.parts):
                continue
            for pattern, kind, guidance in GOVERNED:
                matches = (path.name == pattern if pattern == "SKILL.md"
                           else path.name.endswith(pattern.lstrip("*")))
                if matches:
                    found.append((path, kind, guidance))
                    break
    return found


def review(repo: Path, include: str = "") -> list[Row]:
    """Every governed file, most-behind first, then by path."""
    rows = []
    guidance_stamps: dict[tuple[str, ...], Stamp] = {}
    for path, kind, guidance in governed_files(repo):
        rel = path.relative_to(repo).as_posix()
        # The guidance cannot be measured against itself.
        if any(rel == g or rel.startswith(g.rsplit("/", 1)[0] + "/")
               for g in guidance):
            continue
        if include and include not in rel:
            continue
        if guidance not in guidance_stamps:
            guidance_stamps[guidance] = newest(repo, guidance)
        head = guidance_stamps[guidance]
        stamp = newest(repo, [rel])
        gap = unseen(repo, guidance, stamp.sha)
        rows.append(Row(rel, kind, stamp, head, gap))
    return sorted(rows, key=lambda r: (-len(r.gap), r.path))


def report(rows: Sequence[Row], out=sys.stdout) -> None:
    behind = [r for r in rows if r.status == "behind"]
    for row in rows:
        if row.status == "current":
            continue
        print("[%s] %-58s %s" % (row.status, row.path, row.stamp.date[:10]), file=out)
        for line in row.gap:
            print("           guidance: %s" % line, file=out)
    print("\n%d file(s): %d behind, %d current, %d uncommitted"
          % (len(rows), len(behind),
             sum(1 for r in rows if r.status == "current"),
             sum(1 for r in rows if r.status == "uncommitted")), file=out)
    if behind:
        print("A commit says the guidance moved, not that this file is wrong. Read "
              "the gap commits above:\nif none of them changed a rule this file has "
              "to follow, there is nothing to do.", file=out)


def main(repo: Path = workspace.REPO_OPTION,
         include: str = typer.Option("", "--include", metavar="TEXT",
                                     help="Only paths containing this text."),
         json_out: bool = typer.Option(False, "--json",
                                       help="Machine-readable output on stdout.")) -> None:
    """Show which steering files predate the guidance that governs them."""
    try:
        rows = review(repo.resolve(), include)
    except WorkspaceError as exc:
        raise workspace.die(exc)

    if json_out:
        json.dump({"files": [{"path": r.path, "kind": r.kind, "status": r.status,
                              "last_commit": r.stamp.sha[:7], "last_date": r.stamp.date,
                              "guidance_commit": r.guidance.sha[:7],
                              "guidance_date": r.guidance.date,
                              "gap": list(r.gap)} for r in rows]},
                  sys.stdout, indent=2)
        print()
        return
    report(rows)


def cli() -> None:
    typer.run(main)
