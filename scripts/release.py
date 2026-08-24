#!/usr/bin/env python3
"""Derive each package's next version from its commits, then pack and tag.

Packages version independently. A change to `ops` bumps `ops` and nothing else,
so a version number always means something changed in that package -- which is
the whole reason this is not lockstep.

Two inputs decide a release, and they answer different questions:

  which package   the paths a commit touched. Authoritative: it is what actually
                  changed, and it cannot be mistyped.
  how much        the conventional-commit type. `!` or a BREAKING CHANGE trailer
                  is major, `feat` is minor, anything else is patch.

While a package is still `0.y.z` that last rule is capped at minor. SemVer 4
puts major version zero outside the compatibility promise -- nothing is declared
stable, so there is no stability for a `!` to break, and letting one mint 1.0.0
would announce an API commitment nobody made. Reaching 1.0.0 is a decision, not
a side effect: `--bump major` is how it is taken. Past 1.0.0 the cap lifts and
`!` means major, as it should.

The commit scope (`feat(core):`) is checked against the paths and a mismatch is
reported, so the convention stays meaningful without being load-bearing -- a
typo'd scope should not silently skip a release.

Tags are the baseline, and `last_tag()` reads local ones, so a clone fetched
without tags -- shallow, or --no-tags -- measures from nothing and every package
bumps off its entire history. Hence the `git fetch --tags` below. The tags this
creates are annotated because the push at the end uses `--follow-tags`, which
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

One wrinkle drives the shape of that flow. A pull request opened with
GITHUB_TOKEN does not fire `pull_request` workflows -- GitHub suppresses them so
a token cannot make a workflow trigger itself -- so a required status check
would never report and the merge would wait forever. `workflow_dispatch` is the
documented exception, so the gate workflow is dispatched by hand against the
release branch. Run this with a PAT or GitHub App token instead and the check
fires on its own; the dispatch is then a harmless duplicate.

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
  --pull-request merge the workspace commit through a pull request instead of
                 pushing to the base branch. Requires the `gh` CLI, authenticated
  --gate-check   the status check that must pass before the release PR merges
                 (default: "workspace gates"). Empty string waits for nothing
  --gate-workflow the workflow file to dispatch so that check reports
                 (default: "checks.yml")
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
import workspace  # noqa: E402

# The repo being released, set once from --repo. A module-level name rather
# than a `cwd=WORKSPACE` default because a default argument binds at def time,
# which is before the flags are parsed -- every git call would run against the
# tooling checkout instead, committing and tagging in the wrong repo.
WORKSPACE = None

TYPE_RE = re.compile(r"^(?P<type>[a-z]+)(?:\((?P<scope>[^)]*)\))?(?P<bang>!)?:")
LEVELS = ("patch", "minor", "major")


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


def scalar(path, key):
    """Read a top-level scalar from an apm.yml without a YAML dependency."""
    for line in io.open(path, encoding="utf-8"):
        m = re.match(r"^%s:\s*(.+?)\s*$" % key, line)
        if m:
            return m.group(1).strip("\"'")
    return None


def discover(packages_dir):
    """Every packages/<dir>/ holding an apm.yml, as (dir_name, name, version)."""
    found = []
    for entry in sorted(os.listdir(packages_dir)):
        manifest = os.path.join(packages_dir, entry, "apm.yml")
        if not os.path.isfile(manifest):
            continue
        name, version = scalar(manifest, "name"), scalar(manifest, "version")
        if not name or not version:
            sys.stderr.write("%s: missing name or version\n" % manifest)
            raise SystemExit(1)
        found.append((entry, name, version))
    return found


def last_tag(name):
    """Newest `<name>@<version>` tag by version order, or None."""
    out = git(["tag", "--list", "%s@*" % name, "--sort=-v:refname"])
    return out.split("\n")[0] if out else None


def commits_since(tag, path):
    """(subject, body) for every commit touching `path` since `tag`."""
    span = ["%s..HEAD" % tag] if tag else []
    raw = git(["log"] + span + ["--format=%s%x1f%b%x1e", "--", path])
    entries = []
    for chunk in raw.split("\x1e"):
        chunk = chunk.strip()
        if not chunk:
            continue
        subject, _, body = chunk.partition("\x1f")
        entries.append((subject.strip(), body.strip()))
    return entries


def derive(commits, package_dir):
    """Highest bump level the commits justify, plus any scope mismatches."""
    level, mismatches = None, []
    for subject, body in commits:
        m = TYPE_RE.match(subject)
        breaking = bool(m and m.group("bang")) or "BREAKING CHANGE" in body
        if breaking:
            this = "major"
        elif m and m.group("type") == "feat":
            this = "minor"
        else:
            this = "patch"
        if level is None or LEVELS.index(this) > LEVELS.index(level):
            level = this
        scope = m.group("scope") if m else None
        if scope and scope != package_dir:
            mismatches.append((subject, scope))
    return level, mismatches


def parts_of(version):
    """(major, minor, patch) as ints, tolerating `1.2` and `1.2.3-rc1`."""
    parts = version.split(".")
    while len(parts) < 3:
        parts.append("0")
    return tuple(int(re.sub(r"\D.*$", "", p) or 0) for p in parts[:3])


def cap(version, level):
    """`level`, held to minor while the package is still 0.y.z.

    SemVer 4 puts major version zero outside the compatibility promise, so a
    breaking change there breaks nothing that was promised and must not mint
    1.0.0 on its own. Only the derived level is capped -- an explicit
    `--bump major` is the deliberate act that declares stability.
    """
    if level == "major" and parts_of(version)[0] == 0:
        return "minor"
    return level


def bump(version, level):
    major, minor, patch = parts_of(version)
    if level == "major":
        return "%d.0.0" % (major + 1)
    if level == "minor":
        return "%d.%d.0" % (major, minor + 1)
    return "%d.%d.%d" % (major, minor, patch + 1)


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
        for run in runs:
            if run.get("name") != check:
                continue
            ok = verdict.get(run.get("bucket"))
            if ok is not None:
                return ok, run.get("state") or run.get("bucket")
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
        # GITHUB_TOKEN cannot make a pull request fire `pull_request` workflows,
        # so the gate is asked for explicitly. Harmless when the PR was opened
        # with a credential that does trigger it -- the second run just agrees.
        gh(["workflow", "run", args.gate_workflow, "--ref", branch], check=False)
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
    parser.add_argument("--bump", choices=LEVELS)
    parser.add_argument("--no-tag", action="store_true")
    parser.add_argument("--no-commit", action="store_true")
    parser.add_argument("--no-push", action="store_true")
    parser.add_argument("--pull-request", action="store_true")
    parser.add_argument("--gate-check", default="workspace gates")
    parser.add_argument("--gate-workflow", default="checks.yml")
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

    packages = discover(packages_dir)
    if args.package:
        wanted = set(args.package)
        packages = [p for p in packages if p[0] in wanted or p[1] in wanted]
        if not packages:
            sys.stderr.write("no package matched %s\n" % ", ".join(sorted(wanted)))
            return 1

    # Tags are the baseline for every bump below, and they live on the remote.
    # Without this a fresh clone sees none and reads the whole history instead.
    git(["fetch", "--tags", "origin"], check=False)

    planned = []
    for package_dir, name, version in packages:
        tag = last_tag(name)
        commits = commits_since(tag, "packages/%s" % package_dir)
        if not commits and not args.bump:
            print("[skip] %-18s no commits since %s" % (name, tag or "the start"))
            continue
        level, mismatches = derive(commits, package_dir)
        level = args.bump or cap(version, level)
        for subject, scope in mismatches:
            print("       ! scope `%s` but the change is under packages/%s: %s"
                  % (scope, package_dir, subject[:60]))
        nxt = bump(version, level)
        print("[bump] %-18s %s -> %-8s (%s, %d commit(s) since %s)"
              % (name, version, nxt, level, len(commits), tag or "the start"))
        planned.append((package_dir, name, version, nxt))

    if not planned:
        print("\nnothing to release")
        return 0

    if args.dry_run:
        print("\n[dry-run] no files written")
        return 0

    for package_dir, name, _, nxt in planned:
        set_package_version(os.path.join(packages_dir, package_dir, "apm.yml"), nxt)
        set_manifest_version(manifest, name, nxt)

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

    summary = ", ".join("%s %s" % (n, v) for _, n, _, v in planned)
    message = "chore(release): %s" % summary
    tags = [] if args.no_tag else ["%s@%s" % (n, v) for _, n, _, v in planned]

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
