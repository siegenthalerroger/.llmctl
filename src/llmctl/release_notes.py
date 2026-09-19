"""Release notes for one package, from its commits and the pull requests behind them.

The commits say what changed, grouped by conventional-commit type -- the whole job
the type still does now that it sizes no version. The pull request says why, in the
section under its `## Release notes` heading, and only that section, so review
chatter stays out. A commit with neither contributes its subject line.
"""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

from . import commits as commitlib
from .workspace import Log

if TYPE_CHECKING:
    from github import GitHub
    from versions import Plan

__all__ = ["GROUPS", "build", "extract_release_notes", "group_of",
           "pull_request_sections"]

# Ordered, because the order is the message: what breaks, then what is new,
# then what is fixed, then everything else.
GROUPS = (
    ("breaking", "Breaking changes"),
    ("feat", "Features"),
    ("fix", "Fixes"),
    ("docs", "Documentation"),
    ("other", "Other changes"),
)

SECTION_RE = re.compile(r"(?mis)^##\s+release\s+notes\s*$\n(.*?)(?=^##\s|\Z)")


def extract_release_notes(body: str) -> str:
    """The `## Release notes` section of a pull request body, or ""."""
    match = SECTION_RE.search(body or "")
    return match.group(1).strip() if match else ""


def group_of(commit: commitlib.Commit) -> str:
    if commitlib.breaking(commit):
        return "breaking"
    parsed = commitlib.parse(commit.subject)
    if parsed and parsed.type in ("feat", "fix", "docs"):
        return parsed.type
    return "other"


def build(plan: Plan, owner: str = "", repo: str = "",
          client: GitHub | None = None, log: Log = print,
          cache: dict[str, list[dict]] | None = None) -> str:
    """The notes body for one release plan.

    `client` is optional: without a token there is no pull request lookup, so
    the notes are the commit list alone rather than nothing. `cache` is shared
    across the packages of one release, because a commit touching two of them
    is one pull request, not two lookups.
    """
    lines = []
    since = plan.previous or "the start of the package"
    lines.append("Commits in `packages/%s` since %s." % (plan.directory, since))
    lines.append("")

    grouped = {key: [] for key, _ in GROUPS}
    for commit in plan.commits:
        grouped[group_of(commit)].append(commit)
    for key, heading in GROUPS:
        if not grouped[key]:
            continue
        lines.append("### %s" % heading)
        lines.append("")
        for commit in grouped[key]:
            lines.append("- %s (`%s`)" % (commit.subject, commit.sha[:7]))
        lines.append("")

    sections = pull_request_sections(plan, owner, repo, client, log=log, cache=cache)
    if sections:
        lines.append("## Release notes")
        lines.append("")
        for number, title, text in sections:
            lines.append("### #%d %s" % (number, title))
            lines.append("")
            lines.append(text)
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def pull_request_sections(plan: Plan, owner: str, repo: str,
                          client: GitHub | None, log: Log = print,
                          cache: dict[str, list[dict]] | None = None
                          ) -> list[tuple[int, str, str]]:
    """(number, title, text) for every distinct PR behind these commits that
    carries a `## Release notes` section."""
    if not client or not owner or not repo:
        return []
    cache = {} if cache is None else cache
    seen, sections = set(), []
    for commit in plan.commits:
        if commit.sha in cache:
            pulls = cache[commit.sha]
        else:
            try:
                pulls = client.pulls_for_commit(owner, repo, commit.sha)
            except Exception as exc:                   # notes must not fail a release
                log("[notes] could not read pull requests for %s: %s"
                    % (commit.sha[:7], exc))
                pulls = []
            cache[commit.sha] = pulls
        for pull in pulls:
            number = pull.get("number")
            if number in seen:
                continue
            seen.add(number)
            text = extract_release_notes(pull.get("body") or "")
            if text:
                sections.append((number, str(pull.get("title") or ""), text))
    return sections
