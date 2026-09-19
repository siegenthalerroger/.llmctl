"""The gate registry and runner behind check.py.

A gate is a function of the run context returning an Outcome. Gates never raise
and never exit: the runner turns an exception into a failure and owns the exit
code, so one failure does not hide the gates behind it. A gate declares what it
needs; a missing need either fails it or skips it with the reason printed, so a
skip is never silent and never green-by-omission.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import traceback
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from rich.console import Console

from .workspace import git

__all__ = ["Context", "Gate", "Need", "Outcome", "Runner", "Status", "fail", "ok", "skip"]

Status = Literal["pass", "fail", "skip"]
NeedName = Literal["apm", "network", "git-range"]


@dataclass(frozen=True)
class Outcome:
    status: Status
    detail: str = ""
    data: dict = field(default_factory=dict)


def ok(detail: str = "", **data) -> Outcome:
    return Outcome("pass", detail, data)


def fail(detail: str, **data) -> Outcome:
    return Outcome("fail", detail, data)


def skip(reason: str, **data) -> Outcome:
    return Outcome("skip", reason, data)


@dataclass(frozen=True)
class Need:
    name: NeedName
    on_missing: Literal["fail", "skip"] = "fail"


@dataclass
class Context:
    repo: Path
    since: str | None = None
    subject: str | None = None
    offline: bool = False
    console: Console = field(default_factory=lambda: Console(stderr=True))
    available: dict[str, tuple[bool, str]] = field(default_factory=dict)


@dataclass(frozen=True)
class Gate:
    key: str
    title: str
    run: Callable[[Context], Outcome]
    needs: tuple[Need, ...] = ()


def probe(ctx: Context) -> dict[str, tuple[bool, str]]:
    """What each need resolves to in this run -> {need: (available, why not)}."""
    found = {
        "apm": (shutil.which("apm") is not None, "apm is not on PATH"),
        "network": (not ctx.offline, "--offline"),
    }
    if not ctx.since:
        found["git-range"] = (False, "no --since ref given")
    else:
        resolved = git(
            ["rev-parse", "--verify", "--quiet", f"{ctx.since}^{{commit}}"], ctx.repo, check=False
        )
        found["git-range"] = (bool(resolved), f"ref {ctx.since!r} not found")
    return found


STYLE = {"pass": "green", "fail": "bold red", "skip": "yellow"}
LABEL = {"pass": "pass", "fail": "FAIL", "skip": "skipped"}


class Runner:
    def __init__(
        self,
        gates: Sequence[Gate],
        *,
        only: Sequence[str] = (),
        skip_keys: Sequence[str] = (),
        json_out: bool = False,
    ) -> None:
        keys = [g.key for g in gates]
        for key in list(only) + list(skip_keys):
            if key not in keys:
                raise ValueError("unknown gate {!r}; valid: {}".format(key, ", ".join(keys)))
        self.gates = gates
        self.only = set(only)
        self.skip = set(skip_keys)
        self.json_out = json_out
        self.rows: list[dict] = []

    def run(self, ctx: Context) -> int:
        ctx.available = probe(ctx)
        ctx.console.print(f"check: {ctx.repo}")
        for gate in self.gates:
            if self.only and gate.key not in self.only:
                continue
            ctx.console.print(f"- [bold]{gate.key:<12}[/] {gate.title}")
            self._record(ctx, gate, self._outcome(ctx, gate))
        return self.report(ctx)

    def _outcome(self, ctx: Context, gate: Gate) -> Outcome:
        if gate.key in self.skip:
            return skip("skipped by --skip")
        for need in gate.needs:
            available, why = ctx.available.get(need.name, (False, "unknown need"))
            if available:
                continue
            reason = f"needs {need.name}: {why}"
            return skip(reason) if need.on_missing == "skip" else fail(reason)
        try:
            return gate.run(ctx)
        except Exception as exc:  # a gate must not take the run down
            if os.environ.get("LLMCTL_DEBUG"):
                traceback.print_exc()
            return fail((f"{type(exc).__name__}: {exc}")[:200])

    def _record(self, ctx: Context, gate: Gate, outcome: Outcome) -> None:
        detail = (
            (f"  ({outcome.detail})")
            if outcome.status == "pass" and outcome.detail
            else (f"  {outcome.detail}" if outcome.detail else "")
        )
        ctx.console.print(
            f"  [{STYLE[outcome.status]}]{LABEL[outcome.status]}[/]{detail}", highlight=False
        )
        self.rows.append(
            {
                "key": gate.key,
                "title": gate.title,
                "status": outcome.status,
                "detail": outcome.detail,
                "data": outcome.data,
            }
        )

    def report(self, ctx: Context) -> int:
        failed = [r["key"] for r in self.rows if r["status"] == "fail"]
        skipped = [r["key"] for r in self.rows if r["status"] == "skip"]
        ctx.console.print("")
        if failed:
            ctx.console.print(
                "[bold red]{} gate(s) failed:[/] {}".format(len(failed), ", ".join(failed))
            )
        else:
            ctx.console.print(
                "[green]all gates pass[/]"
                + (" (skipped: {})".format(", ".join(skipped)) if skipped else "")
            )
        if self.json_out:
            json.dump(
                {"repo": str(ctx.repo), "since": ctx.since, "ok": not failed, "gates": self.rows},
                sys.stdout,
                indent=2,
            )
            sys.stdout.write("\n")
        return 1 if failed else 0
