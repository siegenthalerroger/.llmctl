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
from pathlib import Path

import typer

import commits as commitlib
import github as githublib
import pack_marketplace
import release_notes
import versions as versionlib
import workspace
from workspace import WorkspaceError, git


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
    listing = "\n".join("    %s" % line for line in soiled[:show])
    if len(soiled) > show:
        listing += "\n    ... and %d more" % (len(soiled) - show)
    if allowed:
        print("[dirty] marketplace: %d uncommitted path(s) will be swept into the "
              "release commit\n%s" % (len(soiled), listing))
        return
    raise WorkspaceError(
        "the marketplace tree at %s has %d uncommitted path(s):\n%s\n"
        "A release runs `git add -A` there, so all of it would be committed and "
        "pushed under the new version. Commit, stash or discard it first -- or "
        "pass --allow-dirty if sweeping it in is the intent."
        % (marketplace, len(soiled), listing))


def refuse_taken_tags(ws: Path, plans) -> None:
    """A tag that exists is a release that happened; re-cutting it would publish
    different bundles under a version somebody already has."""
    taken = []
    for plan in plans:
        tag = "%s@%s" % (plan.name, plan.next)
        if git(["tag", "--list", tag], ws):
            taken.append("%s (local)" % tag)
        elif git(["ls-remote", "--tags", "origin", "refs/tags/%s" % tag], ws, check=False):
            taken.append("%s (origin)" % tag)
    if taken:
        raise WorkspaceError("already released: %s" % ", ".join(taken))


def tag_plan(ws: Path, package, tag: str):
    """A Plan for a tag already cut, so its notes read like a fresh release's."""
    siblings = git(["tag", "--list", "%s@*" % package.name, "--sort=-v:refname"],
                   ws).split()
    target = versionlib.version_key(versionlib.version_of(tag))
    previous = next((t for t in siblings
                     if versionlib.version_key(versionlib.version_of(t)) < target), None)
    commits = commitlib.log(ws, "%s..%s" % (previous, tag) if previous else tag,
                            "packages/%s" % package.directory)
    return versionlib.Plan(package.directory, package.name, previous,
                           versionlib.version_of(tag), commits, [], False)


def ensure_releases(ws: Path, packages, client, prepared=None, log=print) -> None:
    """Give every package's newest tag a release page, if it has none.

    Publishing is two steps -- push the tag, then create the release -- so they
    can end up out of step when the second fails or is rate-limited. Asking for
    the page rather than assuming it is what lets the next run finish the job,
    instead of reporting nothing to release and leaving a tag with no notes.
    """
    owner, repo = workspace.remote_slug(ws)
    prepared = prepared or {}
    pulls: dict = {}
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
                body = release_notes.build(tag_plan(ws, package, tag), owner, repo,
                                           client=client, cache=pulls)
            created = client.create_release(owner, repo, tag,
                                            "%s %s" % (package.name, version),
                                            body, tag)
            log("[note] %s" % created.get("html_url", tag))
        except githublib.ApiError as exc:
            # The tag is pushed and the bundles are published; a missing release
            # page is a cosmetic loss, not a reason to fail the run and leave
            # the operator wondering which half landed. The next run retries.
            sys.stderr.write("could not publish the GitHub release for %s: %s\n"
                             % (tag, exc))


def main(repo: Path = workspace.REPO_OPTION,
         marketplace: Path = workspace.MARKETPLACE_OPTION,
         dry_run: bool = typer.Option(False, "--dry-run",
                                      help="Show what would be released, and the notes. "
                                           "Writes nothing."),
         package: list[str] = typer.Option([], "--package", help="Release only these packages."),
         force: bool = typer.Option(False, "--force",
                                    help="Release a --package with no commits since its tag."),
         version: str = typer.Option("", "--version", metavar="YYYY.M.N",
                                     help="Release one --package at exactly this version."),
         no_push: bool = typer.Option(False, "--no-push",
                                      help="Pack, commit the marketplace and tag locally; "
                                           "push nothing."),
         allow_dirty: bool = typer.Option(False, "--allow-dirty",
                                          help="Release even though the marketplace tree has "
                                               "uncommitted changes, sweeping them in."),
         github_token: str = typer.Option("", "--github-token",
                                          help="Overrides GITHUB_TOKEN / GH_TOKEN.")) -> None:
    """Pack, tag and publish every package whose paths changed since its last tag."""
    ws, marketplace = repo.resolve(), marketplace.resolve()
    if not (marketplace / ".git").exists():
        sys.stderr.write("%s is not a git checkout -- pass the marketplace clone\n"
                         % marketplace)
        raise typer.Exit(1)
    try:
        release(ws, marketplace, package, force, version or None,
                dry_run=dry_run, no_push=no_push, allow_dirty=allow_dirty,
                token=githublib.token(github_token))
    except (WorkspaceError, pack_marketplace.PackError) as exc:
        raise workspace.die(exc)


