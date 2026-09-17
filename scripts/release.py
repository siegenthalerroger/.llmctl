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

Packages version independently. A change to `ops` releases `ops` and nothing
else, so a version number always means something changed in that package --
which is the whole reason this is not lockstep. Which version that is belongs
to versions.py, imported here rather than reimplemented: `apm run versions`
answers the same question without writing anything, and a preview that can
disagree with the release is worse than no preview.

**A release writes nothing to the workspace.** `packages/*/apm.yml` carries a
placeholder version; the real one is stamped into a scratch export at pack
time, and the record of it is the annotated `<name>@<version>` tag plus the
GitHub release beside it. That is what lets this run on a push to a protected
main branch with no pull request, no bypass and no second CI cycle: pushing a
tag is not pushing a branch.

The marketplace is a different matter. It is generated output, entirely -- the
packer deletes anything in it that is not -- so it is committed and pushed
directly. Protecting it would gate a robot against itself.

Order matters at the end. The workspace tags go first: bundles published for a
release the steering repo never recorded are the worse failure, and a
marketplace push that dies after the tags landed heals itself, because the next
run re-packs any version whose bundle is missing.

Usage:
  uv run scripts/release.py --repo PATH --marketplace PATH
                            [--dry-run] [--package NAME]... [--force]
                            [--version YYYY.M.N] [--no-push] [--allow-dirty]

  --repo         the workspace to release. These scripts live in `.llmctl` but
                 release any repo laid out the same way, so it is never guessed
  --marketplace  the marketplace to publish into. Required for the same reason:
                 a derived path would silently publish into the wrong repo
  --dry-run      show what would be released, and the notes; write nothing
  --package      release only these packages (repeatable)
  --force        release the named packages even with no commits since their
                 tag. Requires --package
  --version      release exactly one --package at this version. Requires
                 --package; must be YYYY.M.N, unused, and above its last tag
  --no-push      pack, commit the marketplace and tag locally; push nothing
  --allow-dirty  release even though the marketplace tree has uncommitted
                 changes, sweeping them into the release commit

A repo that has never been released has no baseline for a package with no
commits to release. Seed one by hand, once:

  git tag -a <package>@<version> -m "<package> <version>" <commit>
  git push origin --tags

Exit codes: 0 released (or nothing to do), 1 error.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import typer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import github as githublib  # noqa: E402
import pack_marketplace  # noqa: E402
import release_notes  # noqa: E402
import versions as versionlib  # noqa: E402
import workspace  # noqa: E402
from workspace import git  # noqa: E402


def refuse_dirty(marketplace: Path, allowed: bool, show: int = 12) -> bool:
    """True when the marketplace tree is dirty and that is not allowed.

    The release stages the marketplace with `git add -A`, so anything already
    sitting there rides along into the release commit and is pushed with it. A
    CI checkout is clean and this never fires; a working checkout is where a
    half-finished edit gets published under a version number. The workspace
    needs no such check: it is never committed, and the pack exports from HEAD.
    """
    soiled = workspace.dirty(marketplace)
    if not soiled:
        return False
    listing = "\n".join("    %s" % line for line in soiled[:show])
    if len(soiled) > show:
        listing += "\n    ... and %d more" % (len(soiled) - show)
    if allowed:
        print("[dirty] marketplace: %d uncommitted path(s) will be swept into the "
              "release commit\n%s" % (len(soiled), listing))
        return False
    sys.stderr.write(
        "the marketplace tree at %s has %d uncommitted path(s):\n%s\n"
        "A release runs `git add -A` there, so all of it would be committed and "
        "pushed under the new version. Commit, stash or discard it first -- or "
        "pass --allow-dirty if sweeping it in is the intent.\n"
        % (marketplace, len(soiled), listing))
    return True


