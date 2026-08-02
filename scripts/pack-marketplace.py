#!/usr/bin/env python3
"""Pack every package in this repo into the sibling `.llmctl-marketplace` repo.

The marketplace is published from a separate repository because a plugin host
(Cowork, Claude Desktop/Code) clones the marketplace repo and reads each
`packages[].source` path *as committed* — it never runs `apm install`. Bundles
therefore have to exist as files in that repo, and `apm pack` refuses to write
a marketplace manifest across a `..` boundary, so the two halves run separately:

  1. here   `apm install` + `apm pack -o <marketplace>/plugins` per package
             -> plugins/<name>-<version>/ with plugin.json, the skills/agents/
                commands, and an embedded apm.lock.yaml
             then strip upstream repo scaffolding (CI config, repo docs,
             nested plugin manifests) out of the vendored skills/
  2. there  `apm pack` -> .claude-plugin/marketplace.json (Claude)
                       + .agents/plugins/marketplace.json (Codex)

Between the two, `packages[].source` in the marketplace apm.yml is rewritten to
the versions just packed, because the bundle directory name is always
`<name>-<version>` and cannot be flattened.

Usage:
  python scripts/pack-marketplace.py [--marketplace PATH] [--dry-run]

  --marketplace  marketplace repo root
                 (default: $LLMCTL_MARKETPLACE_DIR, else ../.llmctl-marketplace)

Exit codes: 0 packed, 1 error (missing repo, apm failure, unknown package).
Dependency-free: only reads the scalar `name:`/`version:` keys it needs.
"""
import argparse
import importlib.util
import os
import re
import shutil
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGES = os.path.join(REPO, "packages")

sys.path.insert(0, os.path.join(REPO, "scripts"))
import provenance  # noqa: E402

# gen-notices.py is hyphenated, so it cannot be a plain import.
_spec = importlib.util.spec_from_file_location(
    "gen_notices", os.path.join(REPO, "scripts", "gen-notices.py"))
gen_notices = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen_notices)

# `apm install` materialises dependencies and deploys them next to the package.
# None of it is authored content, so it is removed after packing to keep the
# working tree clean — the bundle carries its own enriched apm.lock.yaml.
TRANSIENT = (".claude", ".agents", ".github/instructions", "apm_modules",
             ".mcp.json", ".vscode/mcp.json", "apm.lock.yaml", "build")

# A vendored upstream skill arrives as whatever its repo happens to contain.
# When the skill's SKILL.md sits at its repo root (e.g. blader/humanizer), APM
# copies the *entire* repo into skills/<name>/ — CI config, packaging
# manifests, repo-level docs. A plugin host reads none of it.
#
# `.claude-plugin/` is the one that matters beyond disk noise: hosts scan for
# `.claude-plugin/plugin.json` to detect a plugin, so leaving a vendored copy
# inside skills/ ships a plugin manifest nested inside a plugin bundle.
VENDOR_CRUFT_DIRS = (".github", ".gitlab", ".circleci", ".vscode", ".idea",
                     ".claude-plugin", ".git", "node_modules")
VENDOR_CRUFT_FILES = ("apm.yml", "apm.lock.yaml", ".apm-pin", ".gitignore",
                      ".gitattributes", ".editorconfig", "AGENTS.md",
                      "CLAUDE.md", "GEMINI.md", "README.md", "CONTRIBUTING.md",
                      "CODE_OF_CONDUCT.md", "SECURITY.md", "SUPPORT.md",
                      "package.json", "package-lock.json", "pnpm-lock.yaml",
                      "renovate.json")

# Attribution has to travel with the code — MIT requires the notice to be
# carried, Apache-2.0 the licence text — and the generated THIRD-PARTY-NOTICES
# depends on these surviving. Never strip them, whatever else matches above.
KEEP_PREFIXES = ("LICENSE", "LICENCE", "NOTICE", "COPYING")


