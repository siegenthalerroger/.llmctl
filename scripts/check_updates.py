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
"""Audit the upstreams this repo copies from, rather than depends on. Writes nothing.

Two modes over `metadata.provenance`: `adaptedFrom` (content adapted from an
upstream file, dated from its commits) and `--specs` for `authoritativeSpec`
(mostly vendor docs, which have no history, so a dead link and `Last-Modified`
are all HTTP can answer). Pinned APM dependencies are update.py's half.
The statuses and what to do about each are in the meta-update-repo skill.

A fetch failure is a row, never an exit code: a rate limit on one upstream must
not discard the other twenty-seven answers.
"""
from __future__ import annotations

import fnmatch
import json
import os
import sys
import urllib.parse
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NamedTuple

import httpx
import typer

import github as githublib
import provenance as prov
import workspace
from github import ApiError

# The audit's own vocabulary. `Item` is one tracked upstream of one file, `Row`
# is that item plus a verdict -- both are the JSON this prints, so they stay
# dicts; `Query` and `Options` never leave the process, so they do not.
Item = dict[str, str]
Row = dict[str, Any]


class Query(NamedTuple):
    """A GitHub URL taken apart into what the API asks for."""

    owner: str
    repo: str
    ref: str
    path: str


class Options(NamedTuple):
    """What the caller asked for, as every audit function reads it."""

    change_details: bool
    max_change_commits: int
    allow_no_local_commit: bool

# A source with no revision history to diff against -- a book, a paper, a vendor
# doc page. A permanent property of the URL rather than a failure, so it is kept
# out of the failure count: filing these as failures parks unfixable rows in the
# audit, which is how an audit stops being read.
NOT_TRACKABLE = "not_trackable"


def is_github(url: str) -> bool:
    try:
        return urllib.parse.urlparse(url).hostname == "github.com"
    except ValueError:
        return False


def github_query(url: str) -> Query:
    """A repository, tree, or blob URL taken apart."""
    parts = urllib.parse.urlparse(url)
    segments = [s for s in parts.path.strip("/").split("/") if s]
    if len(segments) < 2:
        raise ApiError("Invalid GitHub URL path: '%s'" % url)
    owner, repo = segments[0], segments[1]
    if len(segments) == 2:
        # A bare repository URL names no branch. Leaving the ref empty lets the
        # API use the repository's own default; hardcoding `main` 404s on every
        # repo still using `master`, which reads like a broken URL.
        return Query(owner, repo, "", "")
    if len(segments) >= 4 and segments[2] in ("blob", "tree"):
        return Query(owner, repo, segments[3], "/".join(segments[4:]))
    raise ApiError("Unsupported GitHub URL structure: '%s'. Use repository, tree, "
                   "or blob URLs." % url)


def probe(url: str) -> httpx.Response:
    """HEAD (falling back to GET) an arbitrary URL, for the spec audit."""
    headers = {"User-Agent": githublib.USER_AGENT}
    try:
        response = httpx.head(url, follow_redirects=True, timeout=30.0, headers=headers)
        if response.status_code in (405, 501):
            response = httpx.get(url, follow_redirects=True, timeout=30.0, headers=headers)
        return response
    except httpx.HTTPError as exc:
        raise ApiError("request failed: %s" % exc)


def last_commit(repo: Path | str, path: str) -> dict[str, str]:
    """The local file's last commit, or empty strings when it has none."""
    out = workspace.git(["log", "-n", "1", "--format=%H|%cI", "--", str(path)],
                        repo, check=False)
    sha, _, date = out.partition("|")
    return {"sha": sha, "date": date}


def tracked_entries(root: Path, kind: str) -> list[dict]:
    """One record per upstream URL of `kind`, across every customization file."""
    entries = []
    for path in prov.iter_files(root):
        if not prov.is_customization(path):
            continue
        record = prov.parse(path)
        relative = os.path.relpath(path, root).replace("\\", "/")
        for entry in record.entries:
            if entry.kind == kind:
                entries.append({"file": relative, "source": entry.url,
                                "took": entry.took or "",
                                "license": entry.license or "",
                                "fidelity": entry.fidelity or ""})
    return entries