def release(ws: Path, marketplace: Path, only, force, version, *,
            dry_run, no_push, allow_dirty, token) -> None:
    # The same code `apm run versions` prints from, so a preview cannot disagree
    # with what gets published.
    plans, skips = versionlib.plan(ws, only=only, force=force, version=version)
    versionlib.report(plans, skips)

    client = githublib.GitHub(token) if token else None
    if not client:
        print("[note] no GitHub token; release notes will carry commits only, and "
              "no release page is published")

    if not plans:
        print("\nnothing to release")
        if client and not (dry_run or no_push):
            ensure_releases(ws, workspace.select(ws, list(only)), client)
        return

    owner, repo_name = workspace.remote_slug(ws) if client else ("", "")
    pulls: dict = {}
    notes = {p.name: release_notes.build(p, owner, repo_name, client=client, cache=pulls)
             for p in plans}

    if dry_run:
        for plan in plans:
            print("\n--- %s@%s\n%s" % (plan.name, plan.next, notes[plan.name]))
        print("\n[dry-run] no files written")
        return

    refuse_dirty(marketplace, allow_dirty)
    refuse_taken_tags(ws, plans)

    versions = pack_marketplace.version_map(plans, skips)
    try:
        pack_marketplace.pack_all(ws, marketplace, versions, {p.name for p in plans},
                                  scratch=ws / "build", source="HEAD")
    except pack_marketplace.PackError as exc:
        raise pack_marketplace.PackError("%s\nNothing was committed or tagged." % exc)

    summary = ", ".join("%s %s" % (p.name, p.next) for p in plans)
    tags = ["%s@%s" % (p.name, p.next) for p in plans]

    git(["add", "-A"], marketplace)
    if git(["status", "--porcelain"], marketplace):
        git(["commit", "-m", "chore(release): %s" % summary], marketplace)
        print("[git ] committed in the marketplace")
    else:
        print("[git ] the marketplace is already up to date")

    head = git(["rev-parse", "HEAD"], ws)
    for tag in tags:
        name, _, number = tag.partition("@")
        workspace.tag(ws, tag, "%s %s" % (name, number))
        workspace.tag(marketplace, tag, "%s %s" % (name, number))
        print("[tag ] %s -> %s" % (tag, head[:12]))

    if no_push:
        print("\nReleased %d package(s), unpushed. The tags are the baseline for the "
              "next release, so push both repos:\n"
              "  git -C %s push --atomic origin %s\n"
              "  git -C %s push --atomic --follow-tags origin HEAD"
              % (len(plans), ws, " ".join(tags), marketplace))
        return

    # The workspace half first: bundles published for a release the steering
    # repo never recorded are the worse failure. `--atomic` so a rejected tag
    # takes the others with it rather than half-releasing.
    git(["push", "--atomic", "origin"] + tags, ws)
    print("[push] %d tag(s)" % len(tags))
    git(["push", "--atomic", "--follow-tags", "origin", "HEAD"], marketplace)
    print("[push] marketplace")

    if client:
        released = {plan.name for plan in plans}
        ensure_releases(ws, [p for p in workspace.packages(ws) if p.name in released],
                        client, prepared={"%s@%s" % (p.name, p.next): notes[p.name]
                                          for p in plans})
    print("\nReleased and pushed %d package(s)." % len(plans))


if __name__ == "__main__":
    typer.run(main)
