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
                  the upstream terms its provenance records
  parser parity   check-licenses.py and check-updates.ps1 must find the same
                  tracked entries. They parse the same frontmatter in different
                  languages, and the object form fails *silently* when they
                  disagree -- a file just stops being tracked, with no error

Usage:
  python scripts/check.py --repo PATH [--skip NAME]

  --repo   the workspace to check

Exit codes: 0 all gates pass, 1 one or more failed.
"""
import argparse
import json
import os
import shutil
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


def gate_parity(ws):
    """The two provenance parsers must agree on what is tracked."""
    py = gatelib.sh([sys.executable,
                     workspace.script("scripts", "check-licenses.py"),
                     "--repo", ws, "--json"], ws)
    if py.returncode not in (0, 1) or not py.stdout.strip():
        return False, "check-licenses.py --json produced no output"
    mine = {(e["file"], e["url"]) for e in json.loads(py.stdout)["entries"]
            if e["kind"] == "adaptedFrom"}

    # The PowerShell audit only scans *.agent.md / SKILL.md / *.instructions.md /
    # *.prompt.md, so reference files it never sees are not a disagreement.
    scanned = {m for m in mine if os.path.basename(m[0]) in ("SKILL.md",) or
               m[0].endswith((".agent.md", ".instructions.md", ".prompt.md"))}

    # A workspace of wholly original content tracks nothing, and check-updates.ps1
    # treats an empty scan as an error. Two parsers that both found nothing agree.
    if not scanned:
        return True, "no tracked provenance entries; parity is vacuous"

    pwsh = shutil.which("pwsh") or shutil.which("powershell")
    if not pwsh:
        return True, "PowerShell absent; parity not checked"
    script = workspace.script(".apm", "skills", "meta-upstream-sync",
                              "scripts", "check-updates.ps1")
    ps = gatelib.sh([pwsh, "-NoProfile", "-File", script, "-RepoRoot", ws,
                     "-OutputJson"], ws)
    if ps.returncode != 0 or not ps.stdout.strip():
        return False, "check-updates.ps1 failed: " + ps.stderr.strip()[:160]
    try:
        theirs = {(r["id"], r["sourceUrl"]) for r in json.loads(ps.stdout)["results"]}
    except ValueError:
        return False, "check-updates.ps1 emitted unparseable JSON"

    if scanned != theirs:
        only_py = sorted(scanned - theirs)[:3]
        only_ps = sorted(theirs - scanned)[:3]
        return False, ("parsers disagree: %d vs %d entries; py-only=%s ps-only=%s"
                       % (len(scanned), len(theirs), only_py, only_ps))
    return True, "%d tracked entries, both parsers agree" % len(theirs)


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
    gates.run("parity", "both provenance parsers agree", lambda: gate_parity(ws))
    return gates.report()


if __name__ == "__main__":
    sys.exit(main())
