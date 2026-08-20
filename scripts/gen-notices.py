#!/usr/bin/env python3
"""Generate THIRD-PARTY-NOTICES.md for the marketplace repo.

Replaces a hand-maintained file that carried its own warning admitting it was
never verified against what actually shipped. Three inputs, per bundle:

  1. Vendored APM dependencies  -- each bundle embeds an enriched apm.lock.yaml
     recording repo_url / resolved_commit / version for every skill packed into
     it. It records no licence, so terms come from the workspace's
     dependency-licenses.yml.
  2. Per-file licence exceptions -- files inside the bundle whose frontmatter
     declares a `license:` or carries obligation-bearing provenance.
  3. Acknowledgements -- every remaining provenance source.

Obligation and credit are kept apart on purpose. Listing an `inspiration-only`
source under "Notices" would imply a licence condition that does not exist;
omitting it entirely would drop credit that is owed as courtesy. So sources whose
terms attach go under Notices, everything else under Acknowledgements.

Usage:
  python scripts/gen-notices.py --repo PATH --marketplace PATH [--check] [--verify]

  --repo    the workspace whose dependency-licenses.yml records the terms
  --check   regenerate to memory and diff against the file on disk; write
            nothing, exit 1 when stale. This is the release gate.
  --verify  re-query each upstream's licence via `gh` and warn on drift from
            dependency-licenses.yml -- how an upstream relicence surfaces.

Exit codes: 0 ok, 1 stale (--check), drift (--verify), or error.
Dependency-free, like pack-marketplace.py: it reads the few keys it needs.
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import provenance as prov  # noqa: E402

import workspace  # noqa: E402


# --- Minimal readers -------------------------------------------------------


def read_license_map(path):
    """Parse dependency-licenses.yml without a YAML dependency.

    Shape is fixed and flat: `key:` at column 0, two-space fields under it, with
    `|` block and `>-` folded scalars for `notice` and `note`.

    A missing file is an empty map, not an error: a workspace with no vendored
    upstreams has nothing to record, and every consumer already handles an
    unrecorded dependency by reporting it.
    """
    if not os.path.isfile(path):
        return {}
    entries, current, field, buffer, indent = {}, None, None, [], 0
    for raw in io.open(path, encoding="utf-8").read().split("\n"):
        if field:  # inside a block scalar
            if raw.strip() and (len(raw) - len(raw.lstrip())) > indent:
                buffer.append(raw.strip() if field == "note" else raw[indent + 2:])
                continue
            entries[current][field] = (" " if field == "note" else "\n").join(buffer).strip()
            field, buffer = None, []
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if not line.startswith(" ") and line.endswith(":"):
            current = line[:-1].strip()
            entries[current] = {}
            continue
        m = re.match(r"^(\s+)(\w+):\s*(.*)$", line)
        if m and current:
            indent, key, value = len(m.group(1)), m.group(2), m.group(3).strip()
            if value in ("|", ">-", ">", "|-"):
                field, buffer = key, []
            else:
                entries[current][key] = value.strip("\"'")
    if field:
        entries[current][field] = (" " if field == "note" else "\n").join(buffer).strip()
    return entries


def read_lock_dependencies(bundle_dir):
    """Every dependency recorded in a packed bundle's apm.lock.yaml."""
    path = os.path.join(bundle_dir, "apm.lock.yaml")
    if not os.path.isfile(path):
        return []
    deps, current, in_deps = [], None, False
    for raw in io.open(path, encoding="utf-8").read().split("\n"):
        if re.match(r"^dependencies:\s*$", raw):
            in_deps = True
            continue
        if in_deps and raw and not raw.startswith((" ", "-", "\t")):
            break
        if not in_deps:
            continue
        if re.match(r"^\s*-\s", raw):
            current = {}
            deps.append(current)
            raw = re.sub(r"^(\s*)-\s", r"\1  ", raw)
        m = re.match(r"^\s+(\w+):\s*(.+?)\s*$", raw)
        if m and current is not None:
            current[m.group(1)] = m.group(2).strip("\"'")
    return [d for d in deps if d.get("repo_url")]


# Hosts whose path *is* the identity rather than a section of a site. An ISBN or
# DOI resolver names one work, so three books behind openlibrary.org are three
# sources and must not collapse into a single row crediting the resolver.
IDENTIFIER_HOSTS = ("openlibrary.org", "doi.org", "dx.doi.org", "search.worldcat.org")


def slug(repo_url):
    """Identity of a source, as used to key dependency-licenses.yml.

    A GitHub URL collapses to `github.com/owner/repo`, which is what the map is
    keyed by. Anything else keeps its own host — a documentation site is a real
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


def canonical(key, licenses):
    """Resolve a slug to the licence map's own key, ignoring case.

    GitHub owner and repo names are case-insensitive, and the two inputs
    disagree about casing: APM's lockfile lowercases `repo_url` (keeping the
    original in `materialization_repo_url`, which not every entry carries),
    while `metadata.provenance` records the upstream URL as written. Without
    folding, one repository arrives under two keys — the provenance row finds
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


