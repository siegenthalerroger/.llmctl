---
name: "python-standards"
description: "Authoring conventions for Python source: typing discipline, data modelling, module and API boundaries, error handling, resource and subprocess safety, logging, and concurrency choice. ALWAYS invoke when writing, reviewing or refactoring .py files — modules, packages, tests, or the body of a script. Covers how the code reads, not how the project is tooled: uv/pyproject setup, linter and type-checker configuration, packaging, CI and migration off pip/Poetry belong to the `modern-python` skill; single-file script mechanics and PEP 723 inline metadata belong to `python-scripts`. Do not write or review Python without this skill. Keywords: python, typing, type hints, annotations, dataclass, protocol, exceptions, pathlib, asyncio, logging, subprocess, docstring, api design."
metadata:
  provenance:
    authoritativeSpec:
      - "https://typing.python.org/en/latest/spec/"
      - "https://docs.python.org/3/library/typing.html"
      - "https://peps.python.org/pep-0008/"
      - "https://peps.python.org/pep-0257/"
      - "https://peps.python.org/pep-0604/"
      - "https://peps.python.org/pep-0695/"
      - "https://docs.python.org/3/library/asyncio-task.html"
---

# Python Standards and Patterns

Conventions for the Python **source text** — what the code says, how it is shaped, and where its boundaries sit. The bar is higher than "passes review": prefer the version that makes a wrong call impossible over the version that checks for it.

Worked ✅/❌ examples live in `references/` and are linked from each section — load them on demand rather than reading them all up front.

**Scope boundary.** This skill does not configure anything. Project bootstrap, `pyproject.toml` sections, uv commands, linter and type-checker configuration, dependency groups, packaging, pre-commit, CI and migration off legacy tooling are owned by the **`modern-python`** skill installed as an APM dependency of this package. The single-file script form — PEP 723 inline metadata, shebangs, exit codes, graduation to a project — is owned by **`python-scripts`**. Invoke whichever others the task spans.

## 1. Set the strictness tier first

Three tiers, decided by what the file *is*, not by how long it took to write. Every later section reads against this.

| Tier | What it is | Typing | Tests |
|---|---|---|---|
| **One-off script** | Single file, run directly, not imported, disposable or personal | Annotate every signature; a strict checker is optional | A pure core function that *could* be tested; no suite |
| **Shared code** | A script others run, or any module a second file imports (a `utils.py` included) | Strict checking **strongly recommended** — this is where untyped code starts costing | Tests for the logic that is now depended on |
| **Project** | Multi-file package or application | Strict checking **required**, no exemptions carved for convenience | Required, with the project's coverage floor enforced in CI |

The dangerous tier is the middle one. A file becomes shared the moment something imports it; that is when annotations and a checker stop being polish and start being the contract. Treat "this started as a script" as history, not as an exemption.

## 2. Typing

Annotate every parameter, return and public attribute. An unannotated public signature is an incomplete definition, not a style choice.

- **Modern syntax only.** `X | None`, not `Optional[X]`. `list[str]`/`dict[str, int]`, not `typing.List`/`typing.Dict`. On 3.12+, the `type` statement for aliases and PEP 695 syntax for generic functions and classes.
- **No implicit `Optional`.** A parameter defaulting to `None` is typed `X | None` explicitly.
- **Accept wide, return narrow.** Parameters take the least specific type that works (`Iterable[str]`, `Sequence[int]`, `Mapping[str, int]`); returns state the concrete type (`list[str]`), because the caller has to work with what comes back.
- **`Any` is a defect, not a type.** It disables checking for everything downstream. Use `object` plus narrowing, a `TypeVar`, a `Protocol`, or an overload. Where `Any` is genuinely unavoidable (untyped third-party surface), confine it to one adapter function and annotate the boundary.
- **`Protocol` over inheritance for dependencies.** A function that needs "something with `.read()`" declares a `Protocol`; it does not demand a base class the caller must inherit.
- **Close the value space.** `Literal`, `Enum` or `Final` instead of free strings and magic numbers. A parameter that accepts three strings should accept exactly three.
- **Type-only imports go under `if TYPE_CHECKING:`** with `from __future__ import annotations` where the target version needs it — keeps import graphs from growing edges that exist only for the checker.
- **Narrow with `TypeIs`** (3.13+) rather than `TypeGuard` when the negative branch should narrow too; `TypeGuard` narrows only the positive branch and quietly leaves the `else` wide.
- **`@override`** (3.12+) on every method that overrides a base — it catches the rename that silently turns an override into a new method.
- **`# type: ignore` carries a code and a reason** (`# type: ignore[arg-type]  # upstream stub is wrong, see #123`). A bare ignore is an unbounded suppression.

See [typing.md](./references/typing.md) for ✅/❌ examples of each rule.

## 3. Data modelling

Make illegal states unrepresentable, then parse into that shape once at the edge.

