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

The commit scope (`feat(core):`) is checked against the paths and a mismatch is
reported, so the convention stays meaningful without being load-bearing -- a
typo'd scope should not silently skip a release.

Tags are the baseline, and `last_tag()` reads local ones, so a clone fetched
without tags -- shallow, or --no-tags -- measures from nothing and every package
bumps off its entire history. Hence the `git fetch --tags` below. The tags this
creates are annotated because the push at the end uses `--follow-tags`, which
carries annotated tags only; lightweight ones need `--tags` instead.

Usage:
  python scripts/release.py [--dry-run] [--package NAME] [--bump LEVEL]
                            [--update-deps] [--no-tag] [--no-commit] [--no-push]

  --dry-run      show what would change; make no commits, tags, or version edits
                 (tags are still fetched, or the preview would be wrong)
  --package      release only these packages (repeatable)
  --bump         force a level instead of deriving it
  --update-deps  refresh pinned APM dependencies first, so a moved upstream SHA
                 ships as an ordinary release rather than a hand edit
  --no-tag       bump and pack, but create no tags
  --no-commit    leave both working trees dirty for inspection
  --no-push      commit and tag locally, but do not push

A repo that has never been released has no baseline. Seed one by hand, once
(the .llmctl repos are already seeded; a new workspace is not):

  git tag -a <package>@<current-version> -m "<package> <current-version>" <commit>
  git push origin --tags

Exit codes: 0 released (or nothing to do), 1 error.
"""
import argparse
import io
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGES = os.path.join(REPO, "packages")

TYPE_RE = re.compile(r"^(?P<type>[a-z]+)(?:\((?P<scope>[^)]*)\))?(?P<bang>!)?:")
LEVELS = ("patch", "minor", "major")


def git(args, cwd=REPO, check=True):
    result = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True)
    if check and result.returncode != 0:
        sys.stderr.write("git %s failed in %s\n%s\n"
                         % (" ".join(args), cwd, result.stderr.strip()))
        raise SystemExit(1)
    return result.stdout.strip()


def scalar(path, key):
    """Read a top-level scalar from an apm.yml without a YAML dependency."""
    for line in io.open(path, encoding="utf-8"):
        m = re.match(r"^%s:\s*(.+?)\s*$" % key, line)
        if m:
            return m.group(1).strip("\"'")
    return None


def discover():
    """Every packages/<dir>/ holding an apm.yml, as (dir_name, name, version)."""
    found = []
    for entry in sorted(os.listdir(PACKAGES)):
        manifest = os.path.join(PACKAGES, entry, "apm.yml")
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


def bump(version, level):
    parts = version.split(".")
    while len(parts) < 3:
        parts.append("0")
    major, minor, patch = (int(re.sub(r"\D.*$", "", p) or 0) for p in parts[:3])
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--marketplace", default=os.environ.get(
        "LLMCTL_MARKETPLACE_DIR",
        os.path.join(os.path.dirname(REPO), ".llmctl-marketplace")))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--package", action="append", default=[])
    parser.add_argument("--bump", choices=LEVELS)
    parser.add_argument("--update-deps", action="store_true")
    parser.add_argument("--no-tag", action="store_true")
    parser.add_argument("--no-commit", action="store_true")
    parser.add_argument("--no-push", action="store_true")
    args = parser.parse_args()

    marketplace = os.path.abspath(args.marketplace)
    manifest = os.path.join(marketplace, "apm.yml")
    if not os.path.isfile(manifest):
        sys.stderr.write("no marketplace apm.yml at %s\n" % manifest)
        return 1

    packages = discover()
    if args.package:
        wanted = set(args.package)
        packages = [p for p in packages if p[0] in wanted or p[1] in wanted]
        if not packages:
            sys.stderr.write("no package matched %s\n" % ", ".join(sorted(wanted)))
            return 1

    # Tags are the baseline for every bump below, and they live on the remote.
    # Without this a fresh clone sees none and reads the whole history instead.
    git(["fetch", "--tags", "origin"], check=False)

    if args.update_deps and not args.dry_run:
        print("[deps] apm update")
        subprocess.run(["apm", "update", "-y"], cwd=REPO)

    planned = []
    for package_dir, name, version in packages:
        tag = last_tag(name)
        commits = commits_since(tag, "packages/%s" % package_dir)
        if not commits and not args.bump:
            print("[skip] %-18s no commits since %s" % (name, tag or "the start"))
            continue
        level, mismatches = derive(commits, package_dir)
        level = args.bump or level
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
        set_package_version(os.path.join(PACKAGES, package_dir, "apm.yml"), nxt)
        set_manifest_version(manifest, name, nxt)

    packer = subprocess.run(
        [sys.executable, os.path.join(REPO, "scripts", "pack-marketplace.py"),
         "--marketplace", marketplace])
    if packer.returncode != 0:
        sys.stderr.write("packing failed; versions were written but nothing was "
                         "committed or tagged\n")
        return 1

    if args.no_commit:
        print("\n[--no-commit] both trees left dirty for inspection")
        return 0

    summary = ", ".join("%s %s" % (n, v) for _, n, _, v in planned)
    git(["add", "-A"])
    if git(["status", "--porcelain"]):
        git(["commit", "-m", "chore(release): %s" % summary])
        print("[git ] committed in .llmctl")

    git(["add", "-A"], cwd=marketplace)
    if git(["status", "--porcelain"], cwd=marketplace):
        git(["commit", "-m", "chore(release): %s" % summary], cwd=marketplace)
        print("[git ] committed in the marketplace")

    if not args.no_tag:
        for _, name, _, nxt in planned:
            tag = "%s@%s" % (name, nxt)
            # Annotated, not lightweight: `--follow-tags` below ignores
            # lightweight tags, so those would never reach the remote.
            message = "%s %s" % (name, nxt)
            git(["tag", "-a", tag, "-m", message])
            git(["tag", "-a", tag, "-m", message], cwd=marketplace)
            print("[tag ] %s" % tag)

    if args.no_push:
        print("\nReleased %d package(s), unpushed. The tags are the baseline for "
              "the next release, so push both repos:\n"
              "  git -C %s push --follow-tags\n  git -C %s push --follow-tags"
              % (len(planned), REPO, marketplace))
        return 0

    for label, tree in (("workspace", REPO), ("marketplace", marketplace)):
        print("[push] %s" % label)
        git(["push", "--follow-tags", "origin", "HEAD"], cwd=tree)

    print("\nReleased and pushed %d package(s)." % len(planned))
    return 0


if __name__ == "__main__":
    sys.exit(main())
