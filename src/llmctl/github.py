"""The one GitHub API client the commands share.

Three callers with different needs -- the drift audit reads commit dates, the
notices verifier reads licences, the release writes releases -- and one token
rule, one error type, and one place a rate-limit 403 is explained.
Authentication: an explicit token, then GITHUB_TOKEN, GH_TOKEN, `gh auth token`.
"""

from __future__ import annotations

import os
import subprocess
from datetime import UTC, datetime
from typing import Any

import httpx

API_ROOT = "https://api.github.com"
USER_AGENT = "llmctl-scripts"


class ApiError(Exception):
    pass


def token(explicit: str = "") -> str:
    """Explicit flag, then the env vars, then whatever `gh` is logged in as."""
    for candidate in (explicit, os.environ.get("GITHUB_TOKEN"), os.environ.get("GH_TOKEN")):
        if candidate and candidate.strip():
            return candidate.strip()
    try:
        got = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=False)
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
        parsed = parsed.replace(tzinfo=UTC)
    return parsed


def iso(value: str) -> str:
    return parse_date(value).isoformat()


class GitHub:
    def __init__(self, auth: str = "", base_url: str = API_ROOT, timeout: float = 30.0) -> None:
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if auth:
            headers["Authorization"] = f"Bearer {auth}"
        self.authenticated = bool(auth)
        self.client = httpx.Client(
            base_url=base_url, headers=headers, timeout=timeout, follow_redirects=True
        )

    # -- transport ------------------------------------------------------

    @staticmethod
    def _detail(response: httpx.Response) -> str:
        """GitHub's own account of what it rejected.

        A bare status tells you nothing actionable: a 422 on a release reads
        "Validation Failed" while the `errors` array names the offending field.
        Dropping that is how a broken call stays undiagnosable across releases.
        """
        try:
            payload = response.json()
        except ValueError:
            return (response.text or "").strip()[:200]
        if not isinstance(payload, dict):
            return ""
        parts = [str(payload.get("message") or "").strip()]
        for item in payload.get("errors") or []:
            if isinstance(item, dict):
                field = item.get("field") or item.get("resource") or ""
                reason = item.get("message") or item.get("code") or ""
                parts.append(f"{field}: {reason}".strip(": "))
            else:
                parts.append(str(item))
        return "; ".join(part for part in parts if part)

    def _raise(self, response: httpx.Response) -> None:
        detail = self._detail(response)
        # The endpoint belongs in every message, not just the ones that are not
        # 403. A permission gap is precisely the case where which call was
        # refused is the whole question: a release publish touches three
        # endpoints across two scopes, and "403 with authentication" alone
        # cannot tell you which of them the token is short of.
        request = response.request
        where = f"{request.method} {request.url}"
        hint = ""
        if response.status_code == httpx.codes.FORBIDDEN:
            hint = (
                " (likely the unauthenticated rate limit). Run 'gh auth login', "
                "set GITHUB_TOKEN/GH_TOKEN, or pass --github-token."
                if not self.authenticated
                else " with authentication. Verify the token's validity and the "
                "scopes this endpoint needs, or wait for the rate limit to reset."
            )
        message = f"GitHub API returned {response.status_code} for {where}{hint}"
        return_detail = f" {detail}" if detail else ""
        raise ApiError(f"{message}{return_detail}")

    def get(
        self,
        endpoint: str,
        *,
        ok_404: bool = False,
        missing: tuple[int, ...] = (404,),
        **params: Any,
    ) -> Any:
        """GET `endpoint` with `params` as the query string.

        The endpoint is not called `path` because `path` is itself a GitHub
        query parameter: `commits(path=...)` would bind to it and raise
        "multiple values for argument" instead of filtering by path.
        """
        try:
            response = self.client.get(
                endpoint, params={k: v for k, v in params.items() if v not in (None, "")}
            )
        except httpx.HTTPError as exc:
            raise ApiError(f"GitHub API request failed: {exc}") from exc
        if ok_404 and response.status_code in missing:
            return None
        if response.status_code >= httpx.codes.BAD_REQUEST:
            self._raise(response)
        return response.json()

    def post(self, endpoint: str, payload: dict) -> Any:
        try:
            response = self.client.post(endpoint, json=payload)
        except httpx.HTTPError as exc:
            raise ApiError(f"GitHub API request failed: {exc}") from exc
        if response.status_code >= httpx.codes.BAD_REQUEST:
            self._raise(response)
        return response.json()

    # -- commits and content -------------------------------------------

    def commits(
        self,
        owner: str,
        repo: str,
        *,
        path: str = "",
        ref: str = "",
        per_page: int = 1,
        since: datetime | None = None,
    ) -> list[dict]:
        """`/commits` with the valueless parameters omitted: sending `sha=`
        empty is not the same as omitting it -- omitting it is what makes the
        API use the repository's default branch."""
        payload = self.get(
            f"/repos/{owner}/{repo}/commits",
            path=path,
            sha=ref,
            per_page=per_page,
            since=since.astimezone(UTC).isoformat() if since else None,
        )
        return payload if isinstance(payload, list) else ([payload] if payload else [])

    def latest_commit(self, owner: str, repo: str, path: str = "", ref: str = "") -> dict:
        commits = self.commits(owner, repo, path=path, ref=ref, per_page=1)
        if not commits or not commits[0].get("sha"):
            raise ApiError(
                f"No upstream commits found for '{owner}/{repo}' at ref '{ref}' and path '{path}'."
            )
        head = commits[0]
        return {
            "commitSha": str(head["sha"]),
            "commitDate": iso(head["commit"]["committer"]["date"]),
        }

    def commit_rows(
        self,
        owner: str,
        repo: str,
        *,
        path: str,
        ref: str,
        max_commits: int,
        since: datetime | None = None,
    ) -> list[dict]:
        rows = []
        for commit in self.commits(
            owner, repo, path=path, ref=ref, per_page=max_commits, since=since
        ):
            sha = str(commit.get("sha") or "")
            if not sha:
                continue
            rows.append(
                {
                    "sha": sha,
                    "shortSha": sha[:10],
                    "date": iso(commit["commit"]["committer"]["date"]),
                    "author": str(commit["commit"]["author"]["name"]),
                    "message": str(commit["commit"]["message"]).split("\n", 1)[0].rstrip("\r"),
                    "url": str(commit.get("html_url") or ""),
                }
            )
        return rows

    def path_exists(self, owner: str, repo: str, path: str, ref: str = "") -> bool:
        """Does `path` still exist at `ref` (default branch when empty)?

        `/commits?path=` happily returns the commit that *deleted* a path, so a
        date comparison alone reports a dead upstream as healthy forever.
        """
        if not path:
            return True
        return self.get(f"/repos/{owner}/{repo}/contents/{path}", ok_404=True, ref=ref) is not None

    def compare(self, owner: str, repo: str, base: str, head: str) -> dict:
        return self.get(f"/repos/{owner}/{repo}/compare/{base}...{head}")

    def pulls_for_commit(self, owner: str, repo: str, sha: str) -> list[dict]:
        """The pull requests a commit arrived through, or [].

        422 joins 404 as "none": that is what the API answers for a commit it
        cannot see yet, which is every commit of a release being rehearsed
        locally before the branch is pushed. Neither is an error worth printing
        -- a commit with no pull request is the ordinary case.
        """
        payload = self.get(
            f"/repos/{owner}/{repo}/commits/{sha}/pulls", ok_404=True, missing=(404, 422)
        )
        return payload or []

    # -- releases and metadata ------------------------------------------

    def release_for_tag(self, owner: str, repo: str, tag: str) -> dict | None:
        """The release already published for `tag`, or None.

        A release is created after its tag is pushed, so the two can end up out
        of step -- a failed or rate-limited create leaves a tag with no page.
        Asking first is what lets the next run finish the job instead of
        reporting nothing to do.
        """
        return self.get(f"/repos/{owner}/{repo}/releases/tags/{tag}", ok_404=True)

    def create_release(
        self, owner: str, repo: str, *, tag: str, name: str, body: str, target: str
    ) -> dict:
        return self.post(
            f"/repos/{owner}/{repo}/releases",
            {
                "tag_name": tag,
                "name": name,
                "body": body,
                "target_commitish": target,
                "draft": False,
                "prerelease": False,
            },
        )

    def repo_license(self, owner: str, repo: str) -> str:
        """The SPDX id GitHub detects for a repository, or NONE."""
        payload = self.get(f"/repos/{owner}/{repo}")
        info = (payload or {}).get("license") or {}
        return str(info.get("spdx_id") or "NONE")
