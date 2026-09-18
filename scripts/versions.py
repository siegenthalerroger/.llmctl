#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "ruamel.yaml==0.19.1",
#   "typer==0.27.2",
#   "rich==15.0.0",
#   "httpx==0.28.1",
#   "python-frontmatter==1.3.0",
# ]
# [tool.uv]
# exclude-newer = "2026-09-18T00:00:00Z"
# ///
"""What each package's next version would be, and why. Writes nothing.

A package is planned when `packages/<dir>/` has commits since its last
`<name>@<version>` tag; the version is `YYYY.M.N`, counting that package's
releases within the UTC month. release.py imports `plan()` rather than keeping a
second copy, so the preview cannot disagree with what is published.
The scheme is in CONTRIBUTING.md#releasing.
"""
from __future__ import annotations

import json
import re
import sys
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple, TextIO

import typer

import commits as commitlib
import workspace
from workspace import Log, WorkspaceError, git

CALVER_RE = re.compile(r"^(?P<y>\d{4})\.(?P<m>\d{1,2})\.(?P<n>\d+)$")

# `mismatches` is [(subject, scope)] -- commits whose scope names a package
# other than the one whose paths they touched.
class Plan(NamedTuple):
    """A package that will be released, and the commits that earned it."""

    directory: str
    name: str
    previous: str | None
    next: str
    commits: list[commitlib.Commit]
    mismatches: list[tuple[str, str]]
    forced: bool


class Skip(NamedTuple):
    """A package with nothing to release, held at the version its tag records."""

    directory: str
    name: str
    tag: str | None
    version: str


def version_of(tag: str | None) -> str:
    return tag.partition("@")[2] if tag else ""


def version_key(version: str) -> tuple[int, ...]:
    """Numeric ordering for `a.b.c` strings of any length; suffixes ignored."""
    return tuple(int(re.sub(r"\D.*$", "", p) or 0) for p in version.split("."))


def last_tag(repo: Path | str, name: str) -> str | None:
    """Newest `<name>@<version>` tag by version order, or None."""
    out = git(["tag", "--list", "%s@*" % name, "--sort=-v:refname"], repo)
    return out.split("\n")[0] if out else None


def next_version(repo: Path | str, name: str, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    prefix = "%d.%d." % (now.year, now.month)
    tags = git(["tag", "--list", "%s@%s*" % (name, prefix)], repo).split()
    highest = 0
    for tag in tags:
        m = CALVER_RE.match(version_of(tag))
        if m:
            highest = max(highest, int(m.group("n")))
    return "%s%d" % (prefix, highest + 1)


def check_forced(repo: Path | str, name: str, previous: str | None,
                 version: str) -> None:
    """Refuse a forced version the next run could not measure from."""
    if not CALVER_RE.match(version):
        raise WorkspaceError("--version %r is not YYYY.M.N" % version)
    if git(["tag", "--list", "%s@%s" % (name, version)], repo):
        raise WorkspaceError("%s@%s already exists" % (name, version))
    if previous and version_key(version) <= version_key(version_of(previous)):
        raise WorkspaceError(
            "--version %s does not sort above %s; the highest tag is the baseline, "
            "so a lower one would never be measured from" % (version, previous))


def plan(repo: Path | str, only: Sequence[str] = (), force: bool = False,
         version: str | None = None, fetch: bool = True,
         log: Log = print) -> tuple[list[Plan], list[Skip]]:
    """(plans, skips) for every package, in discovery order."""
    repo = Path(repo)
    packages = workspace.select(repo, list(only))
    if (force or version) and not only:
        raise WorkspaceError("--force/--version need --package to say which")
    if version and len(packages) != 1:
        raise WorkspaceError("--version applies to exactly one --package")

    if fetch:
        workspace.fetch_tags(repo, log=log)

    plans, skips = [], []
    for package in packages:
        tag = last_tag(repo, package.name)
        history = commitlib.log(repo, "%s..HEAD" % tag if tag else "",
                                "packages/%s" % package.directory)
        if not history and not (force or version):
            skips.append(Skip(package.directory, package.name, tag, version_of(tag)))
            continue
        if version:
            check_forced(repo, package.name, tag, version)
            target = version
        else:
            target = next_version(repo, package.name)
        mismatches = [(c.subject, parsed.scope) for c in history
                      for parsed in [commitlib.parse(c.subject)]
                      if parsed and parsed.scope and parsed.scope != package.directory]
        plans.append(Plan(package.directory, package.name, tag, target, history,
                          mismatches, not history))
    return plans, skips


def line(p: Plan) -> str:
    """The one-line summary, shared so release.py and this CLI cannot diverge."""
    return "[release] %-18s %s -> %-10s (%d commit(s) since %s%s)" % (
        p.name, version_of(p.previous) or "unreleased", p.next, len(p.commits),
        p.previous or "the start", ", forced" if p.forced else "")


def report(plans: Sequence[Plan], skips: Sequence[Skip],
           out: TextIO | None = None) -> None:
    """Print every plan and skip, mismatches included, in discovery order."""
    out = out or sys.stdout
    for p in plans:
        print(line(p), file=out)
        for subject, scope in p.mismatches:
            print("          ! scope `%s` but the change is under packages/%s: %s"
                  % (scope, p.directory, subject[:60]), file=out)
    for s in skips:
        print("[skip]    %-18s no commits since %s" % (s.name, s.tag or "the start"),
              file=out)


def as_json(plans: Sequence[Plan], skips: Sequence[Skip]) -> dict:
    return {
        "releases": [{"package": p.directory, "name": p.name,
                      "previous": p.previous, "next": p.next,
                      "commits": len(p.commits),
                      "shas": [c.sha for c in p.commits],
                      "forced": p.forced,
                      "scope_mismatches": [{"subject": s, "scope": c}
                                           for s, c in p.mismatches]}
                     for p in plans],
        "skipped": [{"name": s.name, "since": s.tag, "version": s.version}
                    for s in skips],
    }


def main(repo: Path = workspace.REPO_OPTION,
         package: list[str] = typer.Option([], "--package",
                                           help="Report only these packages."),
         force: bool = typer.Option(False, "--force",
                                    help="Plan a --package with no commits: a re-release."),
         version: str = typer.Option("", "--version", metavar="YYYY.M.N",
                                     help="Release one --package at exactly this version. "
                                          "Must be unused and sort above its last tag."),
         json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
         no_fetch: bool = typer.Option(False, "--no-fetch",
                                       help="Skip `git fetch --tags`, for an offline clone.")) -> None:
    """Show what each package's next calendar version would be, and why."""
    try:
        plans, skips = plan(repo.resolve(), only=package, force=force,
                            version=version or None, fetch=not no_fetch)
    except WorkspaceError as exc:
        raise workspace.die(exc)
    if json_out:
        json.dump(as_json(plans, skips), sys.stdout, indent=2)
        print()
        return
    report(plans, skips)
    if not plans:
        print("\nnothing to release")


if __name__ == "__main__":
    typer.run(main)
