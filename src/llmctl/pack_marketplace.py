"""Pack every package into a marketplace tree, and make that tree nothing but output.

A plugin host clones the marketplace repo and reads each `packages[].source` path
as committed -- it never runs `apm install` -- so the bundles have to exist there
as files. Two phases, because `apm pack` refuses to write a marketplace manifest
across a `..` boundary:

  1. per package  export packages/<dir> to scratch, stamp the version, install
                  and prove the committed lockfile is what was materialised,
                  `apm pack` into <marketplace>/plugins/<name>-<version>/
  2. marketplace  emit apm.yml from apm.marketplace.yml, copy the other
                  `*.marketplace.*` sources, delete everything that is not
                  expected output, `apm pack`, regenerate the notices

Nothing there is authored: `sync()` deletes whatever the two phases did not
produce, which is what lets a release commit the whole tree with `git add -A`.
See CONTRIBUTING.md#packaging-model.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NamedTuple

import typer

from . import gen_notices, provenance, workspace
from . import versions as versionlib
from .workspace import Log, WorkspaceError

# What a marketplace tree may contain at the top level. Anything else is
# deleted by sync(): the repo holds generated output and nothing authored.
TOP_LEVEL = frozenset(
    {
        ".git",
        ".claude-plugin",
        ".agents",
        "apm.yml",
        "README.md",
        "LICENSE",
        ".gitignore",
        "LICENSES",
        "THIRD-PARTY-NOTICES.md",
        "plugins",
    }
)

# Authored in the workspace, copied verbatim. apm.yml is emitted, not copied.
MARKETPLACE_SOURCES = {
    "README.marketplace.md": "README.md",
    "LICENSE.marketplace": "LICENSE",
    ".gitignore.marketplace": ".gitignore",
}
CATALOGUE = "apm.marketplace.yml"
# What a catalogue entry may declare. `source` and `version` are filled in here;
# the rest of APM's allowed keys are refused so a typo cannot pass unnoticed.
CATALOGUE_KEYS = frozenset({"name", "description", "category"})

WORKTREE_IGNORE = shutil.ignore_patterns(
    *workspace.INSTALL_OUTPUT, "build", ".vscode", "__pycache__"
)

# A vendored upstream skill arrives as whatever its repo happens to contain.
# When the skill's SKILL.md sits at its repo root (e.g. blader/humanizer), APM
# copies the *entire* repo into skills/<name>/ -- CI config, packaging
# manifests, repo-level docs. A plugin host reads none of it.
#
# `.claude-plugin/` is the one that matters beyond disk noise: hosts scan for
# `.claude-plugin/plugin.json` to detect a plugin, so leaving a vendored copy
# inside skills/ ships a plugin manifest nested inside a plugin bundle.
VENDOR_CRUFT_DIRS = (
    ".github",
    ".gitlab",
    ".circleci",
    ".vscode",
    ".idea",
    ".claude-plugin",
    ".codex-plugin",
    ".git",
    "node_modules",
)
VENDOR_CRUFT_FILES = (
    "apm.yml",
    "apm.lock.yaml",
    ".apm-pin",
    ".gitignore",
    ".gitattributes",
    ".editorconfig",
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    "README.md",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
    "SUPPORT.md",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "renovate.json",
)

# Attribution has to travel with the code -- MIT requires the notice to be
# carried, Apache-2.0 the licence text -- and the generated THIRD-PARTY-NOTICES
# depends on these surviving. Never strip them, whatever else matches above.
KEEP_PREFIXES = ("LICENSE", "LICENCE", "NOTICE", "COPYING")


class PackReport(NamedTuple):
    """What a sync did: bundles built, bundles left alone, paths deleted."""

    packed: list[str]
    kept: list[str]
    removed: list[str]
    versions: dict[str, str]


class PackError(Exception):
    pass


def run(args: list[str], cwd: Path | str) -> subprocess.CompletedProcess:
    result = subprocess.run(
        args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        command = " ".join(args)
        raise PackError(
            f"{command} failed in {cwd} (exit {result.returncode})\n{result.stdout}{result.stderr}"
        )
    return result


def pack_json(args: list[str], cwd: Path | str) -> dict:
    """`apm pack --json ...`, parsed. Logs go to stderr, so stdout is the payload."""
    result = subprocess.run(
        ["apm", "pack", "--json", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
        errors="replace",
    )
    try:
        return json.loads(result.stdout)
    except ValueError as exc:
        command = " ".join(args)
        output = (result.stdout + result.stderr)[-600:]
        raise PackError(
            f"apm pack --json {command} produced no JSON in {cwd} "
            f"(exit {result.returncode})\n{output}"
        ) from exc


# --- One package -----------------------------------------------------------


def export_package(ws: Path, directory: str, dest: Path, source: str) -> None:
    """Copy packages/<directory> to `dest` from HEAD or from the worktree."""
    if dest.exists():
        shutil.rmtree(dest)
    if source == "HEAD":
        result = subprocess.run(
            ["git", "archive", "--format=tar", f"HEAD:packages/{directory}"],
            cwd=str(ws),
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise PackError(
                "git archive failed for packages/{}\n{}".format(
                    directory, result.stderr.decode("utf-8", "replace")
                )
            )
        dest.mkdir(parents=True)
        with tarfile.open(fileobj=io.BytesIO(result.stdout)) as archive:
            # `git archive` of this repo's own HEAD, so the members are the
            # committed tree; `data` still refuses anything outside it.
            archive.extractall(dest, filter="data")
    elif source == "worktree":
        shutil.copytree(ws / "packages" / directory, dest, ignore=WORKTREE_IGNORE)
    else:
        raise ValueError(f"source must be HEAD or worktree, not {source!r}")


def stamp_version(manifest: Path, version: str) -> None:
    data = workspace.read_yaml(manifest)
    data["version"] = version
    workspace.write_yaml(manifest, data)


def relocate_manifest(bundle_dir: Path) -> bool:
    """Move the packed plugin.json to where a plugin host looks for it.

    `apm pack` writes plugin.json at the bundle root; Claude Code, Desktop and
    Cowork all reject that layout with "requires .claude-plugin/plugin.json or
    a top-level SKILL.md". `apm install` reads either location, so the manifest
    is moved rather than duplicated.
    """
    root = bundle_dir / "plugin.json"
    nested = bundle_dir / ".claude-plugin"
    if not root.is_file():
        return (nested / "plugin.json").is_file()
    nested.mkdir(exist_ok=True)
    shutil.move(str(root), str(nested / "plugin.json"))
    return True


def write_codex_manifest(bundle_dir: Path, category: str) -> None:
    """Write the Codex sibling of the packed `.claude-plugin/plugin.json`.

    Codex reads `.codex-plugin/plugin.json`; it does not fall back to the
    Claude manifest, and a marketplace entry carrying only a name and a source
    path is deliberately non-installable rather than treated as stand-in
    metadata (openai/codex#28789). Derived from the manifest APM just generated
    rather than from apm.yml a second time, so the two cannot end up describing
    the same bundle differently.
    """
    with (bundle_dir / ".claude-plugin" / "plugin.json").open(encoding="utf-8") as handle:
        base = json.load(handle)

    manifest = {}
    for key in ("name", "version", "description", "author", "license"):
        if key in base:
            manifest[key] = base[key]

    capabilities = []
    for directory, capability in (
        ("skills", "Skills"),
        ("agents", "Agents"),
        ("commands", "Commands"),
        ("instructions", "Instructions"),
    ):
        if (bundle_dir / directory).is_dir():
            capabilities.append(capability)
    # Both are supplements to Codex's default discovery, not replacements, and
    # a path that does not resolve is a validation error -- so declare each
    # only when the bundle actually has it.
    if (bundle_dir / "skills").is_dir():
        manifest["skills"] = "./skills/"
    if (bundle_dir / ".mcp.json").is_file():
        manifest["mcpServers"] = "./.mcp.json"
        capabilities.append("MCP")

    author = base.get("author") or {}
    manifest["interface"] = {
        "displayName": base.get("name", ""),
        # One authored description, so the subtitle and the details page say
        # the same thing rather than one of them being invented here.
        "shortDescription": base.get("description", ""),
        "longDescription": base.get("description", ""),
        "developerName": author.get("name", "") if isinstance(author, dict) else author,
        "category": category,
        "capabilities": capabilities,
    }

    target = bundle_dir / ".codex-plugin"
    target.mkdir(exist_ok=True)
    with Path(target / "plugin.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
        handle.write("\n")


def strip_vendor_cruft(bundle_dir: Path) -> list[str]:
    """Drop upstream repo scaffolding from vendored skills in a packed bundle.

    Scoped to `skills/<name>/` only: the bundle root holds the plugin's own
    manifest and the lockfile the notices are generated from.

    Deliberately a denylist of known scaffolding rather than an allowlist of
    known content: a skill may legitimately ship `scripts/`, `references/` or
    anything else its SKILL.md links to, and silently dropping one breaks the
    skill at runtime with no error. A few stale KB is cheaper.
    """
    skills_dir = bundle_dir / "skills"
    if not skills_dir.is_dir():
        return []
    dropped = []
    for skill in sorted(skills_dir.iterdir()):
        if not skill.is_dir():
            continue
        for entry in sorted(skill.iterdir()):
            if entry.name.upper().startswith(KEEP_PREFIXES):
                continue
            if entry.is_dir() and entry.name in VENDOR_CRUFT_DIRS:
                shutil.rmtree(entry, ignore_errors=True)
            elif entry.is_file() and entry.name in VENDOR_CRUFT_FILES:
                entry.unlink()
            else:
                continue
            dropped.append(f"{skill.name}/{entry.name}")
    return dropped


def licenses_needed(bundle_dir: Path, dep_licenses: set) -> list[str]:
    """SPDX ids whose full text has to ship inside this bundle.

    Three sources, because a bundle mixes three kinds of content: the repo
    defaults covering the authored files, any per-file `license:` override, and
    the licence of every vendored upstream skill.
    """
    needed = {provenance.DEFAULT_CONTENT, provenance.DEFAULT_CODE}
    for sub in ("agents", "skills", "instructions", "commands"):
        top = bundle_dir / sub
        if not top.is_dir():
            continue
        for dirpath, _, filenames in os.walk(top):
            for name in sorted(filenames):
                if name.endswith(".md"):
                    declared = provenance.parse(Path(dirpath) / name).declared
                    if declared:
                        needed.add(declared)
    for dep in dep_licenses:
        if dep:
            needed.add(dep)
    return sorted(n for n in needed if n not in ("NONE", "NOASSERTION"))


def add_licenses(
    ws: Path, bundle_dir: Path, name: str, version: str, dep_licenses: set
) -> list[str]:
    """Put the licence files and a minimal manifest into a packed bundle.

    `apm pack` copies neither, and both matter downstream:

      LICENSE + LICENSES/  attribution has to travel with the content. MIT wants
                           its notice carried, Apache-2.0 the licence and NOTICE,
                           CC-BY-SA-4.0 the licence and a change indication.
      apm.yml              `apm pack --check-versions` reads each bundle's version
                           from its apm.yml; with none it reports `no_apm_yml` and
                           fails the gate. Deliberately name/version/license only
                           -- a `dependencies:` block here would invite a
                           re-resolve at install time.
    """
    root_license = ws / "LICENSE"
    if not root_license.is_file():
        raise PackError(f"{name}: no LICENSE at the root of {ws}")
    shutil.copyfile(root_license, bundle_dir / "LICENSE")

    target = bundle_dir / "LICENSES"
    target.mkdir(exist_ok=True)
    carried = []
    for spdx in licenses_needed(bundle_dir, dep_licenses):
        source = ws / "LICENSES" / (f"{spdx}.txt")
        if not source.is_file():
            raise PackError(f"{name}: no licence text for {spdx} in LICENSES/")
        shutil.copyfile(source, target / (f"{spdx}.txt"))
        carried.append(spdx)

    # The expression names every licence in the bundle, not just the repo
    # defaults: a bundle carrying an Apache-2.0 file or an Apache-2.0 vendored
    # skill has to say so, or the SBOM understates what a consumer takes on.
    with Path(bundle_dir / "apm.yml").open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(
            "# Generated by llmctl-pack-marketplace in .llmctl - do not edit.\n"
            "# Present so `apm pack --check-versions` can read this bundle's version.\n"
            "name: {}\nversion: {}\nlicense: {}\n".format(name, version, " AND ".join(carried))
        )
    return carried


def bundle_dep_licenses(bundle_dir: Path, dep_map: dict) -> set:
    """SPDX id of every upstream vendored into this bundle, via its lockfile."""
    found = set()
    for dep in gen_notices.read_lock_dependencies(bundle_dir):
        key = gen_notices.canonical(gen_notices.slug(dep["repo_url"]), dep_map)
        info = dep_map.get(key)
        if info:
            found.add(info.get("spdx"))
        else:
            sys.stderr.write(
                "{}: no licence recorded for {} - add it to dependency-licenses.yml\n".format(
                    bundle_dir.name, dep["repo_url"]
                )
            )
    return found


def install_reproducibly(export: Path, name: str) -> None:
    """Materialise a scratch export's dependencies and prove they are the
    committed ones.

    Not `apm install --frozen`, for two reasons. It checks the wrong thing: a
    frozen install only verifies that every dependency in apm.yml *appears* in
    the lockfile, keyed by repo and subpath -- never at which commit -- so a pin
    moved without a lockfile refresh passes it and packs the old code. And it
    still cannot restore a manifestless repo-root package (blader/humanizer)
    from a cold cache: verified against APM 0.28.0 and again on 0.31.0.

    What makes the build reproducible is this: every pin is a full commit SHA,
    so a plain install cannot resolve anything new, and the lockfile's resolved
    commits are compared before and after. If installing moved any of them, the
    pack stops -- that is a lockfile someone has to refresh deliberately,
    through update.py, not something a release quietly absorbs.
    """
    try:
        pins = workspace.pins_of(workspace.read_yaml(export / "apm.yml"))
    except WorkspaceError as exc:
        raise PackError(f"{name}: {exc}") from exc
    floating = sorted(spec for spec in pins.values() if not workspace.SHA_RE.match(spec))
    if floating:
        raise PackError(
            "{}: every dependency must be pinned to a full commit SHA "
            "before it can be packed reproducibly; found {}".format(name, ", ".join(floating))
        )

    before = workspace.locked_of(workspace.read_lock(export / "apm.lock.yaml") or {})
    run(["apm", "install", "--target", "claude"], export)
    after = workspace.locked_of(workspace.read_lock(export / "apm.lock.yaml") or {})

    moved = workspace.diff_pins(before, after)
    if moved:
        raise PackError(
            "{}: installing moved what the committed lockfile records "
            "({}). Refresh packages/*/apm.lock.yaml deliberately -- a "
            "release never absorbs an unreviewed upstream".format(name, "; ".join(moved))
        )


def audit_export(export: Path, name: str, log: Log) -> None:
    """Scan the materialised upstream content before it is packed.

    A pin fixes which content arrives, not what it does, and this content ships
    to plugin hosts. `apm audit --ci` reads the deployed files for critical
    hidden Unicode -- tag characters and bidi overrides, invisible to a reviewer
    and not to a tokenizer -- and for drift from the lockfile's hashes.
    """
    result = subprocess.run(
        ["apm", "audit", "--ci", "--no-policy"],
        cwd=str(export),
        capture_output=True,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        findings = [
            line.strip()
            for line in result.stdout.split("\n")
            if line.strip().startswith(("[x]", "[!]"))
        ]
        raise PackError(
            "{}: apm audit rejected the materialised content:\n{}".format(
                name, "\n".join(findings[:6]) or result.stdout[-500:]
            )
        )
    log("       audit: clean")


@dataclass(frozen=True)
class Packer:
    """The parts of a pack run that are the same for every package."""

    ws: Path
    plugins_dir: Path
    dep_map: dict
    scratch: Path
    source: str
    log: Callable = print

    def pack(self, package: workspace.Package, version: str, category: str) -> Path:
        """Export, stamp, install, audit, pack and finish one bundle."""
        export = self.scratch / package.directory
        export_package(self.ws, package.directory, export, self.source)
        stamp_version(export / "apm.yml", version)
        if not (export / "apm.lock.yaml").is_file():
            raise PackError(
                f"{package.name}: packages/{package.directory}/apm.lock.yaml is "
                f"missing; commit one "
                "(update.py produces it) before packing"
            )

        bundle_dir = self.plugins_dir / (f"{package.name}-{version}")
        if bundle_dir.exists():
            shutil.rmtree(bundle_dir)
        self.plugins_dir.mkdir(parents=True, exist_ok=True)

        install_reproducibly(export, package.name)
        audit_export(export, package.name, self.log)
        run(["apm", "pack", "-o", str(self.plugins_dir)], export)
        shutil.rmtree(export, ignore_errors=True)

        if not bundle_dir.is_dir():
            raise PackError(f"{package.name}: apm pack did not produce {bundle_dir}")
        dropped = strip_vendor_cruft(bundle_dir)
        if dropped:
            paths = ", ".join(dropped)
            self.log(f"       stripped {len(dropped)} vendored path(s): {paths}")
        if not relocate_manifest(bundle_dir):
            raise PackError(f"{package.name}: packed bundle has no plugin.json")
        write_codex_manifest(bundle_dir, category)
        carried = add_licenses(
            self.ws,
            bundle_dir,
            package.name,
            version,
            bundle_dep_licenses(bundle_dir, self.dep_map),
        )
        self.log("       licences: {}".format(", ".join(carried)))
        return bundle_dir


# --- The marketplace tree --------------------------------------------------


def read_catalogue(ws: Path) -> Any:
    path = ws / CATALOGUE
    if not path.is_file():
        raise PackError(f"no {CATALOGUE} in {ws} -- the marketplace catalogue is authored there")
    data = workspace.read_yaml(path)
    entries = ((data or {}).get("marketplace") or {}).get("packages") or []
    for entry in entries:
        extra = set(entry.keys()) - CATALOGUE_KEYS
        if extra:
            raise PackError(
                "{}: entry {!r} carries {}; only {} are authored here "
                "(source and version are filled in by the packer)".format(
                    CATALOGUE,
                    entry.get("name"),
                    ", ".join(sorted(extra)),
                    ", ".join(sorted(CATALOGUE_KEYS)),
                )
            )
        for key in ("name", "category"):
            if not entry.get(key):
                raise PackError(f"{CATALOGUE}: an entry is missing `{key}` -- Codex requires it")
    return data


def emit_catalogue(ws: Path, marketplace: Path, versions: dict[str, str]) -> None:
    """Write <marketplace>/apm.yml from apm.marketplace.yml, filling source+version."""
    data = read_catalogue(ws)
    for entry in data["marketplace"]["packages"]:
        version = versions[entry["name"]]
        # Inserted right after `name` so the generated file reads like the
        # hand-written one it replaces.
        entry.insert(1, "source", "./plugins/{}-{}".format(entry["name"], version))
        entry.insert(2, "version", version)
    header = (
        f"# Generated by llmctl-pack-marketplace in .llmctl from {CATALOGUE} in the\n"
        "# workspace - do not edit here. Every file in this repository is generated\n"
        "# output; the sources live in the steering repository.\n"
    )
    workspace.write_yaml(marketplace / "apm.yml", data, header=header)


def copy_marketplace_files(ws: Path, marketplace: Path) -> None:
    for source, target in MARKETPLACE_SOURCES.items():
        path = ws / source
        if not path.is_file():
            raise PackError(
                f"no {source} in {ws} -- every marketplace file is authored in the workspace"
            )
        shutil.copyfile(path, marketplace / target)
    licenses = marketplace / "LICENSES"
    if licenses.exists():
        shutil.rmtree(licenses)
    shutil.copytree(ws / "LICENSES", licenses)


def sync(marketplace: Path, expected_bundles: set[str]) -> list[str]:
    """Delete whatever the marketplace holds that is not expected output."""
    removed = []
    for entry in sorted(marketplace.iterdir()):
        if entry.name not in TOP_LEVEL:
            shutil.rmtree(entry) if entry.is_dir() else entry.unlink()
            removed.append(entry.name)
    plugins = marketplace / "plugins"
    if plugins.is_dir():
        for entry in sorted(plugins.iterdir()):
            if entry.name not in expected_bundles:
                shutil.rmtree(entry) if entry.is_dir() else entry.unlink()
                removed.append(f"plugins/{entry.name}")
    return removed


def pack_all(
    ws: Path,
    marketplace: Path,
    versions: dict[str, str],
    repack: set[str],
    *,
    scratch: Path,
    source: str,
    log: Log = print,
) -> PackReport:
    """Bring `marketplace` to the state `versions` describes.

    `versions` maps every package name to the version its bundle must carry;
    `repack` names the ones to pack afresh. A package outside `repack` whose
    bundle is missing is packed anyway -- that is what heals a marketplace whose
    push failed after the workspace was tagged.
    """
    ws, marketplace, scratch = Path(ws), Path(marketplace), Path(scratch)
    packages = workspace.packages(ws)
    entries = {e["name"]: e for e in read_catalogue(ws)["marketplace"]["packages"]}

    names = {p.name for p in packages}
    orphaned = set(entries) - names
    if orphaned:
        raise PackError(
            "{} still lists {}, which packages/ no longer holds -- drop the entry".format(
                CATALOGUE, ", ".join(sorted(orphaned))
            )
        )
    unlisted = names - set(entries)
    if unlisted:
        raise PackError(
            "{} is not listed in {} -- add it or remove the package".format(
                ", ".join(sorted(unlisted)), CATALOGUE
            )
        )
    missing = names - set(versions)
    if missing:
        raise PackError("no version for {}".format(", ".join(sorted(missing))))

    # Workspace data, not tooling data: a private repo declares its own
    # upstreams, and holds none of this code. Absent means none.
    packer = Packer(
        ws,
        marketplace / "plugins",
        gen_notices.read_license_map(ws / "dependency-licenses.yml"),
        scratch,
        source,
        log,
    )
    marketplace.mkdir(parents=True, exist_ok=True)

    packed, kept = [], []
    for package in packages:
        version = versions[package.name]
        bundle = f"{package.name}-{version}"
        if package.name not in repack and (packer.plugins_dir / bundle).is_dir():
            kept.append(bundle)
            continue
        log(f"[pack] {package.name} {version}")
        packer.pack(package, version, entries[package.name]["category"])
        packed.append(bundle)

    emit_catalogue(ws, marketplace, versions)
    copy_marketplace_files(ws, marketplace)
    removed = sync(marketplace, {f"{n}-{v}" for n, v in versions.items()})
    for entry in removed:
        log(f"[sync] removed {entry}")
    run(["apm", "pack"], marketplace)
    gen_notices.write(ws, marketplace)
    log(
        f"[done] {len(packed)} bundle(s) packed, {len(kept)} kept, both "
        f"marketplace manifests in {marketplace}"
    )
    return PackReport(packed, kept, removed, versions)


def version_map(ws: Path, plans: Sequence[versionlib.Plan]) -> dict[str, str]:
    """Every package's version after a release, whether or not it is in it.

    The marketplace holds one bundle per package and a catalogue naming all of
    them, so a release of one package still has to say what version the other
    four are at: the tag each already carries. Derived from every package rather
    than from the plan, because a plan narrowed by --package knows nothing about
    the rest.
    """
    planned = {p.name: p.next for p in plans}
    versions = {}
    for package in workspace.packages(ws):
        if package.name in planned:
            versions[package.name] = planned[package.name]
            continue
        version = versionlib.version_of(versionlib.last_tag(ws, package.name))
        if not version:
            raise PackError(
                f"{package.name} has never been released and is not part of this "
                "release, so its bundle has no version; seed a tag "
                "first"
            )
        versions[package.name] = version
    return versions


def main(
    repo: Path = workspace.REPO_OPTION,
    marketplace: Path = workspace.MARKETPLACE_OPTION,
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Print what would be packed; touch nothing."
    ),
    all_: bool = typer.Option(
        False,
        "--all",
        help="Re-pack every package, not only the ones with commits since their tag.",
    ),
    package: list[str] = typer.Option(
        [], "--package", help="Limit to these packages (implies re-packing them)."
    ),
) -> None:
    """Regenerate a marketplace tree from this workspace, in place."""
    ws, marketplace = repo.resolve(), marketplace.resolve()
    if not (marketplace / ".git").exists():
        sys.stderr.write(f"{marketplace} is not a git checkout -- pass the marketplace clone\n")
        raise typer.Exit(1)
    try:
        plans, _ = versionlib.plan(ws, only=(), force=False, fetch=True)
        versions = version_map(ws, plans)
        repack = set(versions) if all_ else {p.name for p in plans}
        if package:
            repack = {p.name for p in workspace.select(ws, package)}
        if dry_run:
            for name in sorted(versions):
                print(
                    "[{}] {} {}".format("pack" if name in repack else "keep", name, versions[name])
                )
            print("\n[dry-run] no files written")
            return
        pack_all(ws, marketplace, versions, repack, scratch=ws / "build", source="worktree")
    except (PackError, WorkspaceError) as exc:
        raise workspace.die(exc) from None


def cli() -> None:
    typer.run(main)
