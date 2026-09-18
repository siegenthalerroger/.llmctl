#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "ruamel.yaml==0.19.1",
#   "typer==0.27.2",
#   "rich==15.0.0",
#   "httpx==0.28.1",
#   "python-frontmatter==1.3.0",
# ]
# [tool.uv]
# exclude-newer = "2026-09-18T00:00:00Z"
# ///
"""Generate THIRD-PARTY-NOTICES.md for the marketplace repo.

Three inputs per bundle: the vendored APM dependencies its embedded apm.lock.yaml
records, the per-file licence exceptions inside it, and every remaining provenance
source. Obligation and credit are kept apart -- sources whose terms attach go under
Notices, the rest under Acknowledgements, because listing an `inspiration-only`
source as a notice would imply a condition that does not exist.

pack_marketplace.py imports `write()`; the `pack` gate fails on any `UNRECORDED`
upstream. See CONTRIBUTING.md#licensing.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import NamedTuple

import typer
from ruamel.yaml import YAML

import github as githublib
import provenance as prov
import workspace
from workspace import Log

UNRECORDED = "UNRECORDED"


# --- Readers ---------------------------------------------------------------


def read_license_map(path: Path) -> dict:
    """dependency-licenses.yml as {source key: {spdx, holder, license_url, ...}}.

    A missing file is an empty map, not an error: a workspace with no vendored
    upstreams has nothing to record, and every consumer already handles an
    unrecorded dependency by reporting it.
    """
    path = Path(path)
    if not path.is_file():
        return {}
    with open(path, encoding="utf-8") as handle:
        data = YAML(typ="safe").load(handle) or {}
    entries = {}
    for key, info in data.items():
        info = dict(info or {})
        for field in ("notice", "note"):
            if isinstance(info.get(field), str):
                info[field] = info[field].strip()
        entries[str(key)] = info
    return entries


def read_lock_dependencies(bundle_dir: str | Path) -> list[dict]:
    """Every dependency recorded in a packed bundle's apm.lock.yaml."""
    lock = workspace.read_lock(Path(bundle_dir) / "apm.lock.yaml")
    return [dict(d) for d in (lock or {}).get("dependencies") or [] if d.get("repo_url")]


# Hosts whose path *is* the identity rather than a section of a site. An ISBN or
# DOI resolver names one work, so three books behind openlibrary.org are three
# sources and must not collapse into a single row crediting the resolver.
IDENTIFIER_HOSTS = ("openlibrary.org", "doi.org", "dx.doi.org", "search.worldcat.org")


def slug(repo_url: str) -> str:
    """Identity of a source, as used to key dependency-licenses.yml.

    A GitHub URL collapses to `github.com/owner/repo`, which is what the map is
    keyed by. Anything else keeps its own host -- a documentation site is a real
    source, and rewriting `helm.sh/docs` into a github.com path would invent a
    repository that does not exist. Identifier resolvers are the exception: the
    host alone names a catalogue, not a source.
    """
    bare = re.sub(r"^https?://", "", repo_url).rstrip("/")
    bare = re.sub(r"\.git$", "", bare)
    parts = bare.split("/")
    if parts[0] == "github.com":
        return "/".join(parts[:3])
    if "." not in parts[0]:            # a bare `owner/repo` from a lockfile
        return "/".join(["github.com"] + parts[:2])
    if parts[0] in IDENTIFIER_HOSTS:
        return bare                     # host + identifier, one key per work
    return parts[0]                     # a documentation host


def canonical(key: str, licenses: dict) -> str:
    """Resolve a slug to the licence map's own key, ignoring case.

    GitHub owner and repo names are case-insensitive, and the two inputs
    disagree about casing: APM's lockfile lowercases `repo_url` (keeping the
    original in `materialization_repo_url`, which not every entry carries),
    while `metadata.provenance` records the upstream URL as written. Without
    folding, one repository arrives under two keys -- the provenance row finds
    its licence and the lockfile row ships `UNRECORDED` beside it, for a
    dependency whose terms are in fact on file. Folding here rather than
    lowercasing the map keeps the upstream's real casing in the output.
    """
    if key in licenses:
        return key
    folded = key.lower()
    for candidate in licenses:
        if candidate.lower() == folded:
            return candidate
    return key


