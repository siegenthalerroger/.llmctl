"""The conventional-commit convention, parsed once.

The `commits` gate refuses a subject that breaks it; the release notes group a
package's commits by type. Sharing the parser is what keeps "what the gate
accepts" and "what the notes understand" the same set. The rules themselves are
in CONTRIBUTING.md#commit-convention.
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path
from typing import NamedTuple

from .workspace import git

__all__ = ["AREAS", "Commit", "Finding", "Subject", "TYPES", "breaking",
           "lint", "log", "parse", "scopes_for"]

TYPES = ("feat", "fix", "docs", "refactor", "chore", "test", "build", "ci")

SUBJECT_RE = re.compile(
    r"^(?P<type>[a-z]+)(?:\((?P<scope>[^()\s]+)\))?(?P<bang>!)?: (?P<description>\S.*)$")

# Which scope a path outside packages/ may be named by, first match winning.
# A package path names its own directory instead, which `scopes_for` handles.
AREAS = (
    ("src/", "tooling"),
    ("pyproject.toml", "tooling"),
    ("uv.lock", "tooling"),
    (".github/", "ci"),
    (".apm/", "meta"),
    ("LICENSES/", "repo"),
)
ROOT_CONFIG = ("apm.yml", "apm.lock.yaml", ".gitignore", "dependency-licenses.yml")

class Subject(NamedTuple):
    """A conventional-commit subject line, taken apart."""

    type: str
    scope: str | None
    bang: bool
    description: str


class Commit(NamedTuple):
    """One commit. `paths` is empty unless the caller asked for it."""

    sha: str
    subject: str
    body: str
    paths: tuple[str, ...]


class Finding(NamedTuple):
    """One commit the convention rejects, and why."""

    sha: str
    subject: str
    reason: str

RECORD, FIELD = "\x1e", "\x1f"


def parse(subject: str) -> Subject | None:
    m = SUBJECT_RE.match(subject.strip())
    if not m:
        return None
    return Subject(m.group("type"), m.group("scope"), bool(m.group("bang")),
                   m.group("description"))


def breaking(commit: Commit) -> bool:
    parsed = parse(commit.subject)
    return bool(parsed and parsed.bang) or "BREAKING CHANGE" in commit.body


def log(repo: Path | str, rng: str, path: str = "", *, paths: bool = False,
        merges: bool = False) -> list[Commit]:
    """Every commit in `rng`, optionally under `path`, newest first.

    `paths=True` also fills each commit's touched files, in the same `git log`
    rather than a `git show` per commit.
    """
    args = ["log", "--format=%s%%H%s%%s%s%%b%s" % (RECORD, FIELD, FIELD, FIELD)]
    if not merges:
        args.append("--no-merges")
    if paths:
        args.append("--name-only")
    if rng:
        args.append(rng)
    if path:
        args += ["--", path]

    commits = []
    for chunk in git(args, repo).split(RECORD):
        if not chunk.strip():
            continue
        sha, subject, body, touched = (chunk.split(FIELD) + ["", "", ""])[:4]
        commits.append(Commit(
            sha.strip(), subject.strip(), body.strip(),
            tuple(line.strip() for line in touched.split("\n") if line.strip())))
    return commits


def scopes_for(paths: Iterable[str]) -> set[str]:
    """Every scope a commit touching `paths` may legitimately carry."""
    scopes = set()
    for path in paths:
        path = path.replace("\\", "/")
        if path.startswith("packages/"):
            parts = path.split("/")
            if len(parts) > 1 and parts[1]:
                scopes.add(parts[1])
            continue
        for prefix, area in AREAS:
            if path.startswith(prefix):
                scopes.add(area)
                break
        else:
            if "/" in path:
                continue
            if path.endswith(".md"):
                scopes.add("docs")
            if path in ROOT_CONFIG or path.startswith("LICENSE") \
                    or ".marketplace." in path or path.endswith(".marketplace"):
                scopes.add("repo")
    return scopes


def check_subject(subject: str) -> str | None:
    """The reason a subject breaks the convention, or None."""
    parsed = parse(subject)
    if not parsed:
        return "not `<type>(<scope>): <description>`"
    if parsed.type not in TYPES:
        return "unknown type `%s` (allowed: %s)" % (parsed.type, " ".join(TYPES))
    return None


def lint(repo: Path | str, since: str, subject: str | None = None) -> tuple[int, list[Finding]]:
    """(commits checked, findings) for `since..HEAD`, plus an optional extra subject."""
    findings = []
    commits = log(repo, "%s..HEAD" % since, paths=True)
    for commit in commits:
        reason = check_subject(commit.subject)
        if reason:
            findings.append(Finding(commit.sha, commit.subject, reason))
            continue
        scope = parse(commit.subject).scope
        if not scope:
            continue
        allowed = scopes_for(commit.paths)
        if scope not in allowed:
            findings.append(Finding(
                commit.sha, commit.subject,
                "scope `%s` names nothing this commit touched (%s)"
                % (scope, ", ".join(sorted(allowed)) or "no scope applies")))
    if subject:
        reason = check_subject(subject)
        if reason:
            findings.append(Finding("subject", subject, reason))
    return len(commits), findings
