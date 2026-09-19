"""Move each package's pinned upstreams, and show what arrived. Commits nothing.

Per package: `apm update` where the upstream publishes an annotated semver tag,
a HEAD bump where it publishes none (the case `apm update` cannot move at all),
then an install, a check that the lockfile followed, and -- for every pin that
moved -- the upstream's own diff filtered to the path this repo consumes, plus
`apm audit` over what was materialised.

Reading that diff is the job this command exists to set up, and it is the half
that is not automatable: see the meta-update-repo skill and its safety-review
reference. Nothing here is committed, so a blocking finding is reverted with
`git checkout -- packages/<dir>`.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import NamedTuple

import typer
from ruamel.yaml import YAML

from . import gen_notices, workspace
from . import github as githublib
from .workspace import Log, Package, WorkspaceError, label


# `via` is how the pin moved: what `apm update` did, or the manual HEAD bump for
# an upstream it can never move.
class Moved(NamedTuple):
    """One pin that moved, and how it moved."""

    package: str
    key: tuple[str, str]
    before: str
    after: str
    via: str


SEMVER_TAG_RE = re.compile(r"^refs/tags/v?\d+\.\d+\.\d+\^\{\}$")


def apm(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["apm", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
        errors="replace",
    )


def tail(result: subprocess.CompletedProcess, lines: int = 8) -> str:
    """The last few non-blank lines of a command's output, for an error message."""
    text = (result.stdout or "") + (result.stderr or "")
    return "\n".join([line for line in text.split("\n") if line.strip()][-lines:])


def remote_url(key: tuple[str, str]) -> str:
    return f"https://github.com/{key[0]}"


