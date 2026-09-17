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
"""Audit this repository's upstream inputs for drift. Writes nothing.

Three modes, one per kind of upstream the repo depends on. The meta-update-repo
skill drives all three; the output is the audit.

  (default)   `metadata.provenance.adaptedFrom` -- content adapted from an
              upstream file. Compares the local file's last commit date against
              the upstream's latest commit for that path.

                up_to_date            local commit is not older than upstream
                update_available      upstream moved since the local file did
                source_missing        the upstream path is gone. `/commits?path=`
                                      happily returns the commit that *deleted*
                                      a path, so a date comparison alone reports
                                      a dead upstream as healthy forever
                missing_local_commit  the local file is not in git history yet
                                      (--allow-no-local-commit treats it as a
                                      bootstrap candidate)
                fetch_failed          the upstream could not be read
                not_trackable         the source has no revision history to diff
                                      against -- a book, a paper, a vendor doc
                                      page. A permanent property of the URL, not
                                      a failure, so it is kept out of the failure
                                      count: filing these as `fetch_failed` parks
                                      unfixable rows in the audit, which is how
                                      an audit stops being read

  --specs     `metadata.provenance.authoritativeSpec` -- the specifications a
              file's format claims to conform to. Mostly vendor documentation,
              so there is no commit history to read: a GitHub URL goes through
              the path above, anything else is probed for a dead link and for a
              `Last-Modified` newer than the local file's last commit. No hashes
              are stored anywhere; a doc site rebuild would churn them and the
              judgement of whether a spec change matters is not a hash's to make

  --compare   the upstream diff behind a pin that moved in the working tree but
              is not committed yet. For each dependency whose `#sha` in
              packages/<dir>/apm.yml differs from the one at HEAD, print the
              upstream's own compare, filtered to the path this repo consumes.
              This is what the safety review reads before a bump is committed

Frontmatter is parsed by provenance.py, the same module check_licenses.py and
gen_notices.py use, and the file walk is that module's too. Sharing both is the
point: this audit and the licence gate have to agree on what is tracked, and an
entry that silently stops being tracked produces no error anywhere -- it just
quietly leaves the audit.

Usage:
  uv run scripts/check_updates.py --repo PATH [options]

  --repo                    workspace to audit (default: the enclosing git repo).
                            Optional, unlike the release scripts' --repo: this
                            one is run by hand from a repo root far more often
                            than it is wired into anything
  --include GLOB            only paths matching this workspace-relative glob.
                            `*` spans `/`, so a trailing fragment is usually the
                            shortest correct filter. Case-sensitive
  --json                    machine-readable output
  --change-details          also collect commit-level upstream changes
  --max-change-commits N    cap that payload (1-100, default 5)
  --allow-no-local-commit   treat an uncommitted local file as a bootstrap
                            candidate rather than an error
  --github-token TOKEN      overrides GITHUB_TOKEN / GH_TOKEN / `gh auth token`

Exit codes: 0 the audit ran, 1 nothing was tracked or the repo could not be found.
Individual fetch failures are rows in the output, not exit codes -- a rate limit
on one upstream must not discard the other twenty-seven answers.
"""
from __future__ import annotations

import fnmatch
import json
import os
import subprocess
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import typer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import github as githublib  # noqa: E402
import provenance as prov  # noqa: E402
import workspace  # noqa: E402
from github import ApiError  # noqa: E402


# --- Source URLs -----------------------------------------------------------


def is_github(url: str) -> bool:
    try:
        return urllib.parse.urlparse(url).hostname == "github.com"
    except ValueError:
        return False


def github_query(url: str) -> dict:
    """(owner, repo, ref, path) from a repository, tree, or blob URL."""
    parts = urllib.parse.urlparse(url)
    if parts.hostname != "github.com":
        raise ApiError("Unsupported source host '%s'. Only github.com URLs are "
                       "supported." % parts.hostname)
    segments = [s for s in parts.path.strip("/").split("/") if s]
    if len(segments) < 2:
        raise ApiError("Invalid GitHub URL path: '%s'" % url)
    owner, repo = segments[0], segments[1]
    if len(segments) == 2:
        # A bare repository URL names no branch, so leave the ref empty and let
        # the API fall back to the repository's own default. Hardcoding 'main'
        # 404s on every repo still using 'master' or a custom default -- and a
        # 404 reports as `fetch_failed`, which reads like a broken URL rather
        # than a wrong assumption on our side.
        return {"owner": owner, "repo": repo, "ref": "", "path": ""}
    if len(segments) >= 4 and segments[2] in ("blob", "tree"):
        return {"owner": owner, "repo": repo, "ref": segments[3],
                "path": "/".join(segments[4:])}
    raise ApiError("Unsupported GitHub URL structure: '%s'. Use repository, "
                   "tree, or blob URLs." % url)