def link(key: str, url: str | None = None) -> str:
    """Markdown link for a source key, pointing at something that resolves."""
    if key.startswith("github.com/"):
        return "[%s](https://%s)" % (key[len("github.com/"):], key)
    return "[%s](%s)" % (key, url or "https://" + key)


def upstream_path(url: str) -> str:
    """The upstream file a provenance entry points at, for disambiguation."""
    m = re.match(r"https?://github\.com/[^/]+/[^/]+/(?:blob|tree)/[^/]+/(.+)$", url)
    return m.group(1) if m else ""


# --- Gathering -------------------------------------------------------------


class BundleFile(NamedTuple):
    """One file inside a packed bundle, named as the bundle sees it."""

    rel: str
    record: prov.Record


def bundle_provenance(bundle_dir: str) -> list[BundleFile]:
    """Provenance carried by the files inside a packed bundle."""
    found = []
    for sub in ("agents", "skills", "instructions", "commands"):
        top = os.path.join(bundle_dir, sub)
        if not os.path.isdir(top):
            continue
        for dirpath, dirnames, filenames in os.walk(top):
            dirnames.sort()
            for name in sorted(filenames):
                if not name.endswith(".md"):
                    continue
                path = os.path.join(dirpath, name)
                record = prov.parse(path)
                if record.entries or record.declared:
                    rel = os.path.relpath(path, bundle_dir).replace("\\", "/")
                    found.append(BundleFile(rel, record))
    return found


def collect(marketplace: str | Path) -> list[dict]:
    plugins = os.path.join(marketplace, "plugins")
    if not os.path.isdir(plugins):
        return []
    bundles = []
    for entry in sorted(os.listdir(plugins)):
        path = os.path.join(plugins, entry)
        if os.path.isdir(path):
            bundles.append({
                "name": entry,
                "dir": path,
                "deps": read_lock_dependencies(path),
                "files": bundle_provenance(path),
            })
    return bundles


# --- Rendering -------------------------------------------------------------


