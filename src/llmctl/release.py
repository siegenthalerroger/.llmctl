"""Publish each package at the calendar version its commits earn it.

A release writes nothing to the workspace: the version is stamped into a scratch
export at pack time, and the record of it is the annotated `<name>@<version>` tag
plus the GitHub release beside it. The marketplace is the opposite case -- it is
generated output entirely, so it is committed and pushed directly.

Order matters at the end. The workspace tags go first: bundles published for a
release the steering repo never recorded are the worse failure, and a marketplace
push that dies after the tags landed heals itself, because the next run re-packs
any version whose bundle is missing. See CONTRIBUTING.md#releasing.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

import typer

from . import commits as commitlib
from . import github as githublib
from . import pack_marketplace, release_notes, workspace
from . import versions as versionlib
from .workspace import Log, Package, WorkspaceError, git


def refuse_dirty(marketplace: Path, allowed: bool, show: int = 12) -> None:
    """Refuse to sweep a dirty marketplace tree into the release commit.

    The release stages it with `git add -A`, so anything already sitting there
    rides along and is pushed under the new version. A CI checkout is clean and
    this never fires; a working checkout is where a half-finished edit gets
    published. The workspace needs no such check: it is never committed, and the
    pack exports from HEAD.
    """
    soiled = workspace.dirty(marketplace)
    if not soiled:
        return
    listing = "\n".join(f"    {line}" for line in soiled[:show])
    if len(soiled) > show:
        listing += f"\n    ... and {len(soiled) - show} more"
    if allowed:
        print(
            f"[dirty] marketplace: {len(soiled)} uncommitted path(s) will be swept "
            f"into the release commit\n{listing}"
        )
        return
    raise WorkspaceError(
        f"the marketplace tree at {marketplace} has {len(soiled)} uncommitted "
        f"path(s):\n{listing}\nA release runs `git add -A` there, so all of it would "
        f"be committed and pushed under the new version. Commit, stash or discard it "
        f"first -- or pass --allow-dirty if sweeping it in is the intent."
    )


def refuse_taken_tags(ws: Path, plans: Sequence[versionlib.Plan]) -> None:
    """A tag that exists is a release that happened; re-cutting it would publish
    different bundles under a version somebody already has."""
    taken = []
    for plan in plans:
        tag = f"{plan.name}@{plan.next}"
        if git(["tag", "--list", tag], ws):
            taken.append(f"{tag} (local)")
        elif git(["ls-remote", "--tags", "origin", f"refs/tags/{tag}"], ws, check=False):
            taken.append(f"{tag} (origin)")
    if taken:
        raise WorkspaceError("already released: {}".format(", ".join(taken)))


def tag_plan(ws: Path, package: Package, tag: str) -> versionlib.Plan:
    """A Plan for a tag already cut, so its notes read like a fresh release's."""
    siblings = git(["tag", "--list", f"{package.name}@*", "--sort=-v:refname"], ws).split()
    target = versionlib.version_key(versionlib.version_of(tag))
    previous = next(
        (t for t in siblings if versionlib.version_key(versionlib.version_of(t)) < target), None
    )
    commits = commitlib.log(
        ws, f"{previous}..{tag}" if previous else tag, f"packages/{package.directory}"
    )
    return versionlib.Plan(
        package.directory, package.name, previous, versionlib.version_of(tag), commits, [], False
    )


def commit_of(ws: Path, tag: str) -> str:
    """The commit a tag points at.

    `target_commitish` takes a branch or a commit SHA. Handing it the tag name
    is what made every `POST /releases` fail validation, silently, for as long
    as the calendar pipeline has existed.
    """
    return git(["rev-list", "-n", "1", tag], ws)


def ensure_releases(
    ws: Path,
    packages: Sequence[Package],
    client: githublib.GitHub,
    prepared: dict[str, str] | None = None,
    log: Log = print,
) -> None:
    """Give every package's newest tag a release page, if it has none.

    Publishing is two steps -- push the tag, then create the release -- so they
    can end up out of step when the second fails or is rate-limited. Asking for
    the page rather than assuming it is what lets the next run finish the job,
    instead of reporting nothing to release and leaving a tag with no notes.

    A failure here raises. The tag and the bundles are already published, so the
    run did land something -- but a release nobody can read is not the release
    this repository promises, and the first one of these went unnoticed for a
    whole release precisely because it only wrote to stderr.
    """
    owner, repo = workspace.remote_slug(ws)
    prepared = prepared or {}
    pulls: dict = {}
    failures = []
    for package in packages:
        tag = versionlib.last_tag(ws, package.name)
        if not tag:
            continue
        try:
            if client.release_for_tag(owner, repo, tag):
                continue
            version = versionlib.version_of(tag)
            body = prepared.get(tag)
            if body is None:
                body = release_notes.build(
                    tag_plan(ws, package, tag), owner, repo, client=client, cache=pulls
                )
            created = client.create_release(
                owner,
                repo,
                tag=tag,
                name=f"{package.name} {version}",
                body=body,
                target=commit_of(ws, tag),
            )
            log("[note] {}".format(created.get("html_url", tag)))
        except githublib.ApiError as exc:
            failures.append(f"{tag}: {exc}")
    if failures:
        raise WorkspaceError(
            "the tags and bundles are published, but {} release page(s) are "
            "missing -- re-run to finish the job:\n  {}".format(
                len(failures), "\n  ".join(failures)
            )
        )


