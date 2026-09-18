# Inline Script Metadata Reference

Detail for [python-scripts §1–§4](../SKILL.md#1-the-hard-rule-dependencies-are-declared-in-the-file). The format is PEP 723, maintained as the *inline script metadata* specification in the Python packaging specs; the tools below are implementations of it, not the standard itself.

## The block

```python
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "httpx>=0.28",
#     "rich>=14",
# ]
# ///
```

Mechanics that actually bite:

- The opening line is exactly `# /// script` and the closing line exactly `# ///`.
- Every content line is `#` followed by a single space and then TOML, or a bare `#` for a blank line. A missing space is a parse failure.
- Only **one** `script` block per file.
- Anything before it in the file is fine (a shebang, a comment); convention is shebang → block → docstring.
- The block is inert to the interpreter — it is comments. Running the file with a plain interpreter ignores it entirely, which is exactly why a runner is needed.

## Fields

| Field | Required | Notes |
|---|---|---|
| `requires-python` | Always set it | A PEP 508 specifier, e.g. `">=3.12"`. Decides which interpreter the runner provisions. |
| `dependencies` | When anything non-stdlib is imported | A list of PEP 508 requirement strings. Always carry lower bounds. |
| `[tool.<name>]` | Optional | Tool-specific tables, e.g. `[tool.uv]` for index configuration. Other runners ignore tables that are not theirs. |

## Writing the block with tooling

Prefer letting the tool edit it — it keeps the TOML valid and resolves the specifier for you:

```bash
uv init --script report.py --python 3.12     # scaffold a new script with the block
uv add --script report.py httpx rich          # add dependencies to an existing script
uv remove --script report.py rich             # remove one
```

## Running

| Runner | Command | Notes |
|---|---|---|
| uv | `uv run report.py` | Resolves and caches an environment per dependency set; re-runs are near-instant. |
| uv (explicit) | `uv run --script report.py` | Forces script mode; what the shebang uses. |
| pipx | `pipx run report.py` | Reads the same block. |
| hatch / pdm / pixi | their own `run` entry points | pixi extends the block with `[tool.pixi]` for conda channels. |
| pip 26+ | `pip install --requirements-from-script report.py` | Installs the declared dependencies into the *current* environment without running the script. Use only when that environment is one you control. |

Ad-hoc extras for a single invocation, without editing the file: `uv run --with ipdb report.py`. Do not use this as a substitute for declaring a real dependency — the next person will not know to pass it.

## Locking and reproducibility

```bash
uv lock --script report.py       # writes report.py.lock beside the script
uv run --script report.py        # subsequent runs resolve from the lock
```

Alternatives when a lockfile is not wanted:

- **Upper bounds** in the block for the dependency whose API you consume directly: `"httpx>=0.28,<0.29"`.
- **`--exclude-newer 2026-09-01`** to resolve as of a date, for an audit-grade rerun of an old script.

## Alternate indexes

Private or supplementary indexes go in a tool table inside the block, so the script stays self-contained:

```python
# /// script
# requires-python = ">=3.12"
# dependencies = ["internal-client>=2"]
#
# [tool.uv]
# extra-index-url = ["https://pypi.internal.example/simple"]
# ///
```

Credentials never go in the block. Supply them through the runner's environment variables.

## Limits

- It declares **dependencies**, not packaging. A script cannot be `pip install`ed, cannot expose a console entry point, and has no version. Those are the graduation signals in [§9](../SKILL.md#9-when-a-script-must-become-a-project).
- Resolution happens per unique dependency set. A long list costs real time on the first run of each new set, though runners cache aggressively afterwards.
- A checker or editor that does not understand the block will report the imports as unresolved. Type checkers with script support (ty among them) resolve the block's dependencies separately from any surrounding project environment.
