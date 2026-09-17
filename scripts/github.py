"""The one GitHub API client the scripts share.

Three callers, three very different needs -- the drift audit reads commit
dates, the notices verifier reads licences, the release writes releases -- and
each used to carry its own transport (urllib with an ssl context, `gh api`, or
nothing). One httpx client means one token rule, one error type, and one place
where a rate-limit 403 is explained rather than reported as a bare status.

Authentication: `--github-token` where a script offers it, then GITHUB_TOKEN,
then GH_TOKEN, then whatever `gh auth token` prints. The last is what a
contributor's shell usually has; the env vars are what CI has.
"""
from __future__ import annotations

import os
import subprocess
from datetime import datetime, timezone
from typing import Any

import httpx

API_ROOT = "https://api.github.com"
USER_AGENT = "llmctl-scripts"


class ApiError(Exception):
    pass


def token(explicit: str = "") -> str:
    """Explicit flag, then the env vars, then whatever `gh` is logged in as."""
    for candidate in (explicit, os.environ.get("GITHUB_TOKEN"),
                      os.environ.get("GH_TOKEN")):
        if candidate and candidate.strip():
            return candidate.strip()
    try:
        got = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True)
    except OSError:
        return ""
    return got.stdout.strip() if got.returncode == 0 else ""


def parse_date(value: str) -> datetime:
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


def iso(value: str) -> str:
    return parse_date(value).isoformat()


class GitHub:
    def __init__(self, auth: str = "", base_url: str = API_ROOT, timeout: float = 30.0):
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if auth:
            headers["Authorization"] = "Bearer %s" % auth
        self.authenticated = bool(auth)
        self.client = httpx.Client(base_url=base_url, headers=headers,
                                   timeout=timeout, follow_redirects=True)

    # -- transport ------------------------------------------------------

    def _raise(self, response: httpx.Response) -> None:
        if response.status_code == 403:
            if not self.authenticated:
                raise ApiError(
                    "GitHub API returned 403 (likely the unauthenticated rate "
                    "limit). Run 'gh auth login', set GITHUB_TOKEN/GH_TOKEN, or "
                    "pass --github-token.")
            raise ApiError("GitHub API returned 403 with authentication. Verify "
                           "the token's validity/scopes or wait for the rate "
                           "limit to reset.")
        raise ApiError("GitHub API returned %d for %s"
                       % (response.status_code, response.request.url))

    def get(self, path: str, ok_404: bool = False, missing=(404,), **params: Any) -> Any:
        try:
            response = self.client.get(path, params={k: v for k, v in params.items()
                                                     if v not in (None, "")})
        except httpx.HTTPError as exc:
            raise ApiError("GitHub API request failed: %s" % exc)
        if ok_404 and response.status_code in missing:
            return None
        if response.status_code >= 400:
            self._raise(response)
        return response.json()

    def post(self, path: str, payload: dict) -> Any:
        try:
            response = self.client.post(path, json=payload)
        except httpx.HTTPError as exc:
            raise ApiError("GitHub API request failed: %s" % exc)
        if response.status_code >= 400:
            detail = ""
            try:
                detail = response.json().get("message", "")
            except ValueError:
                pass
            raise ApiError("GitHub API returned %d for POST %s%s"
                           % (response.status_code, path,
                              (": " + detail) if detail else ""))
        return response.json()

    # -- commits and content -------------------------------------------

    def commits(self, owner: str, repo: str, path: str = "", ref: str = "",
                per_page: int = 1, since: datetime | None = None) -> list[dict]:
        """`/commits` with the valueless parameters omitted: sending `sha=`
        empty is not the same as omitting it -- omitting it is what makes the
        API use the repository's default branch."""
        payload = self.get("/repos/%s/%s/commits" % (owner, repo), path=path,
                           sha=ref, per_page=per_page,
                           since=since.astimezone(timezone.utc).isoformat()
                           if since else None)
        return payload if isinstance(payload, list) else ([payload] if payload else [])

    def latest_commit(self, owner: str, repo: str, path: str = "", ref: str = "") -> dict:
        commits = self.commits(owner, repo, path, ref, per_page=1)
        if not commits or not commits[0].get("sha"):
            raise ApiError("No upstream commits found for '%s/%s' at ref '%s' and "
                           "path '%s'." % (owner, repo, ref, path))
        head = commits[0]
        return {"commitSha": str(head["sha"]),
                "commitDate": iso(head["commit"]["committer"]["date"])}

    def commit_rows(self, owner: str, repo: str, path: str, ref: str,
                    max_commits: int, since: datetime | None = None) -> list[dict]:
        rows = []
        for commit in self.commits(owner, repo, path, ref, max_commits, since):
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

    def path_exists(self, owner: str, repo: str, path: str, ref: str = "") -> bool:
        """Does `path` still exist at `ref` (default branch when empty)?

        `/commits?path=` happily returns the commit that *deleted* a path, so a
        date comparison alone reports a dead upstream as healthy forever.
        """
        if not path:
            return True
        return self.get("/repos/%s/%s/contents/%s" % (owner, repo, path),
                        ok_404=True, ref=ref) is not None

    def compare(self, owner: str, repo: str, base: str, head: str) -> dict:
        return self.get("/repos/%s/%s/compare/%s...%s" % (owner, repo, base, head))

    def pulls_for_commit(self, owner: str, repo: str, sha: str) -> list[dict]:
        """The pull requests a commit arrived through, or [].

        422 joins 404 as "none": that is what the API answers for a commit it
        cannot see yet, which is every commit of a release being rehearsed
        locally before the branch is pushed. Neither is an error worth printing
        -- a commit with no pull request is the ordinary case.
        """
        payload = self.get("/repos/%s/%s/commits/%s/pulls" % (owner, repo, sha),
                           ok_404=True, missing=(404, 422))
        return payload or []

    # -- releases and metadata ------------------------------------------

    def create_release(self, owner: str, repo: str, tag: str, name: str,
                       body: str, target: str) -> dict:
        return self.post("/repos/%s/%s/releases" % (owner, repo), {
            "tag_name": tag, "name": name, "body": body,
            "target_commitish": target, "draft": False, "prerelease": False,
        })

    def repo_license(self, owner: str, repo: str) -> str:
        """The SPDX id GitHub detects for a repository, or NONE."""
        payload = self.get("/repos/%s/%s" % (owner, repo))
        info = (payload or {}).get("license") or {}
        return str(info.get("spdx_id") or "NONE")

    def head(self, url: str) -> httpx.Response:
        """A HEAD (falling back to GET) against an arbitrary URL, for the
        authoritativeSpec probe. Not under the API base URL."""
        try:
            response = httpx.head(url, follow_redirects=True, timeout=30.0,
                                  headers={"User-Agent": USER_AGENT})
            if response.status_code in (405, 501):
                response = httpx.get(url, follow_redirects=True, timeout=30.0,
                                     headers={"User-Agent": USER_AGENT})
            return response
        except httpx.HTTPError as exc:
            raise ApiError("request failed: %s" % exc)
