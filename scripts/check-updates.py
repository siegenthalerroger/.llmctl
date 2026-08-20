#!/usr/bin/env python3
"""Audit files that declare `metadata.provenance.adaptedFrom` for upstream drift.

For every tracked entry, compare the local file's last commit date against the
latest upstream commit for the source URL, and classify the result. Writes
nothing; the output is the audit.

  up_to_date            local commit is not older than upstream
  update_available      upstream moved since the local file was last committed
  missing_local_commit  the local file is not in git history yet (see
                        --allow-no-local-commit to treat it as a bootstrap)
  fetch_failed          the upstream could not be read
  not_trackable         the source has no revision history to diff against --
                        a book, a paper, a vendor doc page. A permanent property
                        of the URL, not a failure, so it is kept out of the
                        failure count: filing these as `fetch_failed` parks
                        unfixable rows in the audit, which is how an audit stops
                        being read.

Frontmatter is parsed by provenance.py, the same module check-licenses.py and
gen-notices.py use, and the file walk is that module's too. Sharing both is the
point: this audit and the licence checker have to agree on what is tracked, and
an entry that silently stops being tracked produces no error anywhere -- it just
quietly leaves the audit.

This is the automation behind the `meta-upstream-sync` skill, which documents the
workflow around it. It lives here rather than under the skill because the skill is
repo-local -- root `.apm/`, in no package and no packed bundle -- so there is no
bundle for a script to travel in, and every other tool that reads provenance is
already in this directory.

Usage:
  python scripts/check-updates.py --repo PATH [options]

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
import argparse
import fnmatch
import json
import os
import ssl
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import provenance as prov  # noqa: E402

API_ROOT = "https://api.github.com"
USER_AGENT = "llmctl-meta-upstream-sync"



# --- Authentication --------------------------------------------------------


def resolve_token(explicit):
    """Explicit flag, then the env vars, then whatever `gh` is logged in as."""
    for candidate in (explicit, os.environ.get("GITHUB_TOKEN"),
                      os.environ.get("GH_TOKEN")):
        if candidate and candidate.strip():
            return candidate.strip()
    try:
        got = subprocess.run(["gh", "auth", "token"], capture_output=True,
                             text=True)
    except OSError:
        return ""
    if got.returncode == 0 and got.stdout.strip():
        return got.stdout.strip()
    return ""


# --- GitHub API ------------------------------------------------------------


class ApiError(Exception):
    pass


def api_get(url, token):
    headers = {"User-Agent": USER_AGENT, "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = "Bearer %s" % token
    request = urllib.request.Request(url, headers=headers)
    try:
        response = urllib.request.urlopen(request, timeout=30,
                                          context=ssl.create_default_context())
        return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 403:
            if not token:
                raise ApiError(
                    "GitHub API returned 403 (likely unauthenticated rate "
                    "limit). Run 'gh auth login', set GITHUB_TOKEN/GH_TOKEN, "
                    "or pass --github-token.")
            raise ApiError("GitHub API returned 403 with authentication. Verify "
                           "token validity/scopes or wait for rate limit reset.")
        raise ApiError("GitHub API returned %d for %s" % (exc.code, url))
    except (urllib.error.URLError, ValueError) as exc:
        raise ApiError("GitHub API request failed: %s" % exc)


def is_trackable(url):
    """Can this source be compared against a local commit date at all?

    Drift detection needs a revision history to read a date from, which limits it
    to the hosts `github_query` understands. Keep the two in step: a host one
    admits and the other rejects either throws on something reported as
    checkable, or skips something that could have been checked.
    """
    try:
        return urllib.parse.urlparse(url).hostname == "github.com"
    except ValueError:
        return False


def github_query(url):
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


def commits_url(query, **extra):
    """A /commits query with the valueless parameters omitted.

    `path` and `sha` are both optional to the API and both genuinely absent for
    some URL forms: a repository-level entry has no path, a bare repository URL
    names no branch. Sending `sha=` empty is not the same as omitting it --
    omitting it is what makes the API use the repository's default branch.
    """
    params = []
    if query["path"]:
        params.append(("path", query["path"]))
    if query["ref"]:
        params.append(("sha", query["ref"]))
    params.extend(sorted(extra.items()))
    return "%s/repos/%s/%s/commits?%s" % (API_ROOT, query["owner"],
                                          query["repo"],
                                          urllib.parse.urlencode(params))


def as_list(payload):
    if isinstance(payload, list):
        return payload
    return [payload] if payload else []


def latest_commit(query, token):
    commits = as_list(api_get(commits_url(query, per_page=1), token))
    if not commits or not commits[0].get("sha"):
        raise ApiError("No upstream commits found for '%s/%s' at ref '%s' and "
                       "path '%s'." % (query["owner"], query["repo"],
                                       query["ref"], query["path"]))
    head = commits[0]
    return {"commitSha": str(head["sha"]),
            "commitDate": iso(head["commit"]["committer"]["date"])}


def commit_rows(query, token, max_commits, since=None):
    extra = {"per_page": max_commits}
    if since is not None:
        extra["since"] = since.astimezone(timezone.utc).isoformat()
    rows = []
    for commit in as_list(api_get(commits_url(query, **extra), token)):
        sha = str(commit.get("sha") or "")
        if not sha:
            continue
        rows.append({
            "sha": sha,
            "shortSha": sha[:10],
            "date": iso(commit["commit"]["committer"]["date"]),
            "author": str(commit["commit"]["author"]["name"]),
            "message": str(commit["commit"]["message"]).split("\n", 1)[0].rstrip("\r"),
            "url": str(commit.get("html_url") or ""),
        })
    return rows


def no_changes():
    return {"collected": False, "commitCount": 0, "commits": []}


# --- Dates -----------------------------------------------------------------


def parse_date(value):
    """Parse an ISO-8601 timestamp, tolerating the API's trailing `Z`."""
    if not value:
        raise ValueError("cannot parse empty date value")
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def iso(value):
    return parse_date(value).isoformat()


