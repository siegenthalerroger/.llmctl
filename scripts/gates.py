"""The gate registry and runner behind check.py.

A gate is a function of the run context returning an Outcome -- pass, fail or
skip, each with one line of detail. Gates never raise and never exit: the runner
converts an exception into a failure and owns the exit code, so one failure does
not hide the gates behind it.

Each gate declares what it needs. A missing need either fails the gate (a tool
the gate cannot do without) or skips it with the reason printed (a range the
caller did not supply, a network the caller switched off). Skips never fail the
run, but they are never silent either: the detail says why, and the JSON output
carries it, so a CI log cannot report green on a gate that did not run.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Literal, Sequence

from rich.console import Console

from workspace import git

Status = Literal["pass", "fail", "skip"]
NeedName = Literal["apm", "claude", "network", "git-range", "github-token"]


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
    available: dict = field(default_factory=dict)


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
        "claude": (shutil.which("claude") is not None, "claude CLI is not on PATH"),
        "network": (not ctx.offline, "--offline"),
        "github-token": (bool(os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")),
                         "GITHUB_TOKEN/GH_TOKEN not set"),
    }
    if not ctx.since:
        found["git-range"] = (False, "no --since ref given")
    else:
        resolved = git(["rev-parse", "--verify", "--quiet", "%s^{commit}" % ctx.since],
                       ctx.repo, check=False)
        found["git-range"] = (bool(resolved), "ref %r not found" % ctx.since)
    return found


STYLE = {"pass": "green", "fail": "bold red", "skip": "yellow"}


class Runner:
    def __init__(self, gates: Sequence[Gate], *, only: Sequence[str] = (),
                 skip_keys: Sequence[str] = (), json_out: bool = False):
        keys = [g.key for g in gates]
        for key in list(only) + list(skip_keys):
            if key not in keys:
                raise ValueError("unknown gate %r; valid: %s" % (key, ", ".join(keys)))
        self.gates = gates
        self.only = set(only)
        self.skip = set(skip_keys)
        self.json_out = json_out
        self.rows: list[dict] = []

    def run(self, ctx: Context) -> int:
        console = ctx.console
        ctx.available = probe(ctx)
        console.print("check: %s" % ctx.repo)
        for gate in self.gates:
            if self.only and gate.key not in self.only:
                continue
            if gate.key in self.skip:
                self._record(console, gate, skip("skipped by --skip"))
                continue
            outcome = self._blocked(ctx, gate)
            if outcome is None:
                console.print("- [bold]%-12s[/] %s" % (gate.key, gate.title))
                try:
                    outcome = gate.run(ctx)
                except SystemExit as exc:
                    outcome = fail("exited %s" % exc.code)
                except Exception as exc:  # a gate must not take the run down
                    outcome = fail(("%s: %s" % (type(exc).__name__, exc))[:200])
                    if os.environ.get("LLMCTL_DEBUG"):
                        traceback.print_exc()
            else:
                console.print("- [bold]%-12s[/] %s" % (gate.key, gate.title))
            self._record(console, gate, outcome, announced=True)
        return self.report(ctx)

    def _blocked(self, ctx: Context, gate: Gate) -> Outcome | None:
        for need in gate.needs:
            available, why = ctx.available.get(need.name, (False, "unknown need"))
            if available:
                continue
            if need.on_missing == "skip":
                return skip("needs %s: %s" % (need.name, why))
            return fail("needs %s: %s" % (need.name, why))
        return None

    def _record(self, console: Console, gate: Gate, outcome: Outcome,
                announced: bool = False) -> None:
        if not announced:
            console.print("- [bold]%-12s[/] %s" % (gate.key, gate.title))
        label = {"pass": "pass", "fail": "FAIL", "skip": "skipped"}[outcome.status]
        detail = ("  (%s)" % outcome.detail) if outcome.status == "pass" and outcome.detail \
            else ("  %s" % outcome.detail if outcome.detail else "")
        console.print("  [%s]%s[/]%s" % (STYLE[outcome.status], label, detail),
                      highlight=False)
        self.rows.append({"key": gate.key, "title": gate.title,
                          "status": outcome.status, "detail": outcome.detail,
                          "data": outcome.data})

    def report(self, ctx: Context) -> int:
        failed = [r["key"] for r in self.rows if r["status"] == "fail"]
        skipped = [r["key"] for r in self.rows if r["status"] == "skip"]
        ctx.console.print("")
        if failed:
            ctx.console.print("[bold red]%d gate(s) failed:[/] %s"
                              % (len(failed), ", ".join(failed)))
        else:
            ctx.console.print("[green]all gates pass[/]"
                              + (" (skipped: %s)" % ", ".join(skipped) if skipped else ""))
        if self.json_out:
            json.dump({"repo": str(ctx.repo), "since": ctx.since, "ok": not failed,
                       "gates": self.rows}, sys.stdout, indent=2)
            sys.stdout.write("\n")
        return 1 if failed else 0
