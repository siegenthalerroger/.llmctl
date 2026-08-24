#!/usr/bin/env python3
"""Pack, commit and tag each package at the version its commits justify.

Packages version independently. A change to `ops` bumps `ops` and nothing else,
so a version number always means something changed in that package -- which is
the whole reason this is not lockstep.

Which version that is, and why, belongs to versions.py, imported here rather
than reimplemented: `apm run versions` answers the same question without
writing anything, and a preview that can disagree with the release is worse
than no preview. Read that module for the derivation rules, including the
0.y.z cap.

Both trees must be clean before anything is written. The release stages with
`git add -A`, so a stray edit in either repo is committed and pushed under the
new version -- invisible until someone installs it. A CI checkout is clean and
never trips this; a working checkout is exactly where it matters. `--allow-dirty`
sweeps anyway and lists what it swept, which is what the workflow passes: the
deploy check ahead of it rewrites `apm.lock.yaml` whenever tracked content moved
without a lockfile refresh.

The tags this creates are annotated because the push at the end uses `--follow-tags`, which
carries annotated tags only; lightweight ones need `--tags` instead. That push
is also `--atomic`: `--follow-tags` sends the branch and its tags in one command
but git will still apply them independently, so a branch rejected by a ruleset
leaves the tag behind on a commit nothing reaches -- and since the branch is an
ancestor of that commit, the next run measures zero commits since the tag and
skips the package for good.

Where the base branch is protected, the release commit cannot be pushed to it
directly -- `--pull-request` routes it through the same gate every other change
goes through. The workspace commit lands on a throwaway `release/*` branch, a
pull request merges it, the branch is deleted, and only then are the tags cut,
against the merged commit rather than the branch's. The marketplace is pushed
directly: it is generated output, and protecting it would gate a robot against
itself.

Who opens that pull request matters more than it looks. Authored by
github-actions[bot] on a public repo, its checks land behind the
outside-contributor approval gate and sit there until a human clicks approve --
a release that needs babysitting is not automated. Authored by a collaborator,
via a PAT or GitHub App token in GH_TOKEN, they simply run. So run this with
such a token; that is what the workflow does.

A caller stuck with GITHUB_TOKEN has a partial workaround in `--gate-workflow`,
which dispatches the gate explicitly: a pull request opened by that token does
not fire `pull_request` workflows at all, and `workflow_dispatch` is the
documented exception. It buys a check run that would otherwise never exist. It
does not lift the approval gate -- that follows the pull request's author, and
the dispatched run queues behind it just the same.

Usage:
  python scripts/release.py --repo PATH --marketplace PATH
                            [--dry-run] [--package NAME] [--bump LEVEL]
                            [--no-tag] [--no-commit] [--no-push]
                            [--pull-request] [--gate-check NAME]
                            [--gate-workflow FILE] [--gate-timeout SECONDS]

  --repo         the workspace to release. These scripts live in `.llmctl` but
                 release any repo laid out the same way, so it is never guessed
  --marketplace  the marketplace to publish into. Required for the same reason:
                 a derived path would silently publish into the wrong repo
  --dry-run      show what would change; make no commits, tags, or version edits
                 (tags are still fetched, or the preview would be wrong)
  --package      release only these packages (repeatable)
  --bump         force a level instead of deriving it. `--bump major` is also
                 how a 0.y.z package is deliberately promoted to 1.0.0
  --no-tag       bump and pack, but create no tags
  --no-commit    leave both working trees dirty for inspection
  --no-push      commit and tag locally, but do not push
  --allow-dirty  release even though a tree has uncommitted changes, sweeping
                 them into the release commit. Listed before they are swept
  --pull-request merge the workspace commit through a pull request instead of
                 pushing to the base branch. Requires the `gh` CLI, and a token
                 belonging to a collaborator -- see above
  --gate-check   the status check that must pass before the release PR merges
                 (default: "workspace gates"). Empty string waits for nothing
  --gate-workflow dispatch this workflow so the gate reports at all. Only for a
                 caller whose token cannot fire `pull_request` workflows; off by
                 default, because a collaborator's token does not need it
  --gate-timeout how long to wait for the check, in seconds (default: 1800)

A repo that has never been released has no baseline. Seed one by hand, once
(the .llmctl repos are already seeded; a new workspace is not):

  git tag -a <package>@<current-version> -m "<package> <current-version>" <commit>
  git push origin --tags

Exit codes: 0 released (or nothing to do), 1 error.
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import versions  # noqa: E402
import workspace  # noqa: E402

# The repo being released, set once from --repo. A module-level name rather
# than a `cwd=WORKSPACE` default because a default argument binds at def time,
# which is before the flags are parsed -- every git call would run against the
# tooling checkout instead, committing and tagging in the wrong repo.
WORKSPACE = None

def git(args, cwd=None, check=True):
    cwd = cwd or WORKSPACE
    result = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True)
    if check and result.returncode != 0:
        sys.stderr.write("git %s failed in %s\n%s\n"
                         % (" ".join(args), cwd, result.stderr.strip()))
        raise SystemExit(1)
    return result.stdout.strip()


def gh(args, check=True):
    """Run the GitHub CLI in the workspace. Only the --pull-request path uses it.

    Kept out of the git() helper on purpose: everything else here is plain git
    against a local clone, and a repo releasing without --pull-request must not
    need `gh` installed at all.
    """
    result = subprocess.run(["gh"] + args, cwd=WORKSPACE,
                            capture_output=True, text=True)
    if check and result.returncode != 0:
        sys.stderr.write("gh %s failed\n%s\n"
                         % (" ".join(args), (result.stderr or result.stdout).strip()))
        raise SystemExit(1)
    return result.stdout.strip()


def dirty(tree):
    """Everything `git add -A` would stage here, tracked or not."""
    return [l for l in git(["status", "--porcelain"], cwd=tree).split("\n")
            if l.strip()]


def refuse_dirty(ws, marketplace, allowed, show=12):
    """True when a tree is dirty and that is not allowed -- caller should stop.

    The release stages with `git add -A`, so anything already sitting in either
    tree rides along into the release commit and is pushed with it. A CI
    checkout is clean and this never fires; a working checkout is where a
    half-finished edit gets published under a version number.
    """
    for label, tree in (("workspace", ws), ("marketplace", marketplace)):
        soiled = dirty(tree)
        if not soiled:
            continue
        listing = "\n".join("    %s" % l for l in soiled[:show])
        if len(soiled) > show:
            listing += "\n    ... and %d more" % (len(soiled) - show)
        if allowed:
            print("[dirty] %s: %d uncommitted path(s) will be swept into the "
                  "release commit\n%s" % (label, len(soiled), listing))
            continue
        sys.stderr.write(
            "the %s tree at %s has %d uncommitted path(s):\n%s\n"
            "A release runs `git add -A` there, so all of it would be committed "
            "and pushed under the new version. Commit, stash or discard it "
            "first -- or pass --allow-dirty if sweeping it in is the intent.\n"
            % (label, tree, len(soiled), listing))
        return True
    return False


def set_package_version(manifest, version):
    text = io.open(manifest, encoding="utf-8").read()
    updated = re.sub(r"(?m)^version:.*$", "version: %s" % version, text, count=1)
    if updated == text:
        return False
    io.open(manifest, "w", encoding="utf-8", newline="").write(updated)
    return True


def set_manifest_version(manifest, name, version):
    """Rewrite one packages[] entry's `version:` in the marketplace apm.yml.

    Same anchored-to-`- name:` shape pack-marketplace.py uses for `source:`, so
    the two cannot drift apart in how they find an entry.
    """
    text = io.open(manifest, encoding="utf-8").read()
    pattern = (r"(- name: %s\n(?:\s+.*\n)*?\s+version: )\S+" % re.escape(name))
    updated = re.sub(pattern, r"\g<1>%s" % version, text)
    if updated == text:
        return False
    io.open(manifest, "w", encoding="utf-8", newline="").write(updated)
    return True


def cut_tag(tag, cwd=None, at=None):
    """Annotated, not lightweight: `--follow-tags` ignores lightweight tags, so
    those would never reach the remote."""
    name, _, version = tag.partition("@")
    git(["tag", "-a", tag, "-m", "%s %s" % (name, version)] + ([at] if at else []),
        cwd=cwd)


def release_branch(summary):
    """A legible, collision-proof name for the throwaway release branch.

    The UTC stamp is not decoration: a run that dies after pushing the branch
    leaves it behind, and the retry has to be able to push its own.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", summary.lower()).strip("-")[:48].strip("-")
    return "release/%s-%s" % (slug or "packages",
                              time.strftime("%Y%m%d%H%M%S", time.gmtime()))