# --- Local state -----------------------------------------------------------


def git_log(repo, path) -> dict:
    """The local file's last commit, or empty strings when it has none."""
    out = workspace.git(["log", "-n", "1", "--format=%H|%cI", "--", str(path)],
                        repo, check=False)
    if not out:
        return {"commitSha": "", "commitDate": ""}
    sha, _, date = out.partition("|")
    return {"commitSha": sha, "commitDate": date}


def repo_root(hint: str) -> Path:
    if hint and os.path.isdir(hint):
        return Path(hint).resolve()
    got = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                         capture_output=True, text=True)
    if got.returncode == 0 and got.stdout.strip():
        return Path(got.stdout.strip())
    sys.stderr.write("unable to determine the git repository root -- run from a "
                     "git repo or pass --repo\n")
    raise SystemExit(1)


def tracked_entries(root: Path, kind: str) -> list[dict]:
    """One record per upstream URL of `kind`, across every customization file."""
    entries = []
    for path in prov.iter_files(root):
        if not prov.is_customization(path):
            continue
        record = prov.parse(path)
        relative = os.path.relpath(path, root).replace("\\", "/")
        for entry in record["entries"]:
            if entry["kind"] != kind:
                continue
            entries.append({
                "id": relative,
                "localPath": relative,
                "sourceUrl": entry["url"],
                "took": entry["took"] or "",
                "license": entry["license"] or "",
                "fidelity": entry["fidelity"] or "",
            })
    return entries


# --- The audit -------------------------------------------------------------


def no_changes() -> dict:
    return {"collected": False, "commitCount": 0, "commits": []}


def row(item, status, recommendation, recommend, reason, local=None,
        upstream=None, changes=None, older=None, delta=None) -> dict:
    return {
        "id": item["id"],
        "localPath": item["localPath"],
        "sourceUrl": item["sourceUrl"],
        "took": item["took"],
        "license": item["license"],
        "fidelity": item["fidelity"],
        "status": status,
        "recommendation": recommendation,
        "recommendUpdate": recommend,
        "reason": reason,
        "localGit": local or {"commitSha": "", "commitDate": ""},
        "upstream": upstream or {"commitSha": "", "commitDate": ""},
        "upstreamChanges": changes or no_changes(),
        "comparison": {"localIsOlder": older, "deltaDays": delta},
    }


def collect_changes(client, query, max_commits, since=None) -> dict:
    commits = client.commit_rows(query["owner"], query["repo"], query["path"],
                                 query["ref"], max_commits, since)
    payload = {"collected": True, "commitCount": len(commits), "commits": commits}
    if since is not None:
        payload["since"] = since.astimezone(timezone.utc).isoformat()
    return payload


def audit_adapted(item, root, client, options) -> dict:
    if not is_github(item["sourceUrl"]):
        return row(item, "not_trackable", "none_source_has_no_revision_history",
                   False, "source_host_is_not_revision_controlled")

    local = git_log(root, item["localPath"])
    bootstrap = not local["commitDate"]
    if bootstrap and not options["allow_no_local_commit"]:
        return row(item, "missing_local_commit", "commit_local_file_first",
                   False, "local_file_not_in_git_history", local)

    try:
        query = github_query(item["sourceUrl"])
        # Before any date comparison: a path that no longer exists still has a
        # newest commit -- the one that removed it -- and would report healthy.
        if not client.path_exists(query["owner"], query["repo"], query["path"],
                                  query["ref"]):
            return row(item, "source_missing", "repoint_or_drop_provenance", False,
                       "upstream_path_no_longer_exists", local)
        upstream = client.latest_commit(query["owner"], query["repo"],
                                        query["path"], query["ref"])
        changes = no_changes()
        if options["change_details"] and bootstrap:
            changes = collect_changes(client, query, options["max_change_commits"])
    except ApiError as exc:
        return row(item, "fetch_failed", "check_source_url", False, str(exc), local)

    if bootstrap:
        return row(item, "update_available",
                   "bootstrap_review_and_merge_from_upstream", True,
                   "local_file_not_in_git_history_bootstrap_allowed", local,
                   upstream, changes)

    local_date = githublib.parse_date(local["commitDate"])
    upstream_date = githublib.parse_date(upstream["commitDate"])
    older = local_date < upstream_date
    delta = round((upstream_date - local_date).total_seconds() / 86400.0, 3)

    if not older:
        return row(item, "up_to_date", "none", False,
                   "local_commit_date_is_not_older_than_upstream", local,
                   upstream, None, older, delta)

    changes = no_changes()
    if options["change_details"]:
        try:
            changes = collect_changes(client, query, options["max_change_commits"],
                                      since=local_date)
        except ApiError as exc:
            changes = {"collected": False, "commitCount": 0, "commits": [],
                       "error": str(exc)}
    return row(item, "update_available", "review_and_merge_from_upstream", True,
               "upstream_commit_newer_than_local_commit", local, upstream,
               changes, older, delta)