def scalar(path, key):
    """Read a top-level scalar from an apm.yml without a YAML dependency."""
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            match = re.match(r"^%s:\s*(.+?)\s*$" % key, line)
            if match:
                return match.group(1).strip("\"'")
    return None


def run(args, cwd):
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write("%s failed in %s\n%s%s\n"
                         % (" ".join(args), cwd, result.stdout, result.stderr))
    return result.returncode == 0


def clean(package_dir, had_gitignore):
    targets = list(TRANSIENT)
    # `apm install` writes a .gitignore holding `apm_modules/`. Remove it only
    # when the package did not have one before — never clobber an authored file.
    if not had_gitignore:
        targets.append(".gitignore")
    for name in targets:
        target = os.path.join(package_dir, name)
        if os.path.isdir(target):
            shutil.rmtree(target, ignore_errors=True)
        elif os.path.isfile(target):
            os.remove(target)


def discover():
    """Every packages/<name>/ holding an apm.yml, as (dir, name, version)."""
    found = []
    for entry in sorted(os.listdir(PACKAGES)):
        manifest = os.path.join(PACKAGES, entry, "apm.yml")
        if not os.path.isfile(manifest):
            continue
        name = scalar(manifest, "name")
        version = scalar(manifest, "version")
        if not name or not version:
            sys.stderr.write("%s: missing name or version\n" % manifest)
            return None
        found.append((os.path.join(PACKAGES, entry), name, version))
    return found


def relocate_manifest(bundle_dir):
    """Move the packed plugin.json to where a plugin host looks for it.

    `apm pack` writes plugin.json at the bundle root; Claude Code, Desktop and
    Cowork all reject that layout with "requires .claude-plugin/plugin.json or
    a top-level SKILL.md". `apm install` reads either location, so the manifest
    is moved rather than duplicated.
    """
    root = os.path.join(bundle_dir, "plugin.json")
    nested_dir = os.path.join(bundle_dir, ".claude-plugin")
    if not os.path.isfile(root):
        return os.path.isfile(os.path.join(nested_dir, "plugin.json"))
    os.makedirs(nested_dir, exist_ok=True)
    shutil.move(root, os.path.join(nested_dir, "plugin.json"))
    return True


def strip_vendor_cruft(bundle_dir):
    """Drop upstream repo scaffolding from vendored skills in a packed bundle.

    Scoped to `skills/<name>/` only. The bundle root is left alone because
    relocate_manifest puts the plugin's own manifest in `.claude-plugin/`
    there, and the root `apm.lock.yaml` is what THIRD-PARTY-NOTICES is
    generated from.

    Deliberately a denylist of known scaffolding rather than an allowlist of
    known content: a skill may legitimately ship `scripts/`, `references/`,
    `assets/`, or anything else its SKILL.md links to, and silently dropping
    one of those breaks the skill at runtime with no error. Anything
    unrecognised stays — a few stale KB is cheaper than a broken skill.
    """
    skills_dir = os.path.join(bundle_dir, "skills")
    if not os.path.isdir(skills_dir):
        return []
    dropped = []
    for skill in sorted(os.listdir(skills_dir)):
        root = os.path.join(skills_dir, skill)
        if not os.path.isdir(root):
            continue
        for entry in sorted(os.listdir(root)):
            if entry.upper().startswith(KEEP_PREFIXES):
                continue
            target = os.path.join(root, entry)
            if os.path.isdir(target) and entry in VENDOR_CRUFT_DIRS:
                shutil.rmtree(target, ignore_errors=True)
            elif os.path.isfile(target) and entry in VENDOR_CRUFT_FILES:
                os.remove(target)
            else:
                continue
            dropped.append("%s/%s" % (skill, entry))
    return dropped


