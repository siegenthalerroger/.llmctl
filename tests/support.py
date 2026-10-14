"""Fixtures shared by the tests: a throwaway workspace tree and a stand-in GitHub client."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SKILLS = "packages/p/.apm/skills/s"


def write(root: Path, rel: str, text: str = "") -> Path:
    """Create `rel` under `root` (parents included) and return its path."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def block(key: str, *items: str | dict[str, str]) -> str:
    """One provenance key: a bare URL per string, an object entry per dict (`url` first)."""
    lines = [f"    {key}:"]
    for item in items:
        if isinstance(item, str):
            lines.append(f'      - "{item}"')
            continue
        (first, *rest) = item.items()
        lines.append(f'      - {first[0]}: "{first[1]}"')
        lines += [f'        {name}: "{value}"' for name, value in rest]
    return "\n".join(lines)


def frontmatter(body: str, *, license_: str | None = None, name: str | None = None) -> str:
    """A frontmatter block holding `metadata.provenance` = `body` (already indented 4)."""
    lines = ["---"]
    if name:
        lines += [f'name: "{name}"', f'description: "{name} description."']
    if license_:
        lines.append(f"license: {license_}")
    lines += ["metadata:", "  provenance:", body.rstrip("\n"), "---", "", "# Body", ""]
    return "\n".join(lines)


def commit_all(root: Path, when: str) -> None:
    """Make `root` a git repository with one commit dated `when` (ISO 8601)."""
    env = {
        **os.environ,
        "GIT_AUTHOR_DATE": when,
        "GIT_COMMITTER_DATE": when,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.com",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.com",
    }
    # gpgsign off: a developer's global config must not decide whether a fixture commits.
    steps = (
        ["init", "-q"],
        ["add", "-A"],
        ["-c", "commit.gpgsign=false", "commit", "-q", "-m", "x"],
    )
    for args in steps:
        subprocess.run(["git", *args], cwd=root, env=env, check=True, capture_output=True)


class FakeGitHub:
    """Answers the three questions `audit_adapted` asks, from a fixed upstream head."""

    def __init__(self, head_date: str, *, exists: bool = True) -> None:
        self.head_date = head_date
        self.exists = exists

    def path_exists(self, *_args: object, **_kwargs: object) -> bool:
        return self.exists

    def latest_commit(self, *_args: object, **_kwargs: object) -> dict:
        return {"commitSha": "f" * 40, "commitDate": self.head_date}

    def commit_rows(self, *_args: object, **_kwargs: object) -> list[dict]:
        return []