def audit_spec(item, root, client, options) -> dict:
    """A specification source: is it still there, and has it moved since we read it?

    Vendor documentation has no commit history, so the question is answered from
    what HTTP will say -- the link resolves, and `Last-Modified` against the
    local file's last commit. A site that reports no date is `not_trackable`,
    which is the honest answer rather than a hash that churns on every rebuild.
    """
    if is_github(item["sourceUrl"]):
        return audit_adapted(item, root, client, options)

    local = git_log(root, item["localPath"])
    try:
        response = client.head(item["sourceUrl"])
    except ApiError as exc:
        return row(item, "fetch_failed", "check_source_url", False, str(exc), local)

    if response.status_code >= 400:
        return row(item, "source_missing", "repoint_or_drop_provenance", False,
                   "http_%d" % response.status_code, local)

    modified = response.headers.get("Last-Modified")
    if not modified or not local["commitDate"]:
        return row(item, "not_trackable", "none_source_reports_no_date", False,
                   "no_last_modified_header" if not modified
                   else "local_file_not_in_git_history", local)
    try:
        upstream_date = datetime.strptime(modified, "%a, %d %b %Y %H:%M:%S %Z") \
            .replace(tzinfo=timezone.utc)
    except ValueError:
        return row(item, "not_trackable", "none_source_reports_no_date", False,
                   "unparsable_last_modified", local)

    local_date = githublib.parse_date(local["commitDate"])
    older = local_date < upstream_date
    delta = round((upstream_date - local_date).total_seconds() / 86400.0, 3)
    upstream = {"commitSha": "", "commitDate": upstream_date.isoformat()}
    if not older:
        return row(item, "up_to_date", "none", False,
                   "page_not_modified_since_local_commit", local, upstream,
                   None, older, delta)
    return row(item, "update_available", "read_the_page_and_check_our_claims", True,
               "page_modified_since_local_commit", local, upstream, None, older, delta)


def summarize(results) -> dict:
    def count(predicate):
        return sum(1 for r in results if predicate(r))
    return {
        "filesChecked": len({r["localPath"] for r in results}),
        "upstreamChecks": len(results),
        "upToDateCount": count(lambda r: r["status"] == "up_to_date"),
        "updateAvailableCount": count(lambda r: r["status"] == "update_available"),
        "sourceMissingCount": count(lambda r: r["status"] == "source_missing"),
        "failedCount": count(lambda r: r["status"] in ("fetch_failed",
                                                       "missing_local_commit")),
        "notTrackableCount": count(lambda r: r["status"] == "not_trackable"),
        "recommendCount": count(lambda r: r["recommendUpdate"]),
    }


def report(output, change_details: bool) -> None:
    summary = output["summary"]
    print("Upstream audit complete (%s)" % output["mode"])
    print("Auth: %s | Files: %d | Upstreams: %d | Up-to-date: %d | "
          "Update-available: %d | Source-missing: %d | Failed: %d | "
          "Not-trackable: %d | Recommend: %d"
          % (output["authMode"], summary["filesChecked"], summary["upstreamChecks"],
             summary["upToDateCount"], summary["updateAvailableCount"],
             summary["sourceMissingCount"], summary["failedCount"],
             summary["notTrackableCount"], summary["recommendCount"]))
    if output["authMode"] == "unauthenticated":
        print("Tip: run 'gh auth login' (or set GITHUB_TOKEN/GH_TOKEN, or pass "
              "--github-token) to avoid GitHub API rate-limit 403 errors.")
    if not change_details:
        print("Tip: run again with --change-details and a narrow --include for "
              "updated items to inspect commit-level upstream changes.")
    for result in output["results"]:
        suffix = ""
        if change_details:
            suffix = " | upstream commits since local: %d" % result["upstreamChanges"]["commitCount"]
        print("[%s] %s <- %s | %s%s | recommendation: %s"
              % (result["status"], result["localPath"], result["sourceUrl"],
                 result["reason"], suffix, result["recommendation"]))


