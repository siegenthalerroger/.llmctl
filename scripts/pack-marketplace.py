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
import os
import re
import shutil
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACKAGES = os.path.join(REPO, "packages")

# `apm install` materialises dependencies and deploys them next to the package.
# None of it is authored content, so it is removed after packing to keep the
# working tree clean — the bundle carries its own enriched apm.lock.yaml.
TRANSIENT = (".claude", ".agents", ".github/instructions", "apm_modules",
             ".mcp.json", ".vscode/mcp.json", "apm.lock.yaml", "build")


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
        if not relocate_manifest(os.path.join(plugins_dir, bundle)):
            sys.stderr.write("%s: packed bundle has no plugin.json\n" % name)
            return 1
        prune(plugins_dir, name, bundle)
        packed[name] = version

    if args.dry_run:
        return 0

    if retarget(manifest, packed):
        print("[edit] rewrote source paths in %s" % manifest)
    if not run(["apm", "pack"], marketplace):
        return 1
    print("[done] %d bundle(s) + both marketplace manifests in %s"
          % (len(packed), marketplace))
    return 0


if __name__ == "__main__":
    sys.exit(main())