def await_gate(branch, check, timeout, interval=15):
    """Block until `check` concludes on `branch`'s pull request -> (ok, detail).

    Polls rather than using `gh pr checks --watch`, which returns immediately
    when nothing has registered yet -- the normal state for the first seconds
    after a dispatch, and from the outside indistinguishable from success.

    Reads gh's own `bucket` (pass/fail/pending/skipping/cancel) instead of
    enumerating raw states, so a new state name upstream cannot be mistaken for
    a pass here.
    """
    verdict = {"pass": True, "skipping": True, "fail": False, "cancel": False}
    deadline = time.time() + timeout
    while True:
        raw = gh(["pr", "checks", branch, "--json", "name,state,bucket"],
                 check=False)
        try:
            runs = json.loads(raw) if raw else []
        except ValueError:
            runs = []
        # Every run under that name, not the first: the dispatch can leave two
        # on the same commit when the pull_request event fired as well, and a
        # stale pass must not answer for a sibling that is still running.
        buckets = [r.get("bucket") for r in runs if r.get("name") == check]
        results = [verdict.get(b) for b in buckets]
        if results and all(r is not None for r in results):
            failed = [b for b, r in zip(buckets, results) if not r]
            return not failed, ", ".join(failed or buckets)
        if time.time() >= deadline:
            return False, "still not conclusive after %ds" % timeout
        time.sleep(interval)


