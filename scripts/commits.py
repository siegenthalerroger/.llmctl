"""The conventional-commit convention, parsed once.

Two consumers read commit subjects: the `commits` gate in check.py, which
refuses a subject that breaks the convention, and the release notes, which
group a package's commits by type. Sharing the parser is what keeps "what the
gate accepts" and "what the notes understand" the same set.

The type sizes nothing -- versions are calendar-derived -- so the allowlist is
purely about legible history and grouping. The scope rule is the useful half:
when a scope is given it has to name something the commit actually touched,
which is how a typo'd scope surfaces instead of quietly mislabelling history.
"""
from __future__ import annotations

import re
from collections import namedtuple
from pathlib import Path

from workspace import git

TYPES = ("feat", "fix", "docs", "refactor", "chore", "test", "build", "ci")

SUBJECT_RE = re.compile(
    r"^(?P<type>[a-z]+)(?:\((?P<scope>[^()\s]+)\))?(?P<bang>!)?: (?P<description>\S.*)$")

# Areas for paths outside packages/. A commit may name any one it touched.
AREAS = (
    ("scripts/", "scripts"),
    (".github/", "ci"),
    (".apm/", "meta"),
)
ROOT_CONFIG = ("apm.yml", "apm.lock.yaml", ".gitignore", "dependency-licenses.yml")

Subject = namedtuple("Subject", "type scope bang description")
Commit = namedtuple("Commit", "sha subject body")
Finding = namedtuple("Finding", "sha subject reason")


def parse(subject: str) -> Subject | None:
    m = SUBJECT_RE.match(subject.strip())
    if not m:
        return None
    return Subject(m.group("type"), m.group("scope"), bool(m.group("bang")),
                   m.group("description"))


def breaking(commit: Commit) -> bool:
    parsed = parse(commit.subject)
    return bool(parsed and parsed.bang) or "BREAKING CHANGE" in commit.body


def log(repo: Path | str, rng: str, path: str = "", merges: bool = False) -> list[Commit]:
    """(sha, subject, body) for every commit in `rng`, optionally under `path`."""
    args = ["log", "--format=%H%x1f%s%x1f%b%x1e"]
    if not merges:
        args.append("--no-merges")
    if rng:
        args.append(rng)
    if path:
        args += ["--", path]
    raw = git(args, repo)
    commits = []
    for chunk in raw.split("\x1e"):
        chunk = chunk.strip()
        if not chunk:
            continue
        sha, _, rest = chunk.partition("\x1f")
        subject, _, body = rest.partition("\x1f")
        commits.append(Commit(sha.strip(), subject.strip(), body.strip()))
    return commits


def touched(repo: Path | str, sha: str) -> list[str]:
    out = git(["show", "--name-only", "--format=", sha], repo)
    return [line.strip() for line in out.split("\n") if line.strip()]


def scopes_for(paths: list[str]) -> set[str]:
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
            if "/" not in path:
                if path.endswith(".md"):
                    scopes.add("docs")
                if path in ROOT_CONFIG or path.startswith("LICENSE") \
                        or ".marketplace." in path or path.endswith(".marketplace"):
                    scopes.add("repo")
            elif path.startswith("LICENSES/"):
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
    commits = log(repo, "%s..HEAD" % since)
    for commit in commits:
        reason = check_subject(commit.subject)
        if reason:
            findings.append(Finding(commit.sha, commit.subject, reason))
            continue
        scope = parse(commit.subject).scope
        if scope:
            allowed = scopes_for(touched(repo, commit.sha))
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