# --- Discovery -------------------------------------------------------------


def git_log(repo, path):
    """The local file's last commit, or empty strings when it has none."""
    got = subprocess.run(["git", "log", "-n", "1", "--format=%H|%cI", "--", path],
                         cwd=repo, capture_output=True, text=True)
    if got.returncode != 0 or not got.stdout.strip():
        return {"commitSha": "", "commitDate": ""}
    sha, _, date = got.stdout.strip().partition("|")
    return {"commitSha": sha, "commitDate": date}


def repo_root(hint):
    if hint and os.path.isdir(hint):
        return os.path.abspath(hint)
    got = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                         capture_output=True, text=True)
    if got.returncode == 0 and got.stdout.strip():
        return got.stdout.strip()
    sys.stderr.write("unable to determine the git repository root -- run from a "
                     "git repo or pass --repo\n")
    raise SystemExit(1)


def tracked_entries(root):
    """One record per upstream URL across every customization file.

    `authoritativeSpec` is deliberately not walked: it declares which spec a file
    conforms to, not where its content came from, so it has no drift to report.
    """
    entries = []
    for path in prov.iter_files(root):
        if not prov.is_customization(path):
            continue
        record = prov.parse(path)
        relative = os.path.relpath(path, root).replace("\\", "/")
        for entry in record["entries"]:
            if entry["kind"] != "adaptedFrom":
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


def row(item, status, recommendation, recommend, reason, local=None,
        upstream=None, changes=None, older=None, delta=None):
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


def audit(item, root, token, args):
    if not is_trackable(item["sourceUrl"]):
        return row(item, "not_trackable", "none_source_has_no_revision_history",
                   False, "source_host_is_not_revision_controlled")

    local = git_log(root, item["localPath"])

    if not local["commitDate"]:
        if not args.allow_no_local_commit:
            return row(item, "missing_local_commit", "commit_local_file_first",
                       False, "local_file_not_in_git_history", local)
        changes = no_changes()
        try:
            query = github_query(item["sourceUrl"])
            upstream = latest_commit(query, token)
            if args.change_details:
                changes = {"collected": True,
                           "commits": commit_rows(query, token,
                                                  args.max_change_commits)}
                changes["commitCount"] = len(changes["commits"])
        except ApiError as exc:
            return row(item, "fetch_failed", "check_source_url", False, str(exc),
                       local, changes=changes)
        return row(item, "update_available",
                   "bootstrap_review_and_merge_from_upstream", True,
                   "local_file_not_in_git_history_bootstrap_allowed", local,
                   upstream, changes)

    try:
        query = github_query(item["sourceUrl"])
        upstream = latest_commit(query, token)
    except ApiError as exc:
        return row(item, "fetch_failed", "check_source_url", False, str(exc),
                   local)

    local_date = parse_date(local["commitDate"])
    upstream_date = parse_date(upstream["commitDate"])
    older = local_date < upstream_date
    delta = round((upstream_date - local_date).total_seconds() / 86400.0, 3)

    if not older:
        return row(item, "up_to_date", "none", False,
                   "local_commit_date_is_not_older_than_upstream", local,
                   upstream, None, older, delta)

    changes = no_changes()
    if args.change_details:
        try:
            commits = commit_rows(query, token, args.max_change_commits,
                                  since=local_date)
            changes = {"collected": True, "commitCount": len(commits),
                       "commits": commits,
                       "since": local_date.astimezone(timezone.utc).isoformat()}
        except ApiError as exc:
            changes = {"collected": False, "commitCount": 0, "commits": [],
                       "error": str(exc)}
    return row(item, "update_available", "review_and_merge_from_upstream", True,
               "upstream_commit_newer_than_local_commit", local, upstream,
               changes, older, delta)