def link(key, url=None):
    """Markdown link for a source key, pointing at something that resolves."""
    if key.startswith("github.com/"):
        return "[%s](https://%s)" % (key[len("github.com/"):], key)
    return "[%s](%s)" % (key, url or "https://" + key)


def upstream_path(url):
    """The upstream file a provenance entry points at, for disambiguation."""
    m = re.match(r"https?://github\.com/[^/]+/[^/]+/(?:blob|tree)/[^/]+/(.+)$", url)
    return m.group(1) if m else ""


# --- Gathering -------------------------------------------------------------


def bundle_provenance(bundle_dir):
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
                if record["entries"] or record["declared"]:
                    record["rel"] = os.path.relpath(path, bundle_dir).replace("\\", "/")
                    found.append(record)
    return found


def collect(marketplace):
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


def render(bundles, licenses):
    out = []
    w = out.append
    w("# Third-party notices")
    w("")
    w("<!-- Generated by scripts/gen-notices.py in .llmctl. Do not edit by hand;")
    w("     re-run `apm run gen-notices` (or `apm run release`) instead. -->")
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

    ack = {}   # slug -> set of reasons, across all bundles

    for bundle in bundles:
        notices, exceptions = [], []

        for dep in bundle["deps"]:
            key = canonical(slug(dep["repo_url"]), licenses)
            info = licenses.get(key)
            if not info:
                notices.append((dep.get("name", key), key, "UNRECORDED", "", ""))
                continue
            notices.append((dep.get("name", key), key, info.get("spdx", "?"),
                            info.get("holder", ""), dep.get("resolved_commit", "")[:12]))

        for record in bundle["files"]:
            for entry in record["entries"]:
                fidelity = prov.effective_fidelity(entry)
                key = canonical(slug(entry["url"]), licenses)
                if prov.OBLIGATION.get(fidelity, True):
                    info = licenses.get(key, {})
                    exceptions.append((record["rel"], record["effective"],
                                       entry["license"] or info.get("spdx", "?"),
                                       fidelity, key, info.get("holder", ""),
                                       upstream_path(entry["url"]), entry["url"]))
                else:
                    ack.setdefault(key, (set(), entry["url"]))[0].add(fidelity)

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


# --- Verification ----------------------------------------------------------


def verify(licenses):
    """Re-query each upstream and warn where the API disagrees with the map."""
    drift = 0
    for key, info in sorted(licenses.items()):
        if not key.startswith("github.com/"):
            # A documentation host has no repo to query. Its terms come from the
            # site, which is exactly why the entry carries a `note`.
            print("  %-44s %-14s skipped (not a repository)"
                  % (key, info.get("spdx", "?")))
            continue
        repo = key[len("github.com/"):]
        try:
            got = subprocess.run(["gh", "api", "repos/" + repo,
                                  "--jq", ".license.spdx_id // \"NONE\""],
                                 capture_output=True, text=True, timeout=30)
        except Exception as exc:
            print("  ? %s: could not query (%s)" % (repo, exc))
            continue
        if got.returncode != 0:
            print("  ? %s: query failed" % repo)
            continue
        reported = got.stdout.strip()
        recorded = info.get("spdx", "?")
        if reported in (recorded, "NOASSERTION") or (reported == "NONE" and recorded == "NONE"):
            status = "ok" if reported == recorded else "ok (API says %s; see note)" % reported
            print("  %-44s %-14s %s" % (repo, recorded, status))
        else:
            drift += 1
            print("  %-44s %-14s DRIFT: API now reports %s" % (repo, recorded, reported))
    if drift:
        print("\n%d upstream(s) may have relicensed. Re-read their LICENSE file and "
              "update dependency-licenses.yml." % drift)
    return 1 if drift else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    workspace.add_arguments(parser)
    parser.add_argument("--check", action="store_true",
                        help="fail if the committed file is out of date; write nothing")
    parser.add_argument("--verify", action="store_true",
                        help="re-query upstream licences and report drift")
    args = parser.parse_args()

    ws, marketplace = workspace.resolve(args)
    licenses = read_license_map(os.path.join(ws, "dependency-licenses.yml"))

    if args.verify:
        print("verifying %d recorded upstream licence(s):" % len(licenses))
        return verify(licenses)

    bundles = collect(marketplace)
    if not bundles:
        sys.stderr.write("no packed bundles under %s/plugins - run pack-marketplace.py first\n"
                         % marketplace)
        return 1

    text = render(bundles, licenses)
    target = os.path.join(marketplace, "THIRD-PARTY-NOTICES.md")

    if args.check:
        existing = io.open(target, encoding="utf-8").read() if os.path.isfile(target) else ""
        if existing.replace("\r\n", "\n") != text:
            sys.stderr.write("THIRD-PARTY-NOTICES.md is out of date - run "
                             "`apm run gen-notices`\n")
            return 1
        print("THIRD-PARTY-NOTICES.md is current")
        return 0

    io.open(target, "w", encoding="utf-8", newline="\n").write(text)
    print("[notices] %s (%d bundle(s))" % (target, len(bundles)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
