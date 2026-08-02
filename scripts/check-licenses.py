#!/usr/bin/env python3
"""Check that every file's licence can carry the upstream terms it inherits.

The repository licence covers what is genuinely original (`*.md` CC-BY-SA-4.0,
everything else MIT; see LICENSE). Anything beyond an idea-level borrowing carries
its upstream's terms with it, so the per-file provenance decides the per-file
licence — not the other way round.

For each provenance entry this asks two questions:

  1. Does the fidelity mean expression was copied? (`partly-derived` and
     `largely-derived` do; `inspiration-only` and `structural-echo` do not.)
  2. If so, can this file's effective licence satisfy that upstream's licence?

A `NONE` upstream — no LICENSE file, hence no grant of rights — passes only at a
fidelity that copies nothing.

Usage:
  python scripts/check-licenses.py [--json] [--root PATH]

Exit codes: 0 clean, 1 errors found.
Dependency-free; the provenance parse is shared with gen-notices.py via
scripts/provenance.py so the two cannot disagree about what a file claims.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import provenance as prov  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def check_file(record):
    """Return (errors, warnings) for one parsed file."""
    errors, warnings = [], []
    rel = os.path.relpath(record["path"], REPO).replace("\\", "/")

    for problem in record["malformed"]:
        errors.append((rel, problem + " - a provenance block that parses to nothing "
                               "stops being tracked silently"))

    declared = record["declared"]
    effective = record["effective"]
    if declared and declared not in prov.KNOWN_LICENSES:
        errors.append((rel, "declares unknown licence `%s`; known: %s"
                       % (declared, ", ".join(prov.KNOWN_LICENSES))))

    for entry in record["entries"]:
        fidelity = prov.effective_fidelity(entry)
        where = "%s -> %s" % (entry["kind"], entry["url"])

        if entry["fidelity"] and entry["fidelity"] not in prov.FIDELITIES:
            errors.append((rel, "%s: unknown fidelity `%s`; allowed: %s"
                           % (where, entry["fidelity"], ", ".join(prov.FIDELITIES))))
            continue

        if not prov.OBLIGATION.get(fidelity, True):
            # Nothing protected was copied, so no upstream terms attach. A licence
            # may still be recorded for the notices, but is not required.
            if entry["license"] and entry["license"] not in prov.KNOWN_LICENSES:
                warnings.append((rel, "%s: unrecognised licence `%s`"
                                 % (where, entry["license"])))
            continue

        upstream = entry["license"]
        if not upstream:
            errors.append((rel, "%s: fidelity `%s` copies expression, so the "
                                "upstream `license:` is required" % (where, fidelity)))
            continue
        if upstream not in prov.PERMITTED_OUTBOUND:
            errors.append((rel, "%s: unknown upstream licence `%s`" % (where, upstream)))
            continue

        permitted = prov.PERMITTED_OUTBOUND[upstream]
        if not permitted:
            errors.append((rel, "%s: upstream is `%s` - no grant of rights, so no "
                                "licence can carry it. Reduce the borrowing until "
                                "fidelity is inspiration-only, or drop it"
                           % (where, upstream)))
            continue
        if effective not in permitted:
            errors.append((rel, "%s: upstream `%s` at fidelity `%s` requires this file "
                                "to be one of [%s], but it is `%s`%s"
                           % (where, upstream, fidelity, ", ".join(permitted), effective,
                              " (repo default)" if not declared else " (declared)")))
    return errors, warnings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=REPO)
    parser.add_argument("--json", action="store_true",
                        help="machine-readable output for release-check.py")
    args = parser.parse_args()

    all_errors, all_warnings, records = [], [], []
    for path in prov.iter_files(args.root):
        record = prov.parse(path)
        records.append(record)
        errors, warnings = check_file(record)
        all_errors.extend(errors)
        all_warnings.extend(warnings)

    tracked = [e for r in records for e in r["entries"]
               if e["kind"] == "adaptedFrom"]
    obligated = [e for r in records for e in r["entries"]
                 if prov.OBLIGATION.get(prov.effective_fidelity(e), True)]

    if args.json:
        print(json.dumps({
            "files": len(records),
            "trackedEntries": len(tracked),
            "obligationBearing": len(obligated),
            "errors": [{"file": f, "message": m} for f, m in all_errors],
            "warnings": [{"file": f, "message": m} for f, m in all_warnings],
            "entries": [
                {"file": os.path.relpath(r["path"], args.root).replace("\\", "/"),
                 "kind": e["kind"], "url": e["url"], "license": e["license"],
                 "fidelity": prov.effective_fidelity(e),
                 "effectiveLicense": r["effective"]}
                for r in records for e in r["entries"]],
        }, indent=2))
        return 1 if all_errors else 0

    for rel, message in all_warnings:
        print("warning: %s: %s" % (rel, message), file=sys.stderr)
    for rel, message in all_errors:
        print("error: %s: %s" % (rel, message), file=sys.stderr)

    print("checked %d file(s): %d provenance entr(ies), %d carrying an upstream obligation"
          % (len(records), sum(len(r["entries"]) for r in records), len(obligated)))
    if all_errors:
        print("%d error(s)" % len(all_errors), file=sys.stderr)
        return 1
    print("licences OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
