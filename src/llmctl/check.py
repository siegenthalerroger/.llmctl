"""Every gate, in one place. Writes nothing to the workspace.

"Is this repo well-formed, and would it publish?" -- answered from one checkout,
because the marketplace-shaped gates pack into a scratch directory and validate
that. Gates run cheapest first, so an obvious failure reports fast. What each
one means, and what a skip means, is in CONTRIBUTING.md#continuous-integration.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import typer

from . import check_frontmatter, check_licenses, gen_notices, pack_marketplace, workspace
from . import commits as commitlib
from . import gates as gatelib
from .gates import Context, Gate, Need, Outcome, fail, ok, skip


def sh(args: list[str], cwd: Path | str) -> subprocess.CompletedProcess:
    """errors="replace": these tools emit box-drawing and arrows, which the
    Windows console codepage cannot decode. A gate must not die on output it
    only prints."""
    return subprocess.run(
        args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def gate_tooling(ctx: Context) -> Outcome:
    """The tooling's own lint: locked, formatted, linted and type-checked.

    Only a checkout of the project can answer any of that: ruff and ty read
    their configuration out of pyproject.toml, and `uv.lock` only exists beside
    it. A workspace running the tooling from git holds none of those, so the
    gate says so and skips rather than linting an installed copy against
    default rules it was never written for.
    """
    package = Path(__file__).resolve().parent
    project = package.parents[1]

    if not (project / "pyproject.toml").is_file():
        return skip(f"the tooling is installed, not checked out ({package})")
    if ctx.offline:
        return skip("--offline: ruff and ty are resolved from the lockfile")
    if not shutil.which("uv"):
        return skip("uv is not on PATH")

    problems, notes = [], []
    for args, note, wrong in (
        (
            ["lock", "--check"],
            "uv.lock matches pyproject.toml",
            "uv.lock does not match pyproject.toml; run `uv lock`",
        ),
        (
            ["run", "--locked", "--quiet", "ruff", "format", "--check", "src/"],
            "ruff format clean",
            "ruff format --check: run `uv run ruff format src/`",
        ),
        (
            ["run", "--locked", "--quiet", "ruff", "check", "--quiet", "src/"],
            "ruff clean",
            "ruff check",
        ),
        (["run", "--locked", "--quiet", "ty", "check", "src/"], "ty clean", "ty check"),
    ):
        result = sh(["uv", *args], project)
        if result.returncode == 0:
            notes.append(note)
            continue
        lines = [line for line in (result.stdout + result.stderr).split("\n") if line.strip()]
        problems.append(f"{wrong}: {lines[-1].strip()}" if lines else wrong)

    if problems:
        return fail("; ".join(problems)[:300], problems=problems)
    return ok("; ".join(notes))


def gate_frontmatter(ctx: Context) -> Outcome:
    """The edit-time hook's rules, applied to the whole tree rather than one file.

    The hook validates what a session just wrote; this validates everything,
    including files no session has touched and rules added after they were
    written. Same code either way -- the hook runs the same command.
    """
    report = check_frontmatter.check(ctx.repo)
    if report.errors:
        shown = "; ".join("{}: {}".format(*pair) for pair in report.errors[:3])
        return fail(
            f"{len(report.errors)} error(s): {shown[:250]}",
            errors=[{"file": f, "message": m} for f, m in report.errors],
        )
    return ok(
        check_frontmatter.summary(report),
        warnings=[{"file": f, "message": m} for f, m in report.warnings],
    )


def gate_commits(ctx: Context) -> Outcome:
    checked, findings = commitlib.lint(ctx.repo, ctx.since, ctx.subject)
    if findings:
        shown = "; ".join(f"{f.sha[:7]} {f.subject[:50]}: {f.reason}" for f in findings[:3])
        return fail(
            f"{len(findings)} of {checked} commit(s) break the convention: {shown}",
            findings=[f._asdict() for f in findings],
        )
    subject = ", plus the subject" if ctx.subject else ""
    return ok(f"{checked} commit(s) since {ctx.since}{subject}")


def gate_licences(ctx: Context) -> Outcome:
    report = check_licenses.check(ctx.repo)
    if report.errors:
        shown = "; ".join("{}: {}".format(*e) for e in report.errors[:2])
        return fail(
            f"{len(report.errors)} error(s): {shown[:250]}",
            errors=[{"file": f, "message": m} for f, m in report.errors],
        )
    return ok(
        check_licenses.summary(report),
        warnings=[{"file": f, "message": m} for f, m in report.warnings],
    )


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
            problems.append(
                "{}: pins must be 40-hex commit SHAs, not {}".format(
                    package.directory, ", ".join(floating)
                )
            )
        lock = workspace.read_lock(package.path / "apm.lock.yaml")
        if lock is None:
            problems.append(
                f"{package.directory}: no apm.lock.yaml -- packing installs from it, so "
                "every package needs one even with no dependencies"
            )
            continue
        problems += [
            f"{package.directory}: {problem}"
            for problem in workspace.diff_pins(
                pins,
                workspace.locked_of(lock),
                gone="%s is pinned but not in the lockfile",
                new="%s is locked but no longer declared",
                moved="%s pinned at %s but locked at %s",
            )
        ]
    if problems:
        shown = "; ".join(problems[:3])
        return fail(f"{len(problems)} problem(s): {shown[:300]}", problems=problems)
    return ok(f"{len(packages)} package lockfile(s) match their pins")


def gate_pack(ctx: Context) -> Outcome:
    """Does every package still pack into a marketplace a host would accept?"""
    packages = workspace.packages(ctx.repo)
    versions = {p.name: "0.0.0" for p in packages}
    notes = []
    with tempfile.TemporaryDirectory(prefix="llmctl-check-") as tmp:
        marketplace = Path(tmp) / "marketplace"
        try:
            pack_marketplace.pack_all(
                ctx.repo,
                marketplace,
                versions,
                set(versions),
                scratch=Path(tmp) / "scratch",
                source="worktree",
                log=lambda *_: None,
            )
        except pack_marketplace.PackError as exc:
            return fail(str(exc).strip().split("\n")[0][:300], error=str(exc))

        payload = pack_marketplace.pack_json(
            ["--dry-run", "--offline", "--check-versions"], marketplace
        )
        if not payload.get("ok", False):
            misaligned = [
                p
                for p in (payload.get("version_alignment") or {}).get("packages", [])
                if not p.get("ok")
            ]
            detail = "; ".join(
                "{}: {}".format(p["path"], p.get("reason")) for p in misaligned
            ) or "; ".join(str(e) for e in payload.get("errors") or [])
            return fail(
                f"apm pack --check-versions rejected the marketplace: {detail[:250]}",
                errors=payload.get("errors"),
            )

        if shutil.which("claude"):
            bad = []
            for bundle in sorted((marketplace / "plugins").iterdir()):
                got = sh(["claude", "plugin", "validate", "."], bundle)
                if got.returncode != 0:
                    bad.append(f"{bundle.name}: {(got.stderr or got.stdout).strip()[:90]}")
            if bad:
                return fail("claude plugin validate: {}".format("; ".join(bad)[:300]))
            notes.append(f"{len(packages)} bundle(s) validated")
        else:
            notes.append("claude CLI absent; bundles not validated")

        text = (marketplace / "THIRD-PARTY-NOTICES.md").read_text(encoding="utf-8")
        missing = gen_notices.unrecorded(text)
        if missing:
            return fail(
                "no licence recorded in dependency-licenses.yml for {}".format(", ".join(missing))
            )
    detail = "; ".join(notes)
    return ok(f"{len(packages)} package(s) packed from their lockfiles; {detail}")


GATES = [
    Gate("tooling", "the release tooling is locked, formatted, linted and typed", gate_tooling),
    Gate("frontmatter", "customization frontmatter conventions", gate_frontmatter),
    Gate(
        "commits",
        "conventional commits since --since",
        gate_commits,
        needs=(Need("git-range", "skip"),),
    ),
    Gate("licences", "provenance obligations vs declared licences", gate_licences),
    Gate("lockfiles", "package lockfiles resolve exactly the declared pins", gate_lockfiles),
    Gate(
        "pack",
        "every package packs into a valid marketplace",
        gate_pack,
        needs=(Need("apm", "fail"), Need("network", "skip")),
    ),
]


def main(
    repo: Path = workspace.REPO_OPTION,
    since: str = typer.Option(
        "",
        "--since",
        metavar="REF",
        help="Lint the commits in REF..HEAD. CI passes the "
        "pull request's base; without it that gate is skipped.",
    ),
    subject: str = typer.Option(
        "",
        "--subject",
        metavar="TEXT",
        help="An extra subject to lint, such as a pull request title.",
    ),
    only: list[str] = typer.Option([], "--only", help="Run only these gates."),
    skip_: list[str] = typer.Option([], "--skip", help="Skip these gates."),
    offline: bool = typer.Option(False, "--offline", help="Skip the gates that need the network."),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable summary on stdout."),
) -> None:
    """Run every gate over one workspace. Exit 1 if any failed."""
    try:
        runner = gatelib.Runner(GATES, only=only, skip_keys=skip_, json_out=json_out)
    except ValueError as exc:
        raise typer.BadParameter(str(exc)) from None
    ctx = Context(
        repo=repo.resolve(), since=since or None, subject=subject or None, offline=offline
    )
    raise typer.Exit(runner.run(ctx))


def cli() -> None:
    typer.run(main)
