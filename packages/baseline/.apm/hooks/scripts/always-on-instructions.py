"""SessionStart hook: add a plugin's always-on instructions to the session context.

No plugin format loads instruction files, so a plugin install would otherwise
never see them. An always-on instruction is one without `applyTo`; the hook
prints those as `additionalContext`, the SessionStart output Claude Code and
Codex both read.

It emits only from inside a plugin bundle. `apm install` copies this script
into the harness config, where no plugin manifest sits above it, and deploys
the instructions natively instead.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

MANIFESTS = (".claude-plugin/plugin.json", ".codex-plugin/plugin.json")


def plugin_root() -> Path | None:
    """The bundle this script runs from, or None outside a plugin."""
    candidates = [Path(__file__).resolve().parent, *Path(__file__).resolve().parents]
    if root := os.environ.get("CLAUDE_PLUGIN_ROOT"):
        candidates.insert(0, Path(root))
    for candidate in candidates:
        if any((candidate / manifest).is_file() for manifest in MANIFESTS):
            return candidate
    return None


def body_if_always_on(text: str) -> str | None:
    """The body of an instruction file without `applyTo`, else None."""
    if not text.startswith("---\n"):
        return text.strip() or None
    front, sep, body = text[4:].partition("\n---\n")
    if not sep or any(line.startswith("applyTo:") for line in front.splitlines()):
        return None
    return body.strip() or None


def main() -> int:
    root = plugin_root()
    if root is None:
        return 0
    files = sorted((root / "instructions").glob("*.instructions.md"))
    bodies = [b for f in files if (b := body_if_always_on(f.read_text(encoding="utf-8")))]
    if not bodies:
        return 0
    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": "\n\n".join(bodies),
        }
    }
    json.dump(output, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
