"""SessionStart hook: add always-on instructions to the session context.

Usage: always-on-instructions.py <instruction file>...

Each argument is an instruction file without `applyTo`; its body is added as
session context. The files are named in the hook command rather than
discovered, because that is what makes `apm install` copy them next to this
script and rewrite their paths. A new always-on instruction therefore needs
adding to the command in `always-on-instructions.hook.json`.

Where it runs:

- Claude Code via `apm install`: silent, because APM already deploys the files
  as rules.
- Codex via `apm install`: injects once the hook is trusted in `/hooks`. APM
  writes no AGENTS.md there without `apm compile`.
- Copilot CLI via `apm install`: injects, since Copilot does not auto-apply an
  instruction without `applyTo`.
- Claude Code, Claude Desktop and Codex via a plugin: injects (Codex after the
  one-time hook trust), but packed bundles leave the hook inert until
  microsoft/apm#3074 ships. A bundle keeps the files under `instructions/`, so
  a path that does not resolve is looked up there under the plugin root.
- claude.ai, ChatGPT and cloud agents run no hooks; the marketplace's
  ALWAYS_ON_INSTRUCTIONS.md covers them.

Claude Code and Codex read `hookSpecificOutput.additionalContext`; Copilot CLI
reads a top-level `additionalContext`. The stdin payload tells them apart:
only the first two send `hook_event_name`.
"""

from __future__ import annotations

import json
import os
import sys
from itertools import pairwise
from pathlib import Path


def body_if_always_on(text: str) -> str | None:
    """The body of an instruction file without `applyTo`, else None."""
    if not text.startswith("---\n"):
        return text.strip() or None
    front, sep, body = text[4:].partition("\n---\n")
    if not sep or any(line.startswith("applyTo:") for line in front.splitlines()):
        return None
    return body.strip() or None


def resolve(path: str) -> Path | None:
    """The file itself, or its copy under a plugin bundle's instructions/."""
    candidate = Path(path)
    if candidate.is_file():
        return candidate
    root = os.environ.get("PLUGIN_ROOT") or os.environ.get("CLAUDE_PLUGIN_ROOT")
    if root and (bundled := Path(root) / "instructions" / candidate.name).is_file():
        return bundled
    return None


def deployed_as_claude_settings_hook() -> bool:
    """True for the copy `apm install` puts under .claude/hooks/."""
    parts = Path(__file__).resolve().parts
    return any(a == ".claude" and b == "hooks" for a, b in pairwise(parts))


def read_payload() -> dict[str, object]:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return {}
    return payload if isinstance(payload, dict) else {}


def main(paths: list[str]) -> int:
    if deployed_as_claude_settings_hook():
        return 0
    files = [f for p in paths if (f := resolve(p))]
    bodies = [b for f in files if (b := body_if_always_on(f.read_text(encoding="utf-8")))]
    if not bodies:
        return 0
    context = "\n\n".join(bodies)
    if "hook_event_name" in read_payload():
        output: dict[str, object] = {
            "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context}
        }
    else:
        output = {"additionalContext": context}
    json.dump(output, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