def merge_release_pr(branch, base, title, args):
    """Open, gate and merge the release PR; return the merged commit on `base`.

    The returned sha is the point of this function. The merge is a squash, so
    the commit that lands on `base` is not the one on the branch -- tagging the
    branch's would tag a commit no branch reaches, which is exactly the failure
    `--atomic` was added to stop.
    """
    body = ("Automated release commit, opened by `scripts/release.py`.\n\n"
            "Merging this cuts the tags; the branch is deleted on merge.")
    gh(["pr", "create", "--base", base, "--head", branch,
        "--title", title, "--body", body])
    print("[pr  ] %s" % gh(["pr", "view", branch, "--json", "url", "-q", ".url"]))

    if args.gate_check:
        if args.gate_workflow:
            # Only for a caller whose credential cannot make the pull request
            # fire `pull_request` workflows by itself. It does not lift an
            # approval gate: that is decided by who authored the pull request,
            # and a dispatched run waits behind it exactly the same.
            gh(["workflow", "run", args.gate_workflow, "--ref", branch],
               check=False)
        print("[gate] waiting for %r" % args.gate_check)
        ok, detail = await_gate(branch, args.gate_check, args.gate_timeout)
        if not ok:
            sys.stderr.write(
                "the release PR did not pass %r (%s); it is left open at %s "
                "with the branch intact -- fix, merge it by hand, then tag:\n"
                "  git tag -a <pkg>@<version> -m '<pkg> <version>' origin/%s\n"
                % (args.gate_check, detail, branch, base))
            raise SystemExit(1)
        print("[gate] %s: %s" % (args.gate_check, detail))

    # --match-head-commit refuses the merge if anything reached the branch after
    # the gate passed, so what merges is what was tested.
    gh(["pr", "merge", branch, "--squash", "--delete-branch",
        "--match-head-commit", git(["rev-parse", branch]),
        "--subject", title, "--body", ""])
    print("[pr  ] squashed into %s, branch deleted" % base)

    git(["fetch", "origin", base])
    return git(["rev-parse", "origin/%s" % base])