def row(item: Item, status: str, recommendation: str, reason: str,
        local: dict[str, str] | None = None,
        upstream: dict[str, str] | None = None, days: int | None = None,
        commits: list[dict] | None = None) -> Row:
    return dict(item, status=status, recommendation=recommendation, reason=reason,
                local=local or {"sha": "", "date": ""},
                upstream=upstream or {"sha": "", "date": ""},
                days_behind=days, commits=commits or [])


def audit_adapted(item: Item, root: Path, client: githublib.GitHub,
                  options: Options) -> Row:
    """Has the upstream file moved since the local one last did?"""
    if not is_github(item["source"]):
        return row(item, NOT_TRACKABLE, "none_source_has_no_revision_history",
                   "source_host_is_not_revision_controlled")

    local = last_commit(root, item["file"])
    bootstrap = not local["date"]
    if bootstrap and not options.allow_no_local_commit:
        return row(item, "missing_local_commit", "commit_local_file_first",
                   "local_file_not_in_git_history", local)

    try:
        query = github_query(item["source"])
        # Before any date comparison: a path that no longer exists still has a
        # newest commit -- the one that removed it -- and would report healthy.
        if not client.path_exists(query.owner, query.repo, query.path, query.ref):
            return row(item, "source_missing", "repoint_or_drop_provenance",
                       "upstream_path_no_longer_exists", local)
        head = client.latest_commit(query.owner, query.repo, query.path, query.ref)
        upstream = {"sha": head["commitSha"], "date": head["commitDate"]}
    except ApiError as exc:
        return row(item, "fetch_failed", "check_source_url", str(exc), local)

    if bootstrap:
        return row(item, "update_available", "bootstrap_review_and_merge_from_upstream",
                   "local_file_not_in_git_history_bootstrap_allowed", local, upstream,
                   commits=changes(client, query, options))

    local_date = githublib.parse_date(local["date"])
    upstream_date = githublib.parse_date(upstream["date"])
    days = round((upstream_date - local_date).total_seconds() / 86400.0, 3)
    if local_date >= upstream_date:
        return row(item, "up_to_date", "none",
                   "local_commit_date_is_not_older_than_upstream", local, upstream, days)
    return row(item, "update_available", "review_and_merge_from_upstream",
               "upstream_commit_newer_than_local_commit", local, upstream, days,
               changes(client, query, options, since=local_date))


def audit_spec(item: Item, root: Path, client: githublib.GitHub,
               options: Options) -> Row:
    """Is the specification still there, and has it moved since we read it?"""
    if is_github(item["source"]):
        return audit_adapted(item, root, client, options)

    local = last_commit(root, item["file"])
    try:
        response = probe(item["source"])
    except ApiError as exc:
        return row(item, "fetch_failed", "check_source_url", str(exc), local)

    if response.status_code >= 400:
        return row(item, "source_missing", "repoint_or_drop_provenance",
                   "http_%d" % response.status_code, local)

    modified = response.headers.get("Last-Modified")
    if not modified or not local["date"]:
        return row(item, NOT_TRACKABLE, "none_source_reports_no_date",
                   "no_last_modified_header" if not modified
                   else "local_file_not_in_git_history", local)
    try:
        upstream_date = datetime.strptime(modified, "%a, %d %b %Y %H:%M:%S %Z") \
            .replace(tzinfo=timezone.utc)
    except ValueError:
        return row(item, NOT_TRACKABLE, "none_source_reports_no_date",
                   "unparsable_last_modified", local)

    local_date = githublib.parse_date(local["date"])
    upstream = {"sha": "", "date": upstream_date.isoformat()}
    days = round((upstream_date - local_date).total_seconds() / 86400.0, 3)
    if local_date >= upstream_date:
        return row(item, "up_to_date", "none", "page_not_modified_since_local_commit",
                   local, upstream, days)
    return row(item, "update_available", "read_the_page_and_check_our_claims",
               "page_modified_since_local_commit", local, upstream, days)