def has_annotated_semver_tag(key: tuple[str, str]) -> bool:
    """Does this upstream publish a tag `apm update` could move a SHA pin to?

    `apm update` resolves a full-SHA pin only to the commit behind the latest
    *annotated* semver tag. `git ls-remote --tags` dereferences an annotated tag
    into a second `^{}` row, which is exactly that distinction.
    """
    result = subprocess.run(
        ["git", "ls-remote", "--tags", remote_url(key)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return False
    return any(
        SEMVER_TAG_RE.match(line.split("\t")[-1].strip())
        for line in result.stdout.split("\n")
        if "\t" in line
    )


def remote_head(key: tuple[str, str]) -> str:
    """The commit the upstream's default branch is on."""
    result = subprocess.run(
        ["git", "ls-remote", remote_url(key), "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise WorkspaceError(
            "git ls-remote {} failed: {}".format(remote_url(key), (result.stderr or "").strip())
        )
    head = result.stdout.split("\t")[0].strip()
    if not workspace.SHA_RE.match(head):
        raise WorkspaceError(f"{label(key)}: unreadable HEAD from git ls-remote")
    return head


def pins_at_head(ws: Path, directory: str) -> dict:
    """The pins as committed, which is the baseline every move is measured from."""
    committed = workspace.git(["show", f"HEAD:packages/{directory}/apm.yml"], ws, check=False)
    if not committed:
        return {}
    return workspace.pins_of(YAML(typ="safe").load(committed) or {})


def rewrite_pin(manifest_path: Path, key: tuple[str, str], new_sha: str) -> None:
    """Move one `#sha` in place, keeping every comment around it."""
    data = workspace.read_yaml(manifest_path)
    deps = (data.get("dependencies") or {}).get("apm") or []
    for index, spec in enumerate(deps):
        if workspace.parse_pin(str(spec))[0] == key:
            location, _, _ = str(spec).partition("#")
            deps[index] = f"{location}#{new_sha}"
            workspace.write_yaml(manifest_path, data)
            return
    raise WorkspaceError(f"{manifest_path}: no pin to rewrite for {label(key)}")


def clean_install_output(package_path: Path) -> None:
    """Drop what `apm install` deployed beside the package; keep the lockfile."""
    for name in workspace.INSTALL_OUTPUT:
        target = package_path / name
        if target.is_dir():
            shutil.rmtree(target, ignore_errors=True)
        elif target.exists():
            target.unlink()


def update_package(
    ws: Path, package: Package, review_only: bool, log: Log = print
) -> tuple[list[Moved], bool, str]:
    """Move this package's pins as far as they go.

    Returns what moved, whether anything was materialised, and what could not be
    done -- a pin `apm update` refused is reported, never quietly bumped to HEAD,
    because HEAD is not the tag its upstream publishes.
    """
    before = pins_at_head(ws, package.directory)
    manifest_path = package.path / "apm.yml"

    problem = ""
    if not review_only:
        result = apm(["update", "--yes", "--target", "claude"], package.path)
        if result.returncode != 0:
            # It writes the manifest only after resolving every pin, so a
            # failure leaves the package as it was. Report it and carry on with
            # the rest: one upstream APM cannot express must not stop the audit
            # of the others. Known case on 0.31: several subpaths of one repo
            # pinned at the same commit ("Expected exactly one apm.yml entry").
            problem = "apm update: %s" % (tail(result, 2) or "failed")
            log(f"       {problem}")
        else:
            log("       apm update: %s" % (last_summary(result) or "no change"))

        # Whatever `apm update` left alone, for a reason it cannot fix: an
        # upstream publishing no annotated semver tag is never movable by it.
        current = workspace.pins_of(workspace.read_yaml(manifest_path))
        manual = [
            key
            for key, sha in current.items()
            if before.get(key, "").lower() == sha.lower() and not has_annotated_semver_tag(key)
        ]
        bumped = False
        for key in manual:
            head = remote_head(key)
            if head.lower() == current[key].lower():
                continue
            rewrite_pin(manifest_path, key, head)
            log(f"       {label(key)}: no annotated tag upstream, moved to HEAD {head[:12]}")
            bumped = True
        if bumped:
            result = apm(["install", "--target", "claude"], package.path)
            if result.returncode != 0:
                raise WorkspaceError(
                    f"apm install failed in packages/{package.directory}\n{tail(result)}"
                )

    after = workspace.pins_of(workspace.read_yaml(manifest_path))
    lock = workspace.read_lock(package.path / "apm.lock.yaml")
    drift = workspace.diff_pins(
        after,
        workspace.locked_of(lock or {}),
        gone="%s is pinned but not in the lockfile",
        new="%s is locked but no longer declared",
        moved="%s is pinned at %s but locked at %s",
    )
    if drift:
        raise WorkspaceError(
            "packages/{}: the lockfile does not match the manifest after updating "
            "({}). Run `apm install` there and check what it did".format(
                package.directory, "; ".join(drift)
            )
        )

    moved = []
    for key, sha in after.items():
        if key in before and before[key].lower() != sha.lower():
            via = "apm update" if has_annotated_semver_tag(key) else "HEAD, untagged upstream"
            moved.append(Moved(package.directory, key, before[key], sha, via))
    return moved, not review_only, problem


def last_summary(result: subprocess.CompletedProcess) -> str:
    """APM's own closing line, which says what it did."""
    lines = [line.strip() for line in (result.stdout or "").split("\n") if line.strip()]
    for line in reversed(lines):
        if "Updated" in line or "up to date" in line or "No changes" in line:
            return line.lstrip("[*i+] ")
    return ""


def audit(package: Package, log: Log = print) -> None:
    """Scan what was materialised for hidden Unicode and integrity drift.

    `apm approve` gates execution, not content, and a pin fixes which content
    arrives rather than what it does. This is the deterministic half of looking:
    the rest is reading the diff below.
    """
    result = apm(["audit", "--ci", "--no-policy", "--no-fail-fast"], package.path)
    if result.returncode == 0:
        log("       audit: clean")
    else:
        log(f"       audit: FINDINGS -- read them before committing\n{tail(result, 14)}")


def show_diff(
    client: githublib.GitHub | None, move: Moved, max_files: int, log: Log = print
) -> None:
    """The upstream's own diff for one moved pin, filtered to what we consume."""
    owner, _, repo = move.key[0].partition("/")
    path = move.key[1]
    log(
        f"\n=== {move.package}: {label(move.key)}\n"
        f"    {move.before[:12]} -> {move.after[:12]} ({move.via})"
    )
    if not client:
        log("    no GitHub token, so no diff. Set GITHUB_TOKEN or run `gh auth login`.")
        return
    try:
        payload = client.compare(owner, repo, move.before, move.after)
    except githublib.ApiError as exc:
        log(f"    could not compare: {exc}")
        return

    commits = payload.get("commits") or []
    log(f"    {len(commits)} commit(s) upstream:")
    for commit in commits:
        log(
            "      {} {}".format(
                commit["sha"][:10], commit["commit"]["message"].split("\n")[0][:90]
            )
        )

    files = [
        f for f in payload.get("files") or [] if not path or f.get("filename", "").startswith(path)
    ]
    if not files:
        log(
            f"    no file under {path or 'the repository root'} changed -- "
            f"the bump is outside what this repo consumes"
        )
        return
    log(f"    {len(files)} file(s) changed under {path or '/'}:")
    for changed in files[:max_files]:
        log(
            "\n--- {} ({}, +{}/-{})".format(
                changed.get("filename"),
                changed.get("status"),
                changed.get("additions"),
                changed.get("deletions"),
            )
        )
        log(changed.get("patch") or "    (no textual patch: binary or too large)")
    if len(files) > max_files:
        log(f"\n    ... and {len(files) - max_files} more file(s); raise --max-files to see them")


def check_licences(ws: Path, client: githublib.GitHub | None, log: Log = print) -> None:
    """Has any upstream relicensed since its terms were recorded?

    Part of updating rather than of the gates: the licences gate checks that the
    recorded terms are consistent with what each file claims, which stays true
    while the upstream itself quietly changes. Only asking upstream catches that,
    and a bump is when it matters.
    """
    licenses = gen_notices.read_license_map(ws / "dependency-licenses.yml")
    if not licenses or not client:
        return
    drift = [row for row in gen_notices.relicensing(licenses, client) if row.status == "drift"]
    if not drift:
        return
    log(f"\n{len(drift)} upstream licence(s) may have changed:")
    for row in drift:
        log(f"  {row.key:<44} recorded {row.recorded}, GitHub now reports {row.reported}")
    log(
        "  Re-read their LICENSE, update dependency-licenses.yml, and re-check "
        "any local `fidelity` that depends on it."
    )


def preview(packages: Sequence[Package], log: Log = print) -> None:
    """What would move, without moving it."""
    for package in packages:
        log(f"\n[{package.directory}]")
        for command in (["outdated"], ["update", "--dry-run"]):
            result = apm(command, package.path)
            log("  $ apm {}".format(" ".join(command)))
            for line in (result.stdout or "").split("\n"):
                if line.strip():
                    log(f"    {line}")


def main(
    repo: Path = workspace.REPO_OPTION,
    package: list[str] = typer.Option(
        [], "--package", help="Only these packages (directory or name)."
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would move and write nothing."
    ),
    review_only: bool = typer.Option(
        False,
        "--review-only",
        help="Do not update: review the pins already moved in the working tree.",
    ),
    max_files: int = typer.Option(10, "--max-files", help="Patches to print per moved pin."),
    github_token: str = typer.Option(
        "", "--github-token", help="Overrides GITHUB_TOKEN / GH_TOKEN / `gh auth token`."
    ),
) -> None:
    """Update this repo's pinned upstreams and show the diff of everything that moved."""
    ws = repo.resolve()
    try:
        packages = workspace.select(ws, package)
        if dry_run:
            preview(packages)
            print("\n[dry-run] nothing written")
            return

        moved: list[Moved] = []
        problems: list[str] = []
        for entry in packages:
            print(f"[{entry.directory}]")
            found, installed, problem = update_package(ws, entry, review_only)
            if problem:
                problems.append(f"{entry.directory}: {problem}")
            # Only meaningful when this run materialised the content: --review-only
            # reviews a pin someone moved by hand, and installs nothing to scan.
            if found and installed:
                audit(entry)
            if installed:
                clean_install_output(entry.path)
            moved.extend(found)
            print(f"       {len(found)} pin(s) moved")
    except WorkspaceError as exc:
        raise workspace.die(exc) from None

    token = githublib.token(github_token)
    client = githublib.GitHub(token) if token else None
    check_licences(ws, client)

    if not moved:
        print("\nNothing moved. Every pin is where the last update left it.")
        raise typer.Exit(report_problems(problems))

    for move in moved:
        show_diff(client, move, max_files)

    print(f"\n{len(moved)} pin(s) moved:")
    for move in moved:
        print(f"  {move.package:<10} {label(move.key):<52} {move.before[:12]} -> {move.after[:12]}")
    print(
        "\nNothing is committed. Read each diff above against the safety review, "
        "then commit per package:\n"
        "  git add packages/<dir>/apm.yml packages/<dir>/apm.lock.yaml\n"
        "  git commit -m 'build(<dir>): bump <dependency> to <sha7>'\n"
        "To reject one: git checkout -- packages/<dir>"
    )
    raise typer.Exit(report_problems(problems))


def report_problems(problems: list[str]) -> int:
    """Exit non-zero on a package that could not be updated, so a run that did
    only half the job is not read as a clean one."""
    if not problems:
        return 0
    print(f"\n{len(problems)} package(s) could not be updated:")
    for problem in problems:
        print(f"  {problem}")
    return 1


def cli() -> None:
    typer.run(main)
