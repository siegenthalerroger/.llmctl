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
"""What each package's next version would be, and why.

Split out of release.py so the question can be asked without answering it. This
reads tags and commit subjects and prints; it writes no file, cuts no tag and
opens nothing. release.py imports it rather than keeping a second copy, so the
number reported here is the number a release would publish -- a preview that
can disagree with the release is worse than no preview.

Versions are calendar-derived: `YYYY.M.N`, where N counts this package's
releases within the UTC month, from 1. No zero padding, so the string stays
semver-shaped for the hosts that parse it as one. A package is planned when the
paths under `packages/<dir>/` have commits since its last `<name>@<version>`
tag; nothing about a commit's type sizes anything. The commit scope is still
checked against the paths, and a mismatch is reported, so the convention stays
meaningful without being load-bearing.

Tags are the baseline, and they are read locally, so a clone fetched without
tags -- shallow, or --no-tags -- measures from nothing and every package plans
off its entire history. Hence the `git fetch --tags` below.

Usage:
  uv run scripts/versions.py --repo PATH [--package NAME]... [--force]
                             [--version YYYY.M.N] [--json] [--no-fetch]

  --package    report only these packages (repeatable)
  --force      plan the named packages even with no commits since their tag --
               a re-release. Requires --package
  --version    release exactly one --package at this version instead of the
               derived one. Must be YYYY.M.N, unused, and above the last tag
  --json       machine-readable, for a caller that wants the number
  --no-fetch   skip `git fetch --tags`, for an offline or read-only checkout

Exit codes: 0 reported (even when nothing would bump), 1 error.
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import namedtuple
from datetime import datetime, timezone
from pathlib import Path

import typer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import commits as commitlib  # noqa: E402
import workspace  # noqa: E402
from workspace import git  # noqa: E402

CALVER_RE = re.compile(r"^(?P<y>\d{4})\.(?P<m>\d{1,2})\.(?P<n>\d+)$")

# `mismatches` is [(subject, scope)] -- commits whose scope names a package
# other than the one whose paths they touched. `commits` is the list of
# commits.Commit records the release notes are built from.
Plan = namedtuple("Plan", "directory name previous next commits mismatches forced")
Skip = namedtuple("Skip", "directory name tag version")


def version_of(tag: str | None) -> str:
    return tag.partition("@")[2] if tag else ""


def version_key(version: str) -> tuple[int, ...]:
    """Numeric ordering for `a.b.c` strings of any length; suffixes ignored."""
    return tuple(int(re.sub(r"\D.*$", "", p) or 0) for p in version.split("."))


def last_tag(repo, name: str) -> str | None:
    """Newest `<name>@<version>` tag by version order, or None."""
    out = git(["tag", "--list", "%s@*" % name, "--sort=-v:refname"], repo)
    return out.split("\n")[0] if out else None


def next_version(repo, name: str, now: datetime | None = None) -> str:
    now = now or datetime.now(timezone.utc)
    prefix = "%d.%d." % (now.year, now.month)
    tags = git(["tag", "--list", "%s@%s*" % (name, prefix)], repo).split()
    highest = 0
    for tag in tags:
        m = CALVER_RE.match(version_of(tag))
        if m:
            highest = max(highest, int(m.group("n")))
    return "%s%d" % (prefix, highest + 1)


def check_forced(repo, name: str, previous: str | None, version: str) -> None:
    """Refuse a forced version the next run could not measure from."""
    if not CALVER_RE.match(version):
        sys.stderr.write("--version %r is not YYYY.M.N\n" % version)
        raise SystemExit(1)
    if git(["tag", "--list", "%s@%s" % (name, version)], repo):
        sys.stderr.write("%s@%s already exists\n" % (name, version))
        raise SystemExit(1)
    if previous and version_key(version) <= version_key(version_of(previous)):
        sys.stderr.write("--version %s does not sort above %s; the highest tag is "
                         "the baseline, so a lower one would never be measured "
                         "from\n" % (version, previous))
        raise SystemExit(1)


def plan(repo, only=(), force: bool = False, version: str | None = None,
         fetch: bool = True) -> tuple[list[Plan], list[Skip]]:
    """(plans, skips) for every package, in discovery order."""
    repo = Path(repo)
    packages = workspace.packages(repo)
    if only:
        wanted = set(only)
        packages = [p for p in packages if p.directory in wanted or p.name in wanted]
        if not packages:
            sys.stderr.write("no package matched %s\n" % ", ".join(sorted(wanted)))
            raise SystemExit(1)
    if (force or version) and not only:
        sys.stderr.write("--force/--version need --package to say which\n")
        raise SystemExit(1)
    if version and len(packages) != 1:
        sys.stderr.write("--version applies to exactly one --package\n")
        raise SystemExit(1)

    if fetch:
        # Tags are the baseline for every plan below, and they live on the
        # remote. Without this a fresh clone sees none and reads the whole
        # history instead.
        git(["fetch", "--tags", "origin"], repo, check=False)

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
        mismatches = []
        for commit in history:
            parsed = commitlib.parse(commit.subject)
            if parsed and parsed.scope and parsed.scope != package.directory:
                mismatches.append((commit.subject, parsed.scope))
        plans.append(Plan(package.directory, package.name, tag, target, history,
                          mismatches, not history))
    return plans, skips


def line(p: Plan) -> str:
    """The one-line summary, shared so release.py and this CLI cannot diverge."""
    return "[release] %-18s %s -> %-10s (%d commit(s) since %s%s)" % (
        p.name, version_of(p.previous) or "unreleased", p.next, len(p.commits),
        p.previous or "the start", ", forced" if p.forced else "")


def skip_line(s: Skip) -> str:
    return "[skip]    %-18s no commits since %s" % (s.name, s.tag or "the start")


def mismatch_lines(p: Plan) -> list[str]:
    return ["          ! scope `%s` but the change is under packages/%s: %s"
            % (scope, p.directory, subject[:60]) for subject, scope in p.mismatches]


def report(plans, skips, out=None) -> None:
    """Print every plan and skip, mismatches included, in discovery order."""
    out = out or sys.stdout
    for p in plans:
        print(line(p), file=out)
        for warning in mismatch_lines(p):
            print(warning, file=out)
    for s in skips:
        print(skip_line(s), file=out)


def as_json(plans, skips) -> dict:
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
         package: list[str] = typer.Option([], "--package", help="only these packages"),
         force: bool = typer.Option(False, "--force", help="plan even without commits"),
         version: str = typer.Option("", "--version", help="release at this YYYY.M.N"),
         json_out: bool = typer.Option(False, "--json"),
         no_fetch: bool = typer.Option(False, "--no-fetch")) -> None:
    plans, skips = plan(repo.resolve(), only=package, force=force,
                        version=version or None, fetch=not no_fetch)
    if json_out:
        json.dump(as_json(plans, skips), sys.stdout, indent=2)
        print()
        return
    report(plans, skips)
    if not plans:
        print("\nnothing to release")


if __name__ == "__main__":
    typer.run(main)