# --- The pin diff ----------------------------------------------------------


def moved_pins(root: Path, only: list[str]) -> list[dict]:
    """Every dependency whose `#sha` differs between HEAD and the working tree."""
    moved = []
    for package in workspace.packages(root):
        if only and package.directory not in only and package.name not in only:
            continue
        committed = workspace.git(
            ["show", "HEAD:packages/%s/apm.yml" % package.directory], root, check=False)
        if not committed:
            continue
        from ruamel.yaml import YAML
        before = workspace.pins_of(YAML(typ="safe").load(committed) or {})
        after = workspace.pins_of(package.manifest)
        for key, sha in after.items():
            if key in before and before[key].lower() != sha.lower():
                moved.append({"package": package.directory, "repo": key[0],
                              "path": key[1], "from": before[key], "to": sha})
    return moved


def print_compare(client, pin: dict, max_files: int) -> None:
    owner, _, repo = pin["repo"].partition("/")
    print("\n=== %s: %s%s\n    %s -> %s"
          % (pin["package"], pin["repo"], "/" + pin["path"] if pin["path"] else "",
             pin["from"][:12], pin["to"][:12]))
    try:
        payload = client.compare(owner, repo, pin["from"], pin["to"])
    except ApiError as exc:
        print("    could not compare: %s" % exc)
        return
    print("    %d commit(s) upstream:" % len(payload.get("commits") or []))
    for commit in payload.get("commits") or []:
        print("      %s %s" % (commit["sha"][:10],
                               commit["commit"]["message"].split("\n")[0][:90]))
    files = [f for f in payload.get("files") or []
             if not pin["path"] or f.get("filename", "").startswith(pin["path"])]
    if not files:
        print("    no file under %s changed -- the bump is outside what this repo "
              "consumes" % (pin["path"] or "the repository root"))
        return
    print("    %d file(s) changed under %s:" % (len(files), pin["path"] or "/"))
    for changed in files[:max_files]:
        print("\n--- %s (%s, +%s/-%s)"
              % (changed.get("filename"), changed.get("status"),
                 changed.get("additions"), changed.get("deletions")))
        patch = changed.get("patch")
        print(patch if patch else "    (no textual patch: binary or too large)")
    if len(files) > max_files:
        print("\n    ... and %d more file(s); raise --max-files to see them"
              % (len(files) - max_files))


# --- CLI -------------------------------------------------------------------


def main(repo: str = typer.Option("", "--repo", help="workspace to audit "
                                  "(default: the enclosing git repo)"),
         include: str = typer.Option("", "--include", help="workspace-relative glob"),
         specs: bool = typer.Option(False, "--specs",
                                    help="audit authoritativeSpec sources instead"),
         compare: bool = typer.Option(False, "--compare",
                                      help="diff the pins moved in the working tree"),
         package: list[str] = typer.Option([], "--package", help="--compare: only these"),
         max_files: int = typer.Option(10, "--max-files", help="--compare: patches to print"),
         json_out: bool = typer.Option(False, "--json", help="machine-readable output"),
         change_details: bool = typer.Option(False, "--change-details"),
         max_change_commits: int = typer.Option(5, "--max-change-commits", min=1, max=100),
         allow_no_local_commit: bool = typer.Option(False, "--allow-no-local-commit"),
         github_token: str = typer.Option("", "--github-token")) -> None:
    root = repo_root(repo)
    token = githublib.token(github_token)
    client = githublib.GitHub(token)

    if compare:
        pins = moved_pins(root, package)
        if not pins:
            print("no pin moved in the working tree -- nothing to review")
            return
        for pin in pins:
            print_compare(client, pin, max_files)
        return

    kind = "authoritativeSpec" if specs else "adaptedFrom"
    items = tracked_entries(root, kind)
    if include:
        items = [i for i in items if fnmatch.fnmatchcase(i["localPath"], include)]
    if not items:
        sys.stderr.write("no %s sources found%s.\n"
                         % (kind, " for --include '%s'" % include if include else ""))
        raise typer.Exit(1)

    options = {"change_details": change_details,
               "max_change_commits": max_change_commits,
               "allow_no_local_commit": allow_no_local_commit}
    auditor = audit_spec if specs else audit_adapted
    results = [auditor(item, root, client, options) for item in items]

    output = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "repoRoot": str(root),
        "mode": kind,
        "includePath": include,
        "authMode": "token" if token else "unauthenticated",
        "summary": summarize(results),
        "results": results,
    }
    if json_out:
        print(json.dumps(output, indent=2))
    else:
        report(output, change_details)


if __name__ == "__main__":
    typer.run(main)
