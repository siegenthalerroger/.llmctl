#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "ruamel.yaml==0.19.1",
#   "typer==0.27.2",
#   "rich==15.0.0",
#   "httpx==0.28.1",
#   "python-frontmatter==1.3.0",
# ]
# [tool.uv]
# exclude-newer = "2026-09-18T00:00:00Z"
# ///
"""Every gate, in one place. Writes nothing to the workspace.

These gates answer "is this repo well-formed, and would it publish?". They read
the workspace only -- the marketplace-shaped ones pack into a scratch directory
and validate that -- so a contributor with no marketplace clone, and a CI job
that checks out one repo, run the full set rather than a silently reduced one.

Gates, cheapest first so an obvious failure reports fast:

  frontmatter  .apm/hooks/validate-customization-frontmatter.py --all -- the
               same rules the edit-time hook applies, over the whole tree
  commits      every commit in --since..HEAD (and the --subject, if given) is
               conventional, and a scope names something the commit touched.
               Skipped, not failed, when no --since was given
  licences     scripts/check_licenses.py -- every file's licence can carry the
               upstream terms its provenance records, and no provenance block
               parses to nothing
  lockfiles    packages/*/apm.lock.yaml exists and resolves exactly the pins in
               apm.yml. This is the only thing that ties the two together:
               `apm install --frozen` checks that every dependency *is* in the
               lockfile, never *which commit* -- a moved pin with a stale
               lockfile passes --frozen and packs the old commit
  pack         every package packs into a scratch marketplace from its committed
               lockfile; that marketplace passes `apm pack --check-versions`,
               every bundle passes `claude plugin validate` (when the CLI is
               present), and the notices carry no unrecorded upstream. This is
               the deployability check

Usage:
  uv run scripts/check.py --repo PATH [--since REF] [--subject TEXT]
                          [--only KEY]... [--skip KEY]... [--offline] [--json]

  --since    the commit range to lint is REF..HEAD (CI passes the PR base)
  --subject  an extra subject to lint, e.g. the pull request title
  --offline  skip gates that need the network (the pack gate installs each
             package's pinned upstreams)

Exit codes: 0 all gates pass or were skipped, 1 one or more failed.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import typer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_licenses  # noqa: E402
import commits as commitlib  # noqa: E402
import gates as gatelib  # noqa: E402
import gen_notices  # noqa: E402
import pack_marketplace  # noqa: E402
import workspace  # noqa: E402
from gates import Context, Gate, Need, Outcome, fail, ok  # noqa: E402


def sh(args, cwd) -> subprocess.CompletedProcess:
    """errors="replace": these tools emit box-drawing and arrows, which the
    Windows console codepage cannot decode. A gate must not die on output it
    only prints."""
    return subprocess.run(args, cwd=str(cwd), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def gate_frontmatter(ctx: Context) -> Outcome:
    """The edit-time hook's rules, applied to every file rather than one.

    Still a subprocess, deliberately: the hook is deployed on its own by APM
    and runs under plain python3, so it stays stdlib and is not imported here.
    """
    got = sh([sys.executable,
              str(workspace.script(".apm", "hooks", "validate-customization-frontmatter.py")),
              "--repo", str(ctx.repo), "--all"], ctx.repo)
    lines = [line.strip() for line in (got.stdout + got.stderr).split("\n") if line.strip()]
    if got.returncode == 0:
        return ok(lines[-1].replace("[customization-frontmatter] ", "") if lines else "")
    errors = [line for line in lines if "error:" in line]
    return fail("; ".join(errors[:3])[:300], errors=errors)


def gate_commits(ctx: Context) -> Outcome:
    checked, findings = commitlib.lint(ctx.repo, ctx.since, ctx.subject)
    if findings:
        shown = ["%s %s: %s" % (f.sha[:7], f.subject[:50], f.reason) for f in findings[:3]]
        return fail("%d of %d commit(s) break the convention: %s"
                    % (len(findings), checked, "; ".join(shown)),
                    findings=[f._asdict() for f in findings])
    return ok("%d commit(s) since %s%s" % (checked, ctx.since,
                                          ", plus the subject" if ctx.subject else ""))


def gate_licences(ctx: Context) -> Outcome:
    report = check_licenses.check(ctx.repo)
    if report.errors:
        return fail("%d error(s): %s" % (len(report.errors),
                                        "; ".join("%s: %s" % e for e in report.errors[:2])[:250]),
                    errors=[{"file": f, "message": m} for f, m in report.errors])
    return ok(check_licenses.summary(report),
              warnings=[{"file": f, "message": m} for f, m in report.warnings])


def gate_lockfiles(ctx: Context) -> Outcome:
    problems = []
    for package in workspace.packages(ctx.repo):
        lock_path = package.path / "apm.lock.yaml"
        try:
            pins = workspace.pins_of(package.manifest)
        except ValueError as exc:
            problems.append("%s: %s" % (package.directory, exc))
            continue
        bad = [spec for (_, _), spec in pins.items() if not workspace.SHA_RE.match(spec)]
        if bad:
            problems.append("%s: pins must be 40-hex commit SHAs, not %s"
                            % (package.directory, ", ".join(bad)))
        lock = workspace.read_lock(lock_path)
        if lock is None:
            problems.append("%s: no apm.lock.yaml -- packing installs from it, so "
                            "every package needs one even with no dependencies"
                            % package.directory)
            continue
        locked = workspace.locked_of(lock)
        for key in sorted(set(pins) | set(locked)):
            label = "%s%s" % (key[0], "/" + key[1] if key[1] else "")
            if key not in locked:
                problems.append("%s: %s is pinned but not in the lockfile"
                                % (package.directory, label))
            elif key not in pins:
                problems.append("%s: %s is locked but no longer declared"
                                % (package.directory, label))
            elif pins[key].lower() != locked[key].lower():
                problems.append("%s: %s pinned at %s but locked at %s"
                                % (package.directory, label, pins[key][:12], locked[key][:12]))
    if problems:
        return fail("%d problem(s): %s" % (len(problems), "; ".join(problems[:3])[:300]),
                    problems=problems)
    return ok("%d package lockfile(s) match their pins" % len(workspace.packages(ctx.repo)))


def gate_pack(ctx: Context) -> Outcome:
    packages = workspace.packages(ctx.repo)
    versions = {p.name: "0.0.0" for p in packages}
    notes = []
    with tempfile.TemporaryDirectory(prefix="llmctl-check-") as tmp:
        marketplace = Path(tmp) / "marketplace"
        try:
            pack_marketplace.pack_all(ctx.repo, marketplace, versions, set(versions),
                                      scratch=Path(tmp) / "scratch", source="worktree",
                                      log=lambda *_: None)
        except pack_marketplace.PackError as exc:
            return fail(str(exc).strip().split("\n")[0][:300], error=str(exc))

        got = sh(["apm", "pack", "--dry-run", "--offline", "--check-versions"], marketplace)
        if got.returncode != 0:
            tail = [line.strip() for line in got.stdout.split("\n") if line.strip()][-3:]
            return fail("apm pack --check-versions exited %d: %s"
                        % (got.returncode, "; ".join(tail)[:250]))

        if shutil.which("claude"):
            bad = []
            for bundle in sorted((marketplace / "plugins").iterdir()):
                got = sh(["claude", "plugin", "validate", "."], bundle)
                if got.returncode != 0:
                    bad.append("%s: %s" % (bundle.name, (got.stderr or got.stdout).strip()[:90]))
            if bad:
                return fail("claude plugin validate: %s" % "; ".join(bad)[:300])
            notes.append("%d bundle(s) validated" % len(packages))
        else:
            notes.append("claude CLI absent; bundles not validated")

        text = (marketplace / "THIRD-PARTY-NOTICES.md").read_text(encoding="utf-8")
        missing = gen_notices.unrecorded(text)
        if missing:
            return fail("no licence recorded in dependency-licenses.yml for %s"
                        % ", ".join(missing))
    return ok("%d package(s) packed from their lockfiles; %s"
              % (len(packages), "; ".join(notes)))


GATES = [
    Gate("frontmatter", "customization frontmatter conventions", gate_frontmatter),
    Gate("commits", "conventional commits since --since", gate_commits,
         needs=(Need("git-range", "skip"),)),
    Gate("licences", "provenance obligations vs declared licences", gate_licences),
    Gate("lockfiles", "package lockfiles resolve exactly the declared pins", gate_lockfiles),
    Gate("pack", "every package packs into a valid marketplace", gate_pack,
         needs=(Need("apm", "fail"), Need("network", "skip"))),
]


def main(repo: Path = workspace.REPO_OPTION,
         since: str = typer.Option("", "--since", help="lint commits in REF..HEAD"),
         subject: str = typer.Option("", "--subject", help="an extra subject to lint"),
         only: list[str] = typer.Option([], "--only", help="run only these gates"),
         skip_: list[str] = typer.Option([], "--skip", help="skip these gates"),
         offline: bool = typer.Option(False, "--offline", help="skip gates needing the network"),
         json_out: bool = typer.Option(False, "--json", help="machine-readable summary on stdout")) -> None:
    try:
        runner = gatelib.Runner(GATES, only=only, skip_keys=skip_, json_out=json_out)
    except ValueError as exc:
        raise typer.BadParameter(str(exc))
    ctx = Context(repo=repo.resolve(), since=since or None, subject=subject or None,
                  offline=offline)
    raise typer.Exit(runner.run(ctx))


if __name__ == "__main__":
    typer.run(main)
