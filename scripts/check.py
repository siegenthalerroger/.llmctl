#!/usr/bin/env python3
"""Check the workspace itself. Writes nothing, needs no marketplace.

These are the gates that answer "is this repo well-formed?", and every one of
them reads only the workspace: nothing here looks at what was published, so a
contributor with no marketplace clone -- and a PR job that checks out one repo
-- runs the full set rather than a silently reduced one. The release-shaped
gates live in release-check.py, which needs the marketplace to say anything at
all. Splitting them is what lets each script fail loudly when its inputs are
missing instead of skipping past them.

Gates, cheapest first so an obvious failure reports fast:

  frontmatter     .apm/hooks/validate-customization-frontmatter.py --all -- the
                  same rules the edit-time hook applies, over the whole tree.
                  The hook only sees files edited in a Claude session
  licences        scripts/check-licenses.py -- every file's licence can carry
                  the upstream terms its provenance records, and no provenance
                  block parses to nothing. That last one is the silent failure:
                  a block that yields no entries drops the file out of every
                  consumer -- this gate, the notices, the drift audit -- with no
                  error anywhere. They all read scripts/provenance.py, so one
                  parse either works for all of them or fails here

Usage:
  python scripts/check.py --repo PATH [--skip NAME]

  --repo   the workspace to check

Exit codes: 0 all gates pass, 1 one or more failed.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gates as gatelib  # noqa: E402
import workspace  # noqa: E402


def gate_frontmatter(ws):
    """The edit-time hook's rules, applied to every file rather than one."""
    got = gatelib.sh([sys.executable,
                      workspace.script(".apm", "hooks",
                                       "validate-customization-frontmatter.py"),
                      "--repo", ws, "--all"], ws)
    lines = [l.strip() for l in (got.stdout + got.stderr).split("\n") if l.strip()]
    if got.returncode == 0:
        return True, lines[-1].replace("[customization-frontmatter] ", "") if lines else ""
    errors = [l for l in lines if "error:" in l]
    return False, "; ".join(errors[:3])[:200]


def gate_licenses(ws):
    got = gatelib.sh([sys.executable,
                      workspace.script("scripts", "check-licenses.py"),
                      "--repo", ws], ws)
    tail = (got.stderr or got.stdout).strip().split("\n")[-1] if got.returncode else \
        (got.stdout.strip().split("\n")[0] if got.stdout.strip() else "")
    return got.returncode == 0, tail


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    workspace.add_arguments(parser, marketplace=False)
    gatelib.add_arguments(parser)
    args = parser.parse_args()
    ws, _ = workspace.resolve(args)

    print("check: %s\n" % ws)
    gates = gatelib.Gates(args.skip)
    gates.run("frontmatter", "customization frontmatter conventions",
              lambda: gate_frontmatter(ws))
    gates.run("licences", "provenance obligations vs declared licences",
              lambda: gate_licenses(ws))
    return gates.report()


if __name__ == "__main__":
    sys.exit(main())
