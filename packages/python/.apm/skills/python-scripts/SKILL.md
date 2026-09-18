---
name: "python-scripts"
description: "Single-file Python script discipline: PEP 723 inline script metadata as the only way a script declares its dependencies, an executable shebang, locking for reproducibility, argument/stream/exit-code conventions, and the criteria for graduating a script into a project. ALWAYS invoke before creating or editing a standalone .py file that is run rather than imported — automation, a one-off, a tool, a CI helper. Do not write a script that assumes pre-installed packages, ships a sidecar requirements.txt, or tells the user to install anything globally. Runner-agnostic: uv is the default, but any PEP 723-aware runner satisfies the rule. Conventions for the code inside the script belong to `python-standards`; multi-file project tooling to `modern-python`. Keywords: script, standalone, one-off, automation, shebang, PEP 723, inline metadata, uv run, pipx, cli, argparse, exit code."
metadata:
  provenance:
    authoritativeSpec:
      - "https://packaging.python.org/en/latest/specifications/inline-script-metadata/"
      - "https://peps.python.org/pep-0723/"
      - "https://docs.astral.sh/uv/guides/scripts/"
      - "https://docs.python.org/3/library/argparse.html"
---

# Python Script Standards

A standalone script is a **self-contained, executable artifact**. Someone clones it, runs it, and it works — no README step, no virtualenv instructions, no "install these first". Everything below serves that property.

**Scope boundary.** How the code inside the script is written — typing, errors, data modelling, resources, logging — is owned by **`python-standards`**, which applies in full to a script body. Project bootstrap and tooling configuration are owned by the **`modern-python`** skill (APM dependency). This skill owns only the single-file form.

## 1. The hard rule: dependencies are declared in the file

Every standalone script that imports anything outside the standard library carries a PEP 723 inline metadata block. This is not a preference — it is what makes the file self-contained.

```python
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "httpx>=0.28",
#     "rich>=14",
# ]
# ///
```

Rules for the block:

- It is **TOML inside `#`-prefixed lines**, opened by `# /// script` and closed by `# ///`. A line that is just `#` is an empty line; every other line is `# ` followed by TOML.
- **Always set `requires-python`.** Without it the script silently runs on whatever interpreter happens to be first on `PATH`, including ones its syntax does not support.
- **`dependencies` always carries lower bounds** (`"httpx>=0.28"`). A bare name resolves to whatever is newest on the day someone runs it.
- Place it **after the shebang and before the module docstring** — at the top, where a reader looking for "what does this need" will find it.
- A script that imports nothing outside the standard library **does not need a block**. Add `requires-python` alone if the syntax needs a floor.

Three things this replaces, none of which belong beside a single file: a sidecar `requirements.txt`, a comment telling the reader to `pip install` something, and an implicit assumption that the package is already there.

## 2. The runner is the project's choice, not this skill's

`uv` is the default — it is the fastest and most widely installed — but the rule above is about the **file**, not the tool. Any runner that reads inline metadata satisfies it:

| Runner | Invocation |
|---|---|
| uv | `uv run script.py` |
| pipx | `pipx run script.py` |
| hatch, pdm, pixi | their own `run` entry points |
| pip (26+) | `pip install --requirements-from-script script.py`, then run it |

Use whichever the project or machine already standardises on. What is **not** acceptable at any tier: installing the script's dependencies into the ambient system interpreter, or running it with a bare `python script.py` that only works because the packages happen to be installed already.

See [inline-metadata.md](./references/inline-metadata.md) for the full field reference, alternate indexes, and per-runner detail.

## 3. Make it executable

A script that is run directly gets a shebang and the executable bit:

```python
#!/usr/bin/env -S uv run --script
```

`-S` is what lets `env` split the arguments so `uv` receives `run --script`; without it the whole string is treated as one program name. Then `chmod +x script.py`, and it runs as `./script.py`.

Add `--quiet` (`#!/usr/bin/env -S uv run --quiet --script`) when the script's own stdout is consumed by something else and the runner's progress output would contaminate it.

Skip the shebang for a script that is only ever invoked through its runner explicitly, or that ships in a repo where the runner is not guaranteed — a shebang naming a tool the user does not have produces a worse error than `uv run` does.

## 4. Reproducibility

Lower bounds keep a script working; they do not make two runs identical. Where the output matters — anything in CI, anything whose result is compared over time, anything shipped to someone else:

- **Lock it**: `uv lock --script script.py` writes a `script.py.lock` beside it, and subsequent runs resolve from that lock.
- Or **pin an upper bound** in the block for the dependency whose API you are actually exposed to.
- Or **bound resolution by date** with `--exclude-newer` for an audit-grade rerun.

