# Script Templates

Annotated examples for [python-scripts §5–§7](../SKILL.md#5-structure). Copy the tier that matches the job; do not carry the heavier one's machinery into a one-off.

## Minimal — standard library only

No dependency list is needed, but a `requires-python` floor is still worth stating when the syntax needs one — and it is only *enforced* if the script is launched through a runner, so the shebang names one. With a plain `#!/usr/bin/env python3` shebang the floor is documentation, not a check.

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# ///
"""Print the ten largest files under a directory, one `size\tpath` per line."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path


def largest_files(root: Path, count: int) -> list[tuple[int, Path]]:
    """Pure: takes a root, returns sizes. Callable from a test with a tmp_path."""
    entries = ((p.stat().st_size, p) for p in root.rglob("*") if p.is_file())
    return sorted(entries, reverse=True)[:count]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("-n", "--count", type=int, default=10)
    args = parser.parse_args(argv)

    if not args.root.is_dir():
        print(f"not a directory: {args.root}", file=sys.stderr)
        return 2

    for size, path in largest_files(args.root, args.count):
        print(f"{size}\t{path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Note the split: results on **stdout**, the error on **stderr**, and a distinct exit code (`2`) for a usage failure.

## With dependencies

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "httpx>=0.28",
# ]
# ///
"""Fetch build status for each repo named on stdin; print `repo\tstatus`."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from collections.abc import Sequence

import httpx

logger = logging.getLogger(__name__)


class BuildStatusError(Exception):
    """Raised when the API cannot be read for a repo."""


def fetch_status(client: httpx.Client, repo: str) -> str:
    response = client.get(f"/repos/{repo}/status", timeout=10.0)
    if response.status_code == 404:
        raise BuildStatusError(f"no such repo: {repo}")
    response.raise_for_status()
    return response.json()["state"]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="https://api.example.com")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        stream=sys.stderr,
        format="%(levelname)s %(message)s",
    )

    token = os.environ.get("BUILD_API_TOKEN")
    if token is None:
        print("BUILD_API_TOKEN is not set", file=sys.stderr)
        return 2

    repos = [line.strip() for line in sys.stdin if line.strip()]
    failures = 0
    with httpx.Client(base_url=args.base_url, headers={"Authorization": f"Bearer {token}"}) as client:
        for repo in repos:
            try:
                print(f"{repo}\t{fetch_status(client, repo)}")
            except (BuildStatusError, httpx.HTTPError):
                logger.exception("could not read status for %s", repo)
                failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Points worth copying: the token comes from the environment rather than an argument; logging is configured here because this *is* the entry point; per-item failures are counted and reflected in the exit code instead of aborting the run.

## Destructive — dry run by default

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# ///
"""Delete build artifacts older than N days. Prints what it would remove."""

from __future__ import annotations

import argparse
import shutil
import sys
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path


def stale_paths(root: Path, cutoff: datetime) -> list[Path]:
    """Pure enough to test: no deletion happens here."""
    return [
        path
        for path in root.glob("*/build")
        if datetime.fromtimestamp(path.stat().st_mtime, UTC) < cutoff
    ]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="actually delete; without this the script only reports",
    )
    args = parser.parse_args(argv)

    if args.days < 1:
        print("--days must be at least 1", file=sys.stderr)
        return 2

    cutoff = datetime.now(UTC) - timedelta(days=args.days)
    targets = stale_paths(args.root, cutoff)

    for path in targets:
        print(f"{'removing' if args.apply else 'would remove'} {path}")
        if args.apply:
            shutil.rmtree(path)

    print(f"{len(targets)} directories", file=sys.stderr)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130) from None
```

The safe mode is the default, argument validation completes before anything is touched, and an interrupt exits `130` rather than dumping a traceback.

## Testing one of these

A script following this shape imports like any module — no subprocess, no `sys.argv` patching:

```python
def test_largest_files(tmp_path):
    (tmp_path / "a.txt").write_bytes(b"x" * 100)
    (tmp_path / "b.txt").write_bytes(b"x" * 10)
    assert [p.name for _, p in largest_files(tmp_path, 1)] == ["a.txt"]


def test_main_rejects_missing_directory(tmp_path):
    assert main([str(tmp_path / "nope")]) == 2
```

That is the whole return on `main(argv) -> int` and a pure core function.
