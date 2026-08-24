#!/usr/bin/env python3
"""What each package's next version would be, and why.

Split out of release.py so the question can be asked without answering it. This
reads tags and commit subjects and prints; it writes no file, cuts no tag and
opens nothing. release.py imports it rather than keeping a second copy, so the
number reported here is the number a release would publish -- a preview that
can disagree with the release is worse than no preview.

Two inputs decide a version, and they answer different questions:

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

Tags are the baseline, and they are read locally, so a clone fetched without
tags -- shallow, or --no-tags -- measures from nothing and every package bumps
off its entire history. Hence the `git fetch --tags` below.

Usage:
  python scripts/versions.py --repo PATH [--package NAME] [--bump LEVEL]
                             [--json] [--no-fetch]

  --repo       the workspace to inspect. These scripts live in `.llmctl` but
               read any repo laid out the same way, so it is never guessed
  --package    report only these packages (repeatable)
  --bump       force a level instead of deriving it, to preview what
               `release.py --bump LEVEL` would choose
  --json       machine-readable, for a caller that wants the number
  --no-fetch   skip `git fetch --tags`, for an offline or read-only checkout

Exit codes: 0 reported (even when nothing would bump), 1 error.
"""
import argparse
import collections
import io
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import workspace  # noqa: E402

TYPE_RE = re.compile(r"^(?P<type>[a-z]+)(?:\((?P<scope>[^)]*)\))?(?P<bang>!)?:")
LEVELS = ("patch", "minor", "major")

# `mismatches` is [(subject, scope)] -- commits whose scope names a package
# other than the one whose paths they touched.
Plan = collections.namedtuple(
    "Plan", "directory name current level next tag commits mismatches")
Skip = collections.namedtuple("Skip", "name tag")


def git(args, repo, check=True):
    result = subprocess.run(["git"] + args, cwd=repo,
                            capture_output=True, text=True)
    if check and result.returncode != 0:
        sys.stderr.write("git %s failed in %s\n%s\n"
                         % (" ".join(args), repo, result.stderr.strip()))
        raise SystemExit(1)
    return result.stdout.strip()


def scalar(path, key):
    """Read a top-level scalar from an apm.yml without a YAML dependency."""
    for line_ in io.open(path, encoding="utf-8"):
        m = re.match(r"^%s:\s*(.+?)\s*$" % key, line_)
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


def last_tag(repo, name):
    """Newest `<name>@<version>` tag by version order, or None."""
    out = git(["tag", "--list", "%s@*" % name, "--sort=-v:refname"], repo)
    return out.split("\n")[0] if out else None


def commits_since(repo, tag, path):
    """(subject, body) for every commit touching `path` since `tag`."""
    span = ["%s..HEAD" % tag] if tag else []
    raw = git(["log"] + span + ["--format=%s%x1f%b%x1e", "--", path], repo)
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


def plan(repo, only=(), force=None, fetch=True):
    """(plans, skips) for every package, in discovery order.

    `force` substitutes for the derived level and, like release.py, also makes a
    package with no commits eligible -- that is how a version is moved by hand.
    """
    packages_dir = os.path.join(repo, "packages")
    if not os.path.isdir(packages_dir):
        sys.stderr.write("no packages/ in %s\n" % repo)
        raise SystemExit(1)

    packages = discover(packages_dir)
    if only:
        wanted = set(only)
        packages = [p for p in packages if p[0] in wanted or p[1] in wanted]
        if not packages:
            sys.stderr.write("no package matched %s\n" % ", ".join(sorted(wanted)))
            raise SystemExit(1)

    if fetch:
        # Tags are the baseline for every bump below, and they live on the
        # remote. Without this a fresh clone sees none and reads the whole
        # history instead.
        git(["fetch", "--tags", "origin"], repo, check=False)

    plans, skips = [], []
    for package_dir, name, version in packages:
        tag = last_tag(repo, name)
        commits = commits_since(repo, tag, "packages/%s" % package_dir)
        if not commits and not force:
            skips.append(Skip(name, tag))
            continue
        level, mismatches = derive(commits, package_dir)
        level = force or cap(version, level)
        plans.append(Plan(package_dir, name, version, level,
                          bump(version, level), tag, len(commits), mismatches))
    return plans, skips


def line(p):
    """The one-line summary, shared so release.py and this CLI cannot diverge."""
    return ("[bump] %-18s %s -> %-8s (%s, %d commit(s) since %s)"
            % (p.name, p.current, p.next, p.level, p.commits, p.tag or "the start"))


def skip_line(s):
    return "[skip] %-18s no commits since %s" % (s.name, s.tag or "the start")


def mismatch_lines(p):
    return ["       ! scope `%s` but the change is under packages/%s: %s"
            % (scope, p.directory, subject[:60]) for subject, scope in p.mismatches]


def report(plans, skips, out=sys.stdout):
    """Print every plan and skip, mismatches included, in discovery order."""
    for p in plans:
        print(line(p), file=out)
        for warning in mismatch_lines(p):
            print(warning, file=out)
    for s in skips:
        print(skip_line(s), file=out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    workspace.add_arguments(parser, marketplace=False)
    parser.add_argument("--package", action="append", default=[])
    parser.add_argument("--bump", choices=LEVELS)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-fetch", action="store_true")
    args = parser.parse_args()

    repo, _ = workspace.resolve(args)
    plans, skips = plan(repo, only=args.package, force=args.bump,
                        fetch=not args.no_fetch)

    if args.json:
        json.dump({
            "bumps": [{"package": p.directory, "name": p.name,
                       "current": p.current, "level": p.level, "next": p.next,
                       "commits": p.commits, "since": p.tag,
                       "scope_mismatches": [{"subject": s, "scope": c}
                                            for s, c in p.mismatches]}
                      for p in plans],
            "skipped": [{"name": s.name, "since": s.tag} for s in skips],
        }, sys.stdout, indent=2)
        print()
        return 0

    report(plans, skips)
    if not plans:
        print("\nnothing to release")
    return 0


if __name__ == "__main__":
    sys.exit(main())