A throwaway script needs none of this. A script that runs unattended needs one of them.

## 5. Structure

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx>=0.28"]
# ///
"""One line saying what this does and what it prints."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence


def fetch_report(url: str, *, timeout_seconds: float) -> Report:
    """The actual work — pure enough to call from a test or another script."""
    ...


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    ...
    args = parser.parse_args(argv)
    ...
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Why each piece:

- **`main(argv=None) -> int`** — takes its arguments instead of reading `sys.argv` directly, so it can be called from a test or another script with no subprocess.
- **`raise SystemExit(main())`** — propagates the exit code. A bare `main()` call discards it and the script always reports success.
- **A module docstring** that says what the script does *and what it outputs*, reused as the `--help` description.
- **The work in a named function**, not inline under `if __name__`. The `__main__` guard wires things up; it does not compute.

See [script-template.md](./references/script-template.md) for complete annotated examples.

## 6. Arguments, streams and exit codes

- **`argparse` from the standard library** is the default — it keeps the dependency list empty. Reach for `click` or `typer` once there are subcommands or more than roughly six options, and add it to the block.
- **stdout is the result; stderr is everything else.** Progress, warnings and diagnostics go to stderr, always. A script whose output is piped must not interleave chatter into it.
- **Exit codes mean something**: `0` success, non-zero failure, and distinct codes where a caller could plausibly branch on the reason. `130` on `KeyboardInterrupt`.
- **Fail loudly.** An unhandled exception with a traceback is better than a caught exception that prints a friendly message and returns `0`. Catch only what you can explain, and exit non-zero when you do.
- **Machine-readable output is a flag, not the default** (`--json`), unless the script exists to be piped.
- **Read secrets from the environment**, never from an argument — arguments appear in the process list and shell history.

## 7. Destructive scripts

Anything that deletes, overwrites, moves, publishes or mutates a remote system:

- **`--dry-run` that prints exactly what would happen, and make it the default** where the blast radius justifies it. `--apply`/`--yes` is the deliberate second step.
- **Idempotent where possible** — running it twice should not compound.
- **Report per item, and continue or stop explicitly.** A half-finished run must leave enough output to know where it stopped.
- **Never mutate anything before argument validation completes.**

## 8. Typing and testing, proportionally

Per `python-standards` §1, the tier decides the bar. For scripts specifically:

- **Every script**: annotate every function signature. A strict type checker is optional on a one-off.
- **A script anything else imports, or a shared `utils.py` sitting beside your scripts**: strict checking is strongly recommended. This is the tier where untyped code starts costing, and it arrives without announcing itself.
- **Testing is proportional.** Do not build a suite around a forty-line one-off. Do extract the logic into a function that *could* be called with fixed inputs — that shape costs nothing at write time and is what makes a test possible later.
- **A script that runs unattended, in CI, or that others depend on, gets tests** for its core function, even while it is still one file. Pytest can import a script that follows §5 directly.

## 9. When a script must become a project

Graduate it — hand off to `modern-python` for the project setup — when any of these is true:

- A second file needs to import it.
- It needs a lockfile, a CI pipeline and a versioned release.
- It needs to be installed as a command (`console_scripts` entry point) rather than run as a file.
- Its dependency list is long enough that resolution time is a real cost per run.
- It has grown past a few hundred lines, or holds more than one responsibility.
- Multiple scripts have begun sharing a `utils.py` — that shared file is already a package with no packaging.

Graduating is not a failure of the script form. Staying single-file past these points is.

## 10. Checklist

- [ ] Inline `# /// script` block present whenever anything non-stdlib is imported
- [ ] `requires-python` set; dependencies carry lower bounds
- [ ] No sidecar `requirements.txt`, no "run `pip install` first", no assumed global packages
- [ ] Shebang plus executable bit where the script is invoked directly
- [ ] Locked or bounded if it runs unattended or its output is compared over time
- [ ] `main(argv) -> int` with `raise SystemExit(main())`; work in named functions
- [ ] Module docstring says what it does and what it prints; reused in `--help`
- [ ] stdout carries results only; diagnostics on stderr; exit codes meaningful
- [ ] Destructive actions gated behind `--dry-run`/`--apply`
- [ ] Every signature annotated; strict checking if anything imports it
- [ ] Core logic callable with fixed inputs; tests if it runs unattended
- [ ] Still legitimately one file — check §9
- [ ] Body follows `python-standards`

## References

- **Inline metadata** — [field reference, runners, locking, indexes](./references/inline-metadata.md)
- **Templates** — [annotated script examples, minimal to unattended](./references/script-template.md)
- **Code conventions** — [`python-standards`](../python-standards/SKILL.md)
- **Project tooling** — the `modern-python` skill (APM dependency)
