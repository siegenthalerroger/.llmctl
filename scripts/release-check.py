#!/usr/bin/env python3
"""Check what a release would publish. Writes nothing, so it is safe to re-run.

Every gate here reads the *marketplace* -- the packed bundles and the manifests
a release rewrites -- and compares it against the workspace it was packed from.
None of them can run without both repos, which is why they are not in check.py:
a marketplace that is absent is a missing input, not a passing gate, and this
script says so and exits 1 rather than reporting green on nothing.

Run check.py first; the two are complementary, not nested. `apm run release`
does not call either -- the release workflow runs both ahead of it.

Gates, cheapest first so an obvious failure reports fast:

  notices         gen-notices.py --check -- THIRD-PARTY-NOTICES.md is current
  versions        apm pack --check-versions -- per-package versions agree with
                  the manifest (exit 3 means they do not)
  manifest drift  apm pack --check-clean -- the committed marketplace.json files
                  match what would be generated (exit 4 means they do not)
  plugin validity claude plugin validate on each bundle, when the CLI is present

Usage:
  python scripts/release-check.py --repo PATH --marketplace PATH [--skip NAME]

  --repo         the workspace the bundles were packed from
  --marketplace  the marketplace it publishes into

Exit codes: 0 all gates pass, 1 one or more failed or the marketplace is absent.
"""
import argparse
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gates as gatelib  # noqa: E402
import workspace  # noqa: E402


def gate_notices(ws, marketplace):
    got = gatelib.sh([sys.executable,
                      workspace.script("scripts", "gen-notices.py"),
                      "--repo", ws, "--marketplace", marketplace, "--check"], ws)
    return got.returncode == 0, (got.stderr or got.stdout).strip().split("\n")[-1]


def gate_apm(marketplace, flag, bad_code, label):
    got = gatelib.sh(["apm", "pack", "--dry-run", "--offline", flag], marketplace)
    if got.returncode == 0:
        return True, ""
    if got.returncode == bad_code:
        lines = [l.strip() for l in got.stdout.split("\n") if l.strip()]
        return False, "%s (exit %d): %s" % (label, bad_code,
                                            "; ".join(lines[-3:])[:200])
    return False, "apm pack exited %d: %s" % (got.returncode, got.stderr.strip()[:160])


def gate_plugins(marketplace):
    if not shutil.which("claude"):
        return True, "claude CLI absent; bundles not validated"
    plugins = os.path.join(marketplace, "plugins")
    if not os.path.isdir(plugins):
        return False, "no plugins/ directory"
    bad = []
    for entry in sorted(os.listdir(plugins)):
        path = os.path.join(plugins, entry)
        if not os.path.isdir(path):
            continue
        got = gatelib.sh(["claude", "plugin", "validate", "."], path)
        if got.returncode != 0:
            bad.append("%s: %s" % (entry, (got.stderr or got.stdout).strip()[:90]))
    return not bad, "; ".join(bad)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    workspace.add_arguments(parser)
    gatelib.add_arguments(parser)
    args = parser.parse_args()
    ws, marketplace = workspace.resolve(args)

    # An empty directory is the shape a failed cross-repo checkout leaves behind:
    # actions/checkout git-inits the path before it discovers it cannot read the
    # repo. Look for the file that makes it a marketplace, not for the directory.
    if not os.path.isfile(os.path.join(marketplace, "apm.yml")):
        sys.stderr.write("no apm.yml at %s -- these gates read the packed "
                         "marketplace and have nothing to check without it\n"
                         % marketplace)
        return 1

    print("release-check: %s\n           -> %s\n" % (ws, marketplace))
    gates = gatelib.Gates(args.skip)
    gates.run("notices", "THIRD-PARTY-NOTICES.md is current",
              lambda: gate_notices(ws, marketplace))
    gates.run("versions", "per-package version alignment",
              lambda: gate_apm(marketplace, "--check-versions", 3, "version alignment"))
    gates.run("drift", "marketplace manifests match",
              lambda: gate_apm(marketplace, "--check-clean", 4, "manifest drift"))
    gates.run("plugins", "each bundle validates", lambda: gate_plugins(marketplace))
    return gates.report()


if __name__ == "__main__":
    sys.exit(main())