def render(bundles: list[dict], licenses: dict) -> str:
    out = []
    w = out.append
    w("# Third-party notices")
    w("")
    w("<!-- Generated by scripts/gen_notices.py in .llmctl. Do not edit by hand;")
    w("     re-run `apm run gen-notices` (or a release) instead. -->")
    w("")
    w("Plugin bundles here vendor skills authored elsewhere, and adapt content from "
      "upstream sources. `apm pack` copies skill files only — it does not carry "
      "upstream `LICENSE` text — so the obligations are collected here and the "
      "licence texts ship in each bundle's `LICENSES/` directory.")
    w("")
    w("**Notices** lists sources whose terms attach to what we redistribute. "
      "**Acknowledgements** credits sources that shaped this work without imposing "
      "a condition — being listed there is not a licence claim.")
    w("")
    w("Each bundle's `apm.lock.yaml` records the upstream `repo_url`, the resolved "
      "commit, and a SHA-256 per file, and is the authoritative record of what that "
      "bundle actually contains.")
    w("")

    ack = {}   # slug -> (set of reasons, url), across all bundles

    for bundle in bundles:
        notices, exceptions = [], []

        for dep in bundle["deps"]:
            key = canonical(slug(dep["repo_url"]), licenses)
            info = licenses.get(key)
            if not info:
                notices.append((dep.get("name", key), key, UNRECORDED, "", ""))
                continue
            notices.append((dep.get("name", key), key, info.get("spdx", "?"),
                            info.get("holder", ""), str(dep.get("resolved_commit", ""))[:12]))

        for rel, record in bundle["files"]:
            for entry in record.entries:
                fidelity = prov.effective_fidelity(entry)
                key = canonical(slug(entry.url), licenses)
                if prov.OBLIGATION.get(fidelity, True):
                    info = licenses.get(key, {})
                    exceptions.append((rel, record.effective,
                                       entry.license or info.get("spdx", "?"),
                                       fidelity, key, info.get("holder", ""),
                                       upstream_path(entry.url), entry.url))
                else:
                    ack.setdefault(key, (set(), entry.url))[0].add(fidelity)

        if not notices and not exceptions:
            continue

        w("## %s" % bundle["name"])
        w("")
        if notices:
            w("### Vendored dependencies")
            w("")
            w("| Skill | Upstream | Licence | Copyright | Commit |")
            w("| --- | --- | --- | --- | --- |")
            for name, key, spdx, holder, commit in sorted(notices):
                w("| `%s` | %s | %s | %s | `%s` |"
                  % (name, link(key), spdx, holder or "—", commit or "—"))
            w("")
        if exceptions:
            w("### Adapted content")
            w("")
            w("| File | Licensed as | Upstream | Upstream licence | Copyright |")
            w("| --- | --- | --- | --- | --- |")
            for rel, effective, spdx, fidelity, key, holder, path, url in sorted(exceptions):
                source = "%s — [`%s`](%s)" % (link(key), path, url) if path else link(key, url)
                w("| `%s` | %s | %s | %s (%s) | %s |"
                  % (rel, effective, source, spdx, fidelity, holder or "—"))
            w("")
            w("Each file above is a **modification** of its upstream. Where the "
              "upstream is Apache-2.0 or CC-BY-SA-4.0, this line is the statement of "
              "changes those licences require.")
            w("")

    # NOTICE files must be reproduced verbatim (Apache-2.0 section 4d).
    carried = {canonical(slug(d["repo_url"]), licenses) for b in bundles for d in b["deps"]}
    notice_texts = [(k, licenses[k]["notice"]) for k in sorted(carried)
                    if licenses.get(k, {}).get("notice")]
    if notice_texts:
        w("## NOTICE files")
        w("")
        w("Apache-2.0 section 4(d) requires these to travel with any redistribution.")
        w("")
        for key, text in notice_texts:
            w("**%s**" % key.replace("github.com/", ""))
            w("")
            w("```text")
            for line in text.split("\n"):
                w(line)
            w("```")
            w("")

    if ack:
        w("## Acknowledgements")
        w("")
        w("Sources that shaped this work without imposing a condition — an idea, a "
          "structure, or a specification cited but not reproduced. Listed as credit, "
          "not as a licence claim.")
        w("")
        w("| Source | Attribution | Licence | How it was used |")
        w("| --- | --- | --- | --- |")
        for key in sorted(ack):
            fidelities, url = ack[key]
            info = licenses.get(key, {})
            spdx = info.get("spdx")
            # Attribution carries the identity, which for a source keyed by an
            # ISBN or DOI is the only human-readable thing in the row.
            w("| %s | %s | %s | %s |"
              % (link(key, url),
                 info.get("holder", "") or "—",
                 "no licence" if spdx == "NONE" else (spdx or "not recorded"),
                 ", ".join(sorted(fidelities))))
        w("")

    w("## Licence texts")
    w("")
    w("Full texts ship in each bundle's `LICENSES/` directory and at the repository "
      "root. MIT requires its copyright and permission notice to accompany "
      "redistribution; Apache-2.0 additionally requires the licence, any NOTICE "
      "file, and a statement of changes; CC-BY-SA-4.0 requires attribution, a "
      "change indication, and that adaptations carry the same licence.")
    w("")
    return "\n".join(out)


def render_for(ws: str | Path, marketplace: str | Path) -> str:
    """The notices text for `marketplace`, from `ws`'s licence map."""
    licenses = read_license_map(Path(ws) / "dependency-licenses.yml")
    bundles = collect(marketplace)
    if not bundles:
        raise RuntimeError("no packed bundles under %s/plugins" % marketplace)
    return render(bundles, licenses)


