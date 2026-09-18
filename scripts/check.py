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

"Is this repo well-formed, and would it publish?" -- answered from one checkout,
because the marketplace-shaped gates pack into a scratch directory and validate
that. Gates run cheapest first, so an obvious failure reports fast. What each
one means, and what a skip means, is in CONTRIBUTING.md#continuous-integration.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import typer

import check_licenses
import commits as commitlib
import gates as gatelib
import gen_notices
import pack_marketplace
import workspace
from gates import Context, Gate, Need, Outcome, fail, ok

# Every entry script declares the same dependencies, so an edit to one header
# has to reach all of them or `uv run` resolves a different environment per
# script. The shared modules carry no header: the entry importing them supplies
# the dependencies.
ENTRY_SCRIPTS = ("check.py", "check_licenses.py", "check_steering.py",
                 "check_updates.py", "gen_notices.py", "pack_marketplace.py",
                 "release.py", "update.py", "versions.py")
HEADER_END = "# ///"


def sh(args: list[str], cwd: Path | str) -> subprocess.CompletedProcess:
    """errors="replace": these tools emit box-drawing and arrows, which the
    Windows console codepage cannot decode. A gate must not die on output it
    only prints."""
    return subprocess.run(args, cwd=str(cwd), capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def gate_scripts(ctx: Context) -> Outcome:
    """The tooling's own lint: identical headers, and no dead or broken code."""
    scripts = workspace.script("scripts")
    headers, problems = {}, []
    for name in ENTRY_SCRIPTS:
        path = scripts / name
        if not path.is_file():
            problems.append("%s is missing" % name)
            continue
        text = path.read_text(encoding="utf-8")
        if HEADER_END not in text:
            problems.append("%s has no PEP 723 header" % name)
            continue
        headers.setdefault(text.split(HEADER_END)[0], []).append(name)
    if len(headers) > 1:
        groups = ["{%s}" % ", ".join(names) for names in headers.values()]
        problems.append("the PEP 723 headers differ across %s -- every entry script "
                        "resolves its own environment, so they have to agree"
                        % " vs ".join(groups))

    broken = sh([sys.executable, "-m", "compileall", "-q", str(scripts)], ctx.repo)
    if broken.returncode != 0:
        problems.append((broken.stdout + broken.stderr).strip().split("\n")[-1][:200])

    note = "pyflakes skipped (--offline)"
    if not ctx.offline and shutil.which("uv"):
        lint = sh(["uv", "run", "--quiet", "--no-project", "--with", "pyflakes",
                   "python", "-m", "pyflakes", str(scripts)], ctx.repo)
        findings = [line for line in lint.stdout.split("\n") if line.strip()]
        if findings:
            problems.extend(findings[:3])
        note = "pyflakes clean"

    if problems:
        return fail("; ".join(problems[:3])[:300], problems=problems)
    return ok("%d entry script(s) share one header; %s" % (len(ENTRY_SCRIPTS), note))


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
    """Does every package's lockfile resolve exactly the pins its manifest declares?

    The only thing tying the two together. `apm install --frozen` checks that
    every dependency *is* in the lockfile, never *which commit*, so a moved pin
    with a stale lockfile passes it. This is a file comparison: no install, no
    network, so it holds offline and before anything is materialised.
    """
    packages = workspace.packages(ctx.repo)
    problems = []
    for package in packages:
        pins = workspace.pins_of(package.manifest)
        floating = [spec for spec in pins.values() if not workspace.SHA_RE.match(spec)]
        if floating:
            problems.append("%s: pins must be 40-hex commit SHAs, not %s"
                            % (package.directory, ", ".join(floating)))
        lock = workspace.read_lock(package.path / "apm.lock.yaml")
        if lock is None:
            problems.append("%s: no apm.lock.yaml -- packing installs from it, so "
                            "every package needs one even with no dependencies"
                            % package.directory)
            continue
        problems += ["%s: %s" % (package.directory, problem) for problem in
                     workspace.diff_pins(pins, workspace.locked_of(lock),
                                         gone="%s is pinned but not in the lockfile",
                                         new="%s is locked but no longer declared",
                                         moved="%s pinned at %s but locked at %s")]
    if problems:
        return fail("%d problem(s): %s" % (len(problems), "; ".join(problems[:3])[:300]),
                    problems=problems)
    return ok("%d package lockfile(s) match their pins" % len(packages))


def gate_pack(ctx: Context) -> Outcome:
    """Does every package still pack into a marketplace a host would accept?"""
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

        payload = pack_marketplace.pack_json(
            ["--dry-run", "--offline", "--check-versions"], marketplace)
        if not payload.get("ok", False):
            misaligned = [p for p in (payload.get("version_alignment") or {}).get("packages", [])
                          if not p.get("ok")]
            detail = "; ".join("%s: %s" % (p["path"], p.get("reason")) for p in misaligned) \
                or "; ".join(str(e) for e in payload.get("errors") or [])
            return fail("apm pack --check-versions rejected the marketplace: %s"
                        % detail[:250], errors=payload.get("errors"))

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
    Gate("scripts", "the release tooling lints and shares one header", gate_scripts),
    Gate("frontmatter", "customization frontmatter conventions", gate_frontmatter),
    Gate("commits", "conventional commits since --since", gate_commits,
         needs=(Need("git-range", "skip"),)),
    Gate("licences", "provenance obligations vs declared licences", gate_licences),
    Gate("lockfiles", "package lockfiles resolve exactly the declared pins", gate_lockfiles),
    Gate("pack", "every package packs into a valid marketplace", gate_pack,
         needs=(Need("apm", "fail"), Need("network", "skip"))),
]


def main(repo: Path = workspace.REPO_OPTION,
         since: str = typer.Option("", "--since", metavar="REF",
                                   help="Lint the commits in REF..HEAD. CI passes the "
                                        "pull request's base; without it that gate is skipped."),
         subject: str = typer.Option("", "--subject", metavar="TEXT",
                                     help="An extra subject to lint, such as a pull request title."),
         only: list[str] = typer.Option([], "--only", help="Run only these gates."),
         skip_: list[str] = typer.Option([], "--skip", help="Skip these gates."),
         offline: bool = typer.Option(False, "--offline",
                                      help="Skip the gates that need the network."),
         json_out: bool = typer.Option(False, "--json",
                                       help="Machine-readable summary on stdout.")) -> None:
    """Run every gate over one workspace. Exit 1 if any failed."""
    try:
        runner = gatelib.Runner(GATES, only=only, skip_keys=skip_, json_out=json_out)
    except ValueError as exc:
        raise typer.BadParameter(str(exc))
    ctx = Context(repo=repo.resolve(), since=since or None, subject=subject or None,
                  offline=offline)
    raise typer.Exit(runner.run(ctx))


if __name__ == "__main__":
    typer.run(main)