def unused_tags(ws: Path, plans) -> bool:
    """True when some tag this release would cut already exists, here or on the
    remote. A tag that exists is a release that happened; re-cutting it would
    silently publish different bundles under a version somebody already has."""
    taken = []
    for plan in plans:
        tag = "%s@%s" % (plan.name, plan.next)
        if git(["tag", "--list", tag], ws):
            taken.append("%s (local)" % tag)
        elif git(["ls-remote", "--tags", "origin", "refs/tags/%s" % tag], ws, check=False):
            taken.append("%s (origin)" % tag)
    if taken:
        sys.stderr.write("already released: %s\n" % ", ".join(taken))
        return True
    return False


def publish_releases(ws: Path, plans, notes: dict, client, target: str) -> None:
    """One GitHub release per tag, carrying that package's notes."""
    owner, repo = workspace.remote_slug(ws)
    for plan in plans:
        tag = "%s@%s" % (plan.name, plan.next)
        try:
            created = client.create_release(owner, repo, tag,
                                            "%s %s" % (plan.name, plan.next),
                                            notes[plan.name], target)
            print("[note] %s" % created.get("html_url", tag))
        except githublib.ApiError as exc:
            # The tag is pushed and the bundles are published; a missing release
            # page is a cosmetic loss, not a reason to fail the run and leave
            # the operator wondering which half landed.
            sys.stderr.write("could not create the GitHub release for %s: %s\n" % (tag, exc))


def main(repo: Path = workspace.REPO_OPTION,
         marketplace: Path = workspace.MARKETPLACE_OPTION,
         dry_run: bool = typer.Option(False, "--dry-run"),
         package: list[str] = typer.Option([], "--package", help="only these packages"),
         force: bool = typer.Option(False, "--force", help="release without commits"),
         version: str = typer.Option("", "--version", help="release at this YYYY.M.N"),
         no_push: bool = typer.Option(False, "--no-push"),
         allow_dirty: bool = typer.Option(False, "--allow-dirty"),
         github_token: str = typer.Option("", "--github-token", help="overrides GITHUB_TOKEN")) -> None:
    ws, marketplace = repo.resolve(), marketplace.resolve()
    if not (marketplace / ".git").exists():
        sys.stderr.write("%s is not a git checkout -- pass the marketplace clone\n"
                         % marketplace)
        raise typer.Exit(1)

    # Same code `apm run versions` prints from, so a preview cannot disagree
    # with what gets published.
    plans, skips = versionlib.plan(ws, only=package, force=force,
                                   version=version or None)
    versionlib.report(plans, skips)
    if not plans:
        print("\nnothing to release")
        return

    token = githublib.token(github_token)
    client = githublib.GitHub(token) if token else None
    if not client:
        print("[note] no GitHub token; release notes will carry commits only")
    notes = {p.name: release_notes.build(p, *(workspace.remote_slug(ws) if client else ("", "")),
                                         client=client) for p in plans}

    if dry_run:
        for plan in plans:
            print("\n--- %s@%s\n%s" % (plan.name, plan.next, notes[plan.name]))
        print("\n[dry-run] no files written")
        return

    if refuse_dirty(marketplace, allow_dirty):
        raise typer.Exit(1)
    if unused_tags(ws, plans):
        raise typer.Exit(1)

    try:
        versions = pack_marketplace.version_map(plans, skips)
        pack_marketplace.pack_all(ws, marketplace, versions, {p.name for p in plans},
                                  scratch=ws / "build", source="HEAD")
    except pack_marketplace.PackError as exc:
        sys.stderr.write("%s\nNothing was committed or tagged.\n" % exc)
        raise typer.Exit(1)

    summary = ", ".join("%s %s" % (p.name, p.next) for p in plans)
    message = "chore(release): %s" % summary
    tags = ["%s@%s" % (p.name, p.next) for p in plans]

    git(["add", "-A"], marketplace)
    if git(["status", "--porcelain"], marketplace):
        git(["commit", "-m", message], marketplace)
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
        publish_releases(ws, plans, notes, client, head)

    print("\nReleased and pushed %d package(s)." % len(plans))


if __name__ == "__main__":
    typer.run(main)