def main():
    global WORKSPACE
    parser = argparse.ArgumentParser(description=__doc__)
    workspace.add_arguments(parser)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--package", action="append", default=[])
    parser.add_argument("--bump", choices=versions.LEVELS)
    parser.add_argument("--no-tag", action="store_true")
    parser.add_argument("--no-commit", action="store_true")
    parser.add_argument("--no-push", action="store_true")
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--pull-request", action="store_true")
    parser.add_argument("--gate-check", default="workspace gates")
    parser.add_argument("--gate-workflow", default="")
    parser.add_argument("--gate-timeout", type=int, default=1800)
    args = parser.parse_args()

    if args.pull_request and args.no_push:
        parser.error("--pull-request has to push the release branch for a pull "
                     "request to exist; --no-push contradicts it")

    WORKSPACE, marketplace = workspace.resolve(args)
    packages_dir = os.path.join(WORKSPACE, "packages")
    manifest = os.path.join(marketplace, "apm.yml")
    if not os.path.isfile(manifest):
        sys.stderr.write("no marketplace apm.yml at %s\n" % manifest)
        return 1
    if not os.path.isdir(packages_dir):
        sys.stderr.write("no packages/ in %s\n" % WORKSPACE)
        return 1

    # Same code `apm run versions` prints from, so a preview cannot disagree
    # with what gets published.
    planned, skipped = versions.plan(WORKSPACE, only=args.package,
                                     force=args.bump)
    versions.report(planned, skipped)

    if not planned:
        print("\nnothing to release")
        return 0

    if not args.dry_run:
        soiled = refuse_dirty(WORKSPACE, marketplace, args.allow_dirty)
        if soiled:
            return 1

    if args.dry_run:
        print("\n[dry-run] no files written")
        return 0

    for p in planned:
        set_package_version(
            os.path.join(packages_dir, p.directory, "apm.yml"), p.next)
        set_manifest_version(manifest, p.name, p.next)

    packer = subprocess.run(
        [sys.executable, workspace.script("scripts", "pack-marketplace.py"),
         "--repo", WORKSPACE, "--marketplace", marketplace])
    if packer.returncode != 0:
        sys.stderr.write("packing failed; versions were written but nothing was "
                         "committed or tagged\n")
        return 1

    if args.no_commit:
        print("\n[--no-commit] both trees left dirty for inspection")
        return 0

    summary = ", ".join("%s %s" % (p.name, p.next) for p in planned)
    message = "chore(release): %s" % summary
    tags = [] if args.no_tag else ["%s@%s" % (p.name, p.next) for p in planned]

    # Read before any branch switch: the pull request targets whatever was
    # checked out, so releasing from a maintenance branch stays on it.
    base = git(["rev-parse", "--abbrev-ref", "HEAD"])
    branch = release_branch(summary) if args.pull_request else None
    if branch:
        git(["switch", "-c", branch])
        print("[git ] %s off %s" % (branch, base))

    git(["add", "-A"])
    if git(["status", "--porcelain"]):
        git(["commit", "-m", message])
        print("[git ] committed in .llmctl")

    git(["add", "-A"], cwd=marketplace)
    if git(["status", "--porcelain"], cwd=marketplace):
        git(["commit", "-m", message], cwd=marketplace)
        print("[git ] committed in the marketplace")

    if args.no_push:
        for tag in tags:
            cut_tag(tag)
            cut_tag(tag, cwd=marketplace)
            print("[tag ] %s" % tag)
        print("\nReleased %d package(s), unpushed. The tags are the baseline for "
              "the next release, so push both repos:\n"
              "  git -C %s push --atomic --follow-tags\n"
              "  git -C %s push --atomic --follow-tags"
              % (len(planned), WORKSPACE, marketplace))
        return 0

    if branch:
        # The commit must reach the remote before a pull request can exist, but
        # its tags must not travel with it: the squash merge rewrites the commit,
        # so a tag cut now would name one that never lands on `base`.
        git(["push", "--atomic", "-u", "origin", branch])
        merged = merge_release_pr(branch, base, message, args)
        for tag in tags:
            cut_tag(tag, at=merged)
            print("[tag ] %s -> %s" % (tag, merged[:12]))
        if tags:
            git(["push", "--atomic", "origin"] + tags)
            print("[push] %d tag(s)" % len(tags))
    else:
        for tag in tags:
            cut_tag(tag)
            print("[tag ] %s" % tag)
        print("[push] workspace")
        # --atomic so a rejected branch takes its tags down with it: the tag is
        # the next release's baseline, and one that outlives its commit silently
        # retires the package.
        git(["push", "--atomic", "--follow-tags", "origin", "HEAD"])

    # The marketplace is generated output with nothing to gate, so it is pushed
    # directly either way -- but only now, after the workspace half has landed.
    # Publishing bundles for a release that never merged is the worse failure.
    for tag in tags:
        cut_tag(tag, cwd=marketplace)
        print("[tag ] %s (marketplace)" % tag)
    print("[push] marketplace")
    git(["push", "--atomic", "--follow-tags", "origin", "HEAD"], cwd=marketplace)

    print("\nReleased and pushed %d package(s)." % len(planned))
    return 0


if __name__ == "__main__":
    sys.exit(main())