def licenses_needed(bundle_dir, dep_licenses):
    """SPDX ids whose full text has to ship inside this bundle.

    Three sources, because a bundle mixes three kinds of content: the repo
    defaults that cover the authored files, any per-file `license:` override, and
    the licence of every vendored upstream skill.
    """
    needed = {provenance.DEFAULT_CONTENT, provenance.DEFAULT_CODE}

    for sub in ("agents", "skills", "instructions", "commands"):
        top = os.path.join(bundle_dir, sub)
        if not os.path.isdir(top):
            continue
        for dirpath, _, filenames in os.walk(top):
            for name in sorted(filenames):
                if name.endswith(".md"):
                    declared = provenance.parse(os.path.join(dirpath, name))["declared"]
                    if declared:
                        needed.add(declared)

    for dep in dep_licenses:
        if dep:
            needed.add(dep)
    return sorted(n for n in needed if n not in ("NONE", "NOASSERTION"))


def add_licenses(bundle_dir, name, version, dep_licenses):
    """Put the licence files and a minimal manifest into a packed bundle.

    `apm pack` copies neither, and both matter downstream:

      LICENSE + LICENSES/  attribution has to travel with the content. MIT wants
                           its notice carried, Apache-2.0 the licence and NOTICE,
                           CC-BY-SA-4.0 the licence and a change indication.
      apm.yml              `apm pack --check-versions` reads each bundle's version
                           from its apm.yml; with none it reports `no_apm_yml` and
                           fails the release gate. Deliberately name/version/license
                           only -- carrying a `dependencies:` block here would
                           invite a re-resolve at install time.
    """
    shutil.copyfile(os.path.join(REPO, "LICENSE"),
                    os.path.join(bundle_dir, "LICENSE"))

    target = os.path.join(bundle_dir, "LICENSES")
    os.makedirs(target, exist_ok=True)
    carried = []
    for spdx in licenses_needed(bundle_dir, dep_licenses):
        source = os.path.join(REPO, "LICENSES", "%s.txt" % spdx)
        if not os.path.isfile(source):
            sys.stderr.write("%s: no licence text for %s in LICENSES/\n" % (name, spdx))
            return None
        shutil.copyfile(source, os.path.join(target, "%s.txt" % spdx))
        carried.append(spdx)

    # The expression names every licence in the bundle, not just the repo
    # defaults: a bundle carrying an Apache-2.0 file or an Apache-2.0 vendored
    # skill has to say so, or the SBOM understates what a consumer takes on.
    with open(os.path.join(bundle_dir, "apm.yml"), "w", encoding="utf-8") as handle:
        handle.write(
            "# Generated by scripts/pack-marketplace.py in .llmctl - do not edit.\n"
            "# Present so `apm pack --check-versions` can read this bundle's version.\n"
            "name: %s\nversion: %s\nlicense: %s\n"
            % (name, version, " AND ".join(carried)))
    return carried


def bundle_dep_licenses(bundle_dir, dep_map):
    """SPDX id of every upstream vendored into this bundle, via its lockfile."""
    found = set()
    for dep in gen_notices.read_lock_dependencies(bundle_dir):
        info = dep_map.get(gen_notices.slug(dep["repo_url"]))
        if info:
            found.add(info.get("spdx"))
        else:
            sys.stderr.write("%s: no licence recorded for %s - add it to "
                             "scripts/dependency-licenses.yml\n"
                             % (os.path.basename(bundle_dir), dep["repo_url"]))
    return found


def prune(plugins_dir, name, keep):
    """Drop bundles of `name` left over from earlier versions."""
    if not os.path.isdir(plugins_dir):
        return
    for entry in os.listdir(plugins_dir):
        if entry.startswith(name + "-") and entry != keep:
            shutil.rmtree(os.path.join(plugins_dir, entry), ignore_errors=True)