- **Records are typed objects, not dicts.** `@dataclass(frozen=True, slots=True, kw_only=True)` is the default shape: immutable by default, cheap, and keyword-only so adding a field never silently reorders a call site. Reach for a plain mutable dataclass only where mutation is the point.
- **`dict[str, Any]` crossing a function boundary is a missing type.** It is acceptable as the immediate output of `json.loads` and nowhere else.
- **Parse, don't validate.** Convert external input (JSON, env, CLI, HTTP, DB rows) into typed objects at the boundary, once. Downstream code then receives something already known-good instead of re-checking the same fields.
- **A validation library belongs at trust boundaries only.** Use one where input is genuinely untrusted or the schema is externally owned; do not make internal plumbing depend on it.
- **`NamedTuple` for a positional value with no behaviour; `Enum` for a closed set; `TypedDict` only where a `dict` shape is forced on you** by an external format.

See [design.md](./references/design.md#data-modelling) for ✅/❌ examples.

## 4. Module and API boundaries

- **Separate the pure core from the I/O shell.** Computation goes in functions that take values and return values; reading files, calling networks, printing and mutating global state live in a thin outer layer that calls them. This single split is what makes code testable without mocks, and it is the strongest available quality lever.
- **No I/O, no network calls and no expensive work at import time.** A module body defines things; it does not do things.
- **No module-level mutable state.** Module globals are singletons with no lifecycle. Pass state explicitly, or hold it in an object the caller owns.
- **Declare the public surface.** `__all__` on any module meant to be imported from; a leading underscore on everything else. What is not exported can be changed freely — that is the point.
- **Absolute imports, no wildcards.** A circular import is a design error; fix the dependency direction rather than deferring the import into a function body.
- **Functions take what they use.** Passing a whole config object so the callee can read two fields couples them for no reason.

See [design.md](./references/design.md#module-and-api-boundaries) for ✅/❌ examples.

## 5. Functions and control flow

- **Never a mutable default argument** (`def f(items: list[str] = [])`). Use `None` and build inside, or a `field(default_factory=...)` on a dataclass.
- **Return early.** Guard clauses over nested `if`; the happy path stays at the left margin.
- **One return type.** A function that returns `Result | None | str` on different paths is three functions.
- **Comprehensions over `map`/`filter` with a `lambda`**; a generator where the sequence is large or lazily consumed; a plain loop where the comprehension would need two `for` clauses and a condition to stay readable.
- **`zip(..., strict=True)`** whenever the inputs are expected to be the same length — the default silently truncates to the shortest.
- **`enumerate`** instead of maintaining an index; `pathlib` instead of string path arithmetic.
- **`match` for dispatch on structure**, not as a substitute for an `if`/`elif` chain on one value.
- **Keyword-only parameters after the second argument**, and never a bare boolean positional: `render(data, strict=True)`, never `render(data, True)`.

## 6. Errors

- **Define the module's or package's own base exception**, and raise subclasses of it. Callers can then catch your failures without catching everything.
- **Never bare `except:`** (it swallows `KeyboardInterrupt` and `SystemExit`), and never `except Exception: pass`. `contextlib.suppress(SpecificError)` when ignoring is genuinely correct — it states which error is being ignored.
- **Chain the cause: `raise NewError(...) from err`.** Re-raising without `from` discards the traceback that explains what actually happened.
- **The message names the value.** `f"config key {key!r} missing from {path}"`, not `"invalid config"`. An error that cannot be acted on is a bug report the user has to write for you.
- **Catch narrowly and locally.** A `try` block wraps the one call that can fail, not the twenty lines around it.
- **Do not use exceptions for expected outcomes across a public boundary.** "Not found" is a return value; "the database is unreachable" is an exception.
- **Never log-and-re-raise the same error at every level.** Handle it once, at the level that can do something about it.

See [runtime.md](./references/runtime.md#errors) for ✅/❌ examples.

## 7. Resources, I/O and subprocesses

- **Every resource is acquired in a `with`.** Files, sockets, locks, pools, temporary directories. Write your own `contextlib.contextmanager` when a resource has a lifecycle.
- **`encoding=` is always explicit** on `open()` and on any text conversion. The platform default is not the same on every machine, which is exactly the class of bug that only appears in production.
- **`pathlib.Path` throughout**; `os.path` string handling only when an API forces it.
- **`subprocess.run` with an argument list and `check=True`.** Never `shell=True` with an interpolated string — that is a command-injection primitive. Capture output explicitly rather than letting it leak into the parent's streams.
- **`tempfile`** for scratch space, never a hardcoded `/tmp/...` path.
- **Close over the clock and the filesystem at the boundary** — a function that calls `datetime.now()` or reads `os.environ` in its core cannot be tested without patching. Pass the value in.

See [runtime.md](./references/runtime.md#resources-and-processes) for ✅/❌ examples.

## 8. Logging

- **`logger = logging.getLogger(__name__)` at module level; never `print` in importable code.** `print` writes to a stream the caller did not choose and cannot filter.
- **Lazy formatting: `logger.info("loaded %d rows from %s", n, path)`.** An f-string is formatted even when the level is disabled.
- **The library never configures logging.** No `basicConfig`, no handler installation, no level setting outside the application entry point.
- **`logger.exception(...)` inside an `except` block** — it attaches the traceback; `logger.error(str(err))` throws it away.
- **Never log secrets, tokens, credentials or whole request bodies.**

## 9. Concurrency

Pick the model from the workload, and do not mix models inside one boundary.

- **I/O-bound, many operations** → `asyncio` with structured concurrency: `asyncio.TaskGroup` (3.11+), not a bare list of `create_task` calls that nobody awaits. `asyncio.timeout` for deadlines.
- **I/O-bound, few operations, sync codebase** → `concurrent.futures.ThreadPoolExecutor`.
- **CPU-bound** → `ProcessPoolExecutor`. Threads will not help under the GIL; free-threaded builds exist but are not the default, so do not assume them.
- **Never call a blocking function from a coroutine.** `asyncio.to_thread` it, or the event loop stalls for every other task.
- **Shared mutable state needs an explicit lock, or should not be shared.** Prefer passing values through a queue over guarding a global.
- **Every task is awaited or explicitly cancelled.** A task nobody holds a reference to can be garbage-collected mid-flight, and its exception disappears with it.

See [runtime.md](./references/runtime.md#concurrency) for ✅/❌ examples.

## 10. Comments, docstrings and naming

- **Docstrings on public modules, classes and functions**: a one-line imperative summary, then `Args`/`Returns`/`Raises` only where the signature does not already say it. Never restate the types — the annotations carry them.
- **Comments explain *why*.** A comment that paraphrases the line below it is noise that will drift out of date. Comment the workaround, the constraint, the non-obvious ordering, the rejected alternative.
- **No commented-out code and no `TODO` without an owner or issue.**
- **Names carry units and intent**: `timeout_seconds`, not `timeout`; `is_expired`, not `flag`; `user_ids`, not `data`. No abbreviations beyond the universally known ones.

## 11. Security defaults

- Never `eval`, `exec`, or `pickle.loads` on input you did not produce.
- `secrets`, never `random`, for tokens, keys and anything an attacker should not predict.
- No credentials in source, in defaults, or in logs — read them from the environment or a secret store at the boundary.
- Parameterised queries only; no string-built SQL or shell commands.
- Validate and normalise any path derived from input before opening it.

## 12. Language level

Target the oldest version actually supported, and say so in one place (`requires-python`). New work with no constraint targets the current stable release. Do not carry compatibility shims for versions that have reached end of life — dropping them is a feature, not a regression. Where a rule above names a version (PEP 695 syntax on 3.12+, `TypeIs` on 3.13+), apply it only when the floor allows; otherwise use the older equivalent rather than a conditional import.

## 13. Quality checklist

Before calling Python work finished:

- [ ] Strictness tier identified, and typing/testing match it (§1)
- [ ] Every public signature annotated; no bare `Any`; no implicit `Optional`
- [ ] Every `# type: ignore` carries a code and a reason
- [ ] Records are dataclasses or enums, not dicts crossing boundaries
- [ ] External input parsed into typed objects once, at the edge
- [ ] Pure logic separated from I/O; no work at import time; no module-level mutable state
- [ ] `__all__` set, or everything internal underscored
- [ ] No mutable default arguments; no bare booleans passed positionally
- [ ] Failures raise a package-specific exception, chained with `from`, with the offending value in the message
- [ ] No bare `except`, no silent `pass`, no log-and-re-raise chains
- [ ] Every resource in a `with`; every `open()` has `encoding=`
- [ ] `subprocess` calls pass a list and `check=True`; no `shell=True` on interpolated input
- [ ] Module logger used; no `print` in importable code; no logging configuration in a library
- [ ] Concurrency model matches the workload; no blocking calls inside coroutines; every task awaited
- [ ] Docstrings explain intent, comments explain why; no commented-out code
- [ ] No secrets, no `eval`/`exec`/`pickle` on untrusted input, no string-built queries
- [ ] Formatter and linter are whatever the repo already uses; ruff if it has none (see §14)

## 14. Formatting and linting

**Follow the repository's existing convention.** If a project already runs black, flake8, pylint or isort, use it and do not migrate it as a side effect of unrelated work. A consistent codebase beats a fashionable one.

Where a project has no convention — a new project, or one with nothing configured — use **ruff** for both formatting and linting, and let the `modern-python` skill configure it. Neither tool is mandated by this skill: none of the rules above depend on which linter runs, and a formatter cannot produce any of the properties in §1–§11.

## References

- **Typing** — [modern syntax, variance, protocols, narrowing, ignores](./references/typing.md)
- **Design** — [data modelling, boundaries, functional core / imperative shell](./references/design.md)
- **Runtime** — [errors, resources, subprocesses, logging, concurrency](./references/runtime.md)
- **Project tooling** — the `modern-python` skill (APM dependency): uv, `pyproject.toml`, ruff/ty configuration, dependency groups, CI, migration
- **Single-file scripts** — [`python-scripts`](../python-scripts/SKILL.md): PEP 723 inline metadata, shebangs, exit codes, graduation criteria