def summarize(results):
    def count(predicate):
        return sum(1 for r in results if predicate(r))
    return {
        "filesChecked": len({r["localPath"] for r in results}),
        "upstreamChecks": len(results),
        "upToDateCount": count(lambda r: r["status"] == "up_to_date"),
        "updateAvailableCount": count(lambda r: r["status"] == "update_available"),
        "failedCount": count(lambda r: r["status"] in ("fetch_failed",
                                                       "missing_local_commit")),
        "notTrackableCount": count(lambda r: r["status"] == "not_trackable"),
        "recommendCount": count(lambda r: r["recommendUpdate"]),
    }


def report(output, args):
    summary = output["summary"]
    print("Meta upstream sync check complete")
    print("Auth: %s | Files: %d | Upstreams: %d | Up-to-date: %d | "
          "Update-available: %d | Failed: %d | Not-trackable: %d | Recommend: %d"
          % (output["authMode"], summary["filesChecked"],
             summary["upstreamChecks"], summary["upToDateCount"],
             summary["updateAvailableCount"], summary["failedCount"],
             summary["notTrackableCount"], summary["recommendCount"]))
    if output["authMode"] == "unauthenticated":
        print("Tip: run 'gh auth login' (or set GITHUB_TOKEN/GH_TOKEN, or pass "
              "--github-token) to avoid GitHub API rate-limit 403 errors.")
    if not args.change_details:
        print("Tip: run again with --change-details and a narrow --include for "
              "updated items to inspect commit-level upstream changes.")
    for result in output["results"]:
        if args.change_details:
            print("[%s] %s <- %s | %s | upstream commits since local: %d | "
                  "recommendation: %s"
                  % (result["status"], result["localPath"], result["sourceUrl"],
                     result["reason"], result["upstreamChanges"]["commitCount"],
                     result["recommendation"]))
        else:
            print("[%s] %s <- %s | %s | recommendation: %s"
                  % (result["status"], result["localPath"], result["sourceUrl"],
                     result["reason"], result["recommendation"]))


def bounded(value):
    number = int(value)
    if not 1 <= number <= 100:
        raise argparse.ArgumentTypeError("must be between 1 and 100")
    return number


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", default="", metavar="PATH",
                        help="workspace to audit (default: enclosing git repo)")
    parser.add_argument("--include", default="", metavar="GLOB",
                        help="only paths matching this workspace-relative glob")
    parser.add_argument("--json", action="store_true",
                        help="machine-readable output")
    parser.add_argument("--change-details", action="store_true",
                        help="collect commit-level upstream changes")
    parser.add_argument("--max-change-commits", type=bounded, default=5,
                        metavar="N", help="cap that payload (1-100, default 5)")
    parser.add_argument("--allow-no-local-commit", action="store_true",
                        help="treat an uncommitted local file as a bootstrap "
                             "candidate rather than an error")
    parser.add_argument("--github-token", default="", metavar="TOKEN",
                        help="overrides GITHUB_TOKEN / GH_TOKEN / gh auth token")
    args = parser.parse_args()

    root = repo_root(args.repo)
    items = tracked_entries(root)
    if args.include:
        items = [i for i in items if fnmatch.fnmatchcase(i["localPath"],
                                                         args.include)]
    if not items:
        sys.stderr.write("no tracked files found%s. Add "
                         "metadata.provenance.adaptedFrom URLs in frontmatter.\n"
                         % (" for --include '%s'" % args.include
                            if args.include else ""))
        return 1

    token = resolve_token(args.github_token)
    results = [audit(item, root, token, args) for item in items]

    output = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "repoRoot": root,
        "includePath": args.include,
        "authMode": "token" if token else "unauthenticated",
        "summary": summarize(results),
        "results": results,
    }

    if args.json:
        print(json.dumps(output, indent=2))
    else:
        report(output, args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