def retarget(manifest, packed):
    """Sync each packages[] entry's source path and version with what was packed.

    The bundle directory is always `<name>-<version>`, and `version:` is only
    emitted into marketplace.json when declared explicitly — the generator does
    not read it out of a packed bundle's plugin.json.
    """
    with open(manifest, encoding="utf-8") as handle:
        text = handle.read()
    updated = text
    for name, version in packed.items():
        entry = r"(- name: %s\n(?:\s+.*\n)*?\s+%%s: )" % re.escape(name)
        updated = re.sub(
            entry % "source" + r"\./plugins/%s-[^\s]+" % re.escape(name),
            r"\g<1>./plugins/%s-%s" % (name, version),
            updated,
        )
        updated = re.sub(entry % "version" + r"\S+",
                         r"\g<1>%s" % version, updated)
    if updated != text:
        with open(manifest, "w", encoding="utf-8") as handle:
            handle.write(updated)
    return updated != text


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--marketplace", default=os.environ.get(
        "LLMCTL_MARKETPLACE_DIR",
        os.path.join(os.path.dirname(REPO), ".llmctl-marketplace")))
    parser.add_argument("--dry-run", action="store_true",
                        help="list what would be packed, touch nothing")
    args = parser.parse_args()

    marketplace = os.path.abspath(args.marketplace)
    manifest = os.path.join(marketplace, "apm.yml")
    if not os.path.isfile(manifest):
        sys.stderr.write("no marketplace apm.yml at %s\n" % manifest)
        return 1

    packages = discover()
    if packages is None:
        return 1

    declared = set(re.findall(r"- name: (\S+)", open(manifest, encoding="utf-8").read()))
    plugins_dir = os.path.join(marketplace, "plugins")
    dep_map = gen_notices.read_license_map(
        os.path.join(REPO, "scripts", "dependency-licenses.yml"))
    packed = {}

    for package_dir, name, version in packages:
        if name not in declared:
            sys.stderr.write("%s is not listed in %s — add it or remove the package\n"
                             % (name, manifest))
            return 1
        print("[pack] %s %s" % (name, version))
        if args.dry_run:
            continue
        had_gitignore = os.path.isfile(os.path.join(package_dir, ".gitignore"))
        ok = (run(["apm", "install", "--target", "claude"], package_dir)
              and run(["apm", "pack", "-o", plugins_dir], package_dir))
        clean(package_dir, had_gitignore)
        if not ok:
            return 1
        bundle = "%s-%s" % (name, version)
        dropped = strip_vendor_cruft(os.path.join(plugins_dir, bundle))
        if dropped:
            print("       stripped %d vendored path(s): %s"
                  % (len(dropped), ", ".join(dropped)))
        bundle_dir = os.path.join(plugins_dir, bundle)
        if not relocate_manifest(bundle_dir):
            sys.stderr.write("%s: packed bundle has no plugin.json\n" % name)
            return 1
        carried = add_licenses(bundle_dir, name, version,
                               bundle_dep_licenses(bundle_dir, dep_map))
        if carried is None:
            return 1
        print("       licences: %s" % ", ".join(carried))
        prune(plugins_dir, name, bundle)
        packed[name] = version

    if args.dry_run:
        return 0

    if retarget(manifest, packed):
        print("[edit] rewrote source paths in %s" % manifest)

    # Keep the marketplace root's licence texts in step with this repo's.
    root_licenses = os.path.join(marketplace, "LICENSES")
    os.makedirs(root_licenses, exist_ok=True)
    for entry in sorted(os.listdir(os.path.join(REPO, "LICENSES"))):
        shutil.copyfile(os.path.join(REPO, "LICENSES", entry),
                        os.path.join(root_licenses, entry))

    if not run(["apm", "pack"], marketplace):
        return 1

    notices = subprocess.run(
        [sys.executable, os.path.join(REPO, "scripts", "gen-notices.py"),
         "--marketplace", marketplace], capture_output=True, text=True)
    sys.stdout.write(notices.stdout)
    if notices.returncode != 0:
        sys.stderr.write(notices.stderr)
        return 1

    print("[done] %d bundle(s) + both marketplace manifests in %s"
          % (len(packed), marketplace))
    return 0


if __name__ == "__main__":
    sys.exit(main())