def write(ws: str | Path, marketplace: str | Path) -> Path:
    target = Path(marketplace) / "THIRD-PARTY-NOTICES.md"
    with open(target, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(render_for(ws, marketplace))
    return target


def unrecorded(text: str) -> list[str]:
    """Upstream keys the notices could not find a licence for."""
    return sorted({m.group(1) for m in re.finditer(
        r"\| `[^`]*` \| \[([^\]]+)\]\([^)]*\) \| %s \|" % UNRECORDED, text)})


# --- Verification ----------------------------------------------------------


class Checked(NamedTuple):
    """One upstream's recorded licence against what its host reports today."""

    key: str
    recorded: str
    reported: str
    status: str


def relicensing(licenses: dict, gh: githublib.GitHub) -> list[Checked]:
    """Re-query each upstream's licence and say where the API disagrees.

    How an upstream relicence surfaces. The API is not authoritative -- it
    reports NOASSERTION for a LICENSE it cannot classify -- so `drift` means
    "re-read their LICENSE", not "the record is wrong".
    """
    rows = []
    for key, info in sorted(licenses.items()):
        recorded = info.get("spdx", "?")
        if not key.startswith("github.com/"):
            # A documentation host has no repo to query. Its terms come from the
            # site, which is exactly why the entry carries a `note`.
            rows.append(Checked(key, recorded, "", "not a repository"))
            continue
        owner, _, repo = key[len("github.com/"):].partition("/")
        try:
            reported = gh.repo_license(owner, repo)
        except githublib.ApiError as exc:
            rows.append(Checked(key, recorded, "", "could not query (%s)" % exc))
            continue
        if reported == recorded:
            rows.append(Checked(key, recorded, reported, "ok"))
        elif reported == "NOASSERTION":
            rows.append(Checked(key, recorded, reported,
                                "ok (API cannot classify it; see note)"))
        else:
            rows.append(Checked(key, recorded, reported, "drift"))
    return rows


def verify(licenses: dict, gh: githublib.GitHub, log: Log = print) -> int:
    """Print every upstream's licence check; exit code counts the drift."""
    rows = relicensing(licenses, gh)
    for row in rows:
        log("  %-44s %-14s %s" % (row.key, row.recorded, row.status))
    drift = [row for row in rows if row.status == "drift"]
    if drift:
        log("\n%d upstream(s) may have relicensed. Re-read their LICENSE file and "
            "update dependency-licenses.yml." % len(drift))
    return 1 if drift else 0


def main(repo: Path = workspace.REPO_OPTION,
         marketplace: Path = workspace.MARKETPLACE_OPTION,
         check: bool = typer.Option(False, "--check",
                                    help="Regenerate to memory and diff against the file on "
                                         "disk; write nothing, exit 1 when stale."),
         verify_: bool = typer.Option(False, "--verify",
                                      help="Re-query each upstream's licence via the GitHub API "
                                           "and warn on drift from dependency-licenses.yml."),
         github_token: str = typer.Option("", "--github-token",
                                          help="Overrides GITHUB_TOKEN / GH_TOKEN.")) -> None:
    """Regenerate the marketplace's third-party notices from what each bundle carries."""
    ws, marketplace = repo.resolve(), marketplace.resolve()
    if verify_:
        licenses = read_license_map(ws / "dependency-licenses.yml")
        print("verifying %d recorded upstream licence(s):" % len(licenses))
        raise typer.Exit(verify(licenses, githublib.GitHub(githublib.token(github_token))))

    try:
        text = render_for(ws, marketplace)
    except RuntimeError as exc:
        sys.stderr.write("%s - run pack_marketplace.py first\n" % exc)
        raise typer.Exit(1)
    target = marketplace / "THIRD-PARTY-NOTICES.md"

    if check:
        existing = target.read_text(encoding="utf-8") if target.is_file() else ""
        if existing.replace("\r\n", "\n") != text:
            sys.stderr.write("THIRD-PARTY-NOTICES.md is out of date - run "
                             "`apm run gen-notices`\n")
            raise typer.Exit(1)
        print("THIRD-PARTY-NOTICES.md is current")
        return

    with open(target, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    missing = unrecorded(text)
    if missing:
        sys.stderr.write("no licence recorded for: %s - add them to "
                         "dependency-licenses.yml\n" % ", ".join(missing))
    print("[notices] %s (%d bundle(s))" % (target, len(collect(marketplace))))


if __name__ == "__main__":
    typer.run(main)