def changes(client: githublib.GitHub, query: Query, options: Options,
            since: str | None = None) -> list[dict]:
    """Upstream commit rows, when --change-details asked for them."""
    if not options.change_details:
        return []
    try:
        return client.commit_rows(query.owner, query.repo, query.path,
                                  query.ref, options.max_change_commits, since)
    except ApiError as exc:
        return [{"error": str(exc)}]


def summarize(results: Sequence[Row]) -> dict[str, int]:
    def count(status: str) -> int:
        return sum(1 for r in results if r["status"] == status)
    return {
        "files": len({r["file"] for r in results}),
        "upstreams": len(results),
        "up_to_date": count("up_to_date"),
        "update_available": count("update_available"),
        "source_missing": count("source_missing"),
        "not_trackable": count(NOT_TRACKABLE),
        "failed": count("fetch_failed") + count("missing_local_commit"),
    }


def report(output: dict[str, Any]) -> None:
    s = output["summary"]
    print("Upstream audit complete (%s)" % output["mode"])
    print("Auth: %s | Files: %d | Upstreams: %d | Up-to-date: %d | Update-available: "
          "%d | Source-missing: %d | Not-trackable: %d | Failed: %d"
          % (output["auth"], s["files"], s["upstreams"], s["up_to_date"],
             s["update_available"], s["source_missing"], s["not_trackable"], s["failed"]))
    if output["auth"] == "unauthenticated":
        print("Tip: run 'gh auth login' (or set GITHUB_TOKEN/GH_TOKEN, or pass "
              "--github-token) to avoid GitHub API rate-limit 403 errors.")
    for result in output["results"]:
        extra = (" | %d upstream commit(s) since local" % len(result["commits"])
                 if result["commits"] else "")
        print("[%s] %s <- %s | %s%s | recommendation: %s"
              % (result["status"], result["file"], result["source"],
                 result["reason"], extra, result["recommendation"]))


def main(repo: Path = workspace.REPO_OPTION,
         specs: bool = typer.Option(False, "--specs",
                                    help="Audit authoritativeSpec sources instead of adaptedFrom."),
         include: str = typer.Option("", "--include", metavar="GLOB",
                                     help="Only files matching this workspace-relative glob. "
                                          "`*` spans `/`; case-sensitive."),
         json_out: bool = typer.Option(False, "--json", help="Machine-readable output."),
         change_details: bool = typer.Option(False, "--change-details",
                                             help="Also collect the upstream commits behind a change."),
         max_change_commits: int = typer.Option(5, "--max-change-commits", min=1, max=100,
                                                help="Cap that payload."),
         allow_no_local_commit: bool = typer.Option(False, "--allow-no-local-commit",
                                                    help="Treat an uncommitted local file as a "
                                                         "bootstrap candidate rather than an error."),
         github_token: str = typer.Option("", "--github-token",
                                          help="Overrides GITHUB_TOKEN / GH_TOKEN / `gh auth token`.")) -> None:
    """Audit adapted files and cited specifications for upstream drift."""
    root = repo.resolve()
    token = githublib.token(github_token)
    client = githublib.GitHub(token)

    kind = "authoritativeSpec" if specs else "adaptedFrom"
    items = tracked_entries(root, kind)
    if include:
        items = [i for i in items if fnmatch.fnmatchcase(i["file"], include)]
    if not items:
        sys.stderr.write("no %s sources found%s.\n"
                         % (kind, " for --include '%s'" % include if include else ""))
        raise typer.Exit(1)

    options = Options(change_details, max_change_commits, allow_no_local_commit)
    auditor = audit_spec if specs else audit_adapted
    results = [auditor(item, root, client, options) for item in items]

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repo": str(root),
        "mode": kind,
        "include": include,
        "auth": "token" if token else "unauthenticated",
        "summary": summarize(results),
        "results": results,
    }
    if json_out:
        print(json.dumps(output, indent=2))
    else:
        report(output)


if __name__ == "__main__":
    typer.run(main)