def main(
    repo: Path = workspace.REPO_OPTION,
    marketplace: Path = workspace.MARKETPLACE_OPTION,
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be released, and the notes. Writes nothing."
    ),
    package: list[str] = typer.Option([], "--package", help="Release only these packages."),
    force: bool = typer.Option(
        False, "--force", help="Release a --package with no commits since its tag."
    ),
    version: str = typer.Option(
        "", "--version", metavar="YYYY.M.N", help="Release one --package at exactly this version."
    ),
    no_push: bool = typer.Option(
        False, "--no-push", help="Pack, commit the marketplace and tag locally; push nothing."
    ),
    allow_dirty: bool = typer.Option(
        False,
        "--allow-dirty",
        help="Release even though the marketplace tree has uncommitted changes, sweeping them in.",
    ),
    github_token: str = typer.Option(
        "", "--github-token", help="Overrides GITHUB_TOKEN / GH_TOKEN."
    ),
) -> None:
    """Pack, tag and publish every package whose paths changed since its last tag."""
    ws, marketplace = repo.resolve(), marketplace.resolve()
    if not (marketplace / ".git").exists():
        sys.stderr.write(f"{marketplace} is not a git checkout -- pass the marketplace clone\n")
        raise typer.Exit(1)
    try:
        release(
            ws,
            marketplace,
            package,
            force,
            version or None,
            dry_run=dry_run,
            no_push=no_push,
            allow_dirty=allow_dirty,
            token=githublib.token(github_token),
        )
    except (WorkspaceError, pack_marketplace.PackError) as exc:
        raise workspace.die(exc) from None


def release(
    ws: Path,
    marketplace: Path,
    only: Sequence[str],
    force: bool,
    version: str | None,
    *,
    dry_run: bool,
    no_push: bool,
    allow_dirty: bool,
    token: str,
) -> None:
    # The same code `apm run versions` prints from, so a preview cannot disagree
    # with what gets published.
    plans, skips = versionlib.plan(ws, only=only, force=force, version=version)
    versionlib.report(plans, skips)

    client = githublib.GitHub(token) if token else None
    if not client:
        print(
            "[note] no GitHub token; release notes will carry commits only, and "
            "no release page is published"
        )

    if not plans:
        print("\nnothing to release")
        if client and not (dry_run or no_push):
            ensure_releases(ws, workspace.select(ws, list(only)), client)
        return

    owner, repo_name = workspace.remote_slug(ws) if client else ("", "")
    pulls: dict = {}
    notes = {
        p.name: release_notes.build(p, owner, repo_name, client=client, cache=pulls) for p in plans
    }

    if dry_run:
        for plan in plans:
            print(f"\n--- {plan.name}@{plan.next}\n{notes[plan.name]}")
        print("\n[dry-run] no files written")
        return

    refuse_dirty(marketplace, allow_dirty)
    refuse_taken_tags(ws, plans)

    versions = pack_marketplace.version_map(ws, plans)
    try:
        pack_marketplace.pack_all(
            ws, marketplace, versions, {p.name for p in plans}, scratch=ws / "build", source="HEAD"
        )
    except pack_marketplace.PackError as exc:
        raise pack_marketplace.PackError(f"{exc}\nNothing was committed or tagged.") from exc

    summary = ", ".join(f"{p.name} {p.next}" for p in plans)
    tags = [f"{p.name}@{p.next}" for p in plans]

    git(["add", "-A"], marketplace)
    if git(["status", "--porcelain"], marketplace):
        git(["commit", "-m", f"chore(release): {summary}"], marketplace)
        print("[git ] committed in the marketplace")
    else:
        print("[git ] the marketplace is already up to date")

    head = git(["rev-parse", "HEAD"], ws)
    for tag in tags:
        name, _, number = tag.partition("@")
        workspace.tag(ws, tag, f"{name} {number}")
        workspace.tag(marketplace, tag, f"{name} {number}")
        print(f"[tag ] {tag} -> {head[:12]}")

    if no_push:
        pushable = " ".join(tags)
        print(
            f"\nReleased {len(plans)} package(s), unpushed. The tags are the baseline "
            f"for the next release, so push both repos:\n"
            f"  git -C {ws} push --atomic origin {pushable}\n"
            f"  git -C {marketplace} push --atomic --follow-tags origin HEAD"
        )
        return

    # The workspace half first: bundles published for a release the steering
    # repo never recorded are the worse failure. `--atomic` so a rejected tag
    # takes the others with it rather than half-releasing.
    git(["push", "--atomic", "origin", *tags], ws)
    print(f"[push] {len(tags)} tag(s)")
    git(["push", "--atomic", "--follow-tags", "origin", "HEAD"], marketplace)
    print("[push] marketplace")

    if client:
        released = {plan.name for plan in plans}
        ensure_releases(
            ws,
            [p for p in workspace.packages(ws) if p.name in released],
            client,
            prepared={f"{p.name}@{p.next}": notes[p.name] for p in plans},
        )
    print(f"\nReleased and pushed {len(plans)} package(s).")


def cli() -> None:
    typer.run(main)
