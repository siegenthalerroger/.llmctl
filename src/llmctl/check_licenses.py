"""Check that every file's licence can carry the upstream terms it inherits.

Per provenance entry: does the fidelity mean expression was copied, and if so can
this file's effective licence satisfy that upstream's? check.py imports `check()`
for its `licences` gate. Rules: CONTRIBUTING.md#licensing.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import NamedTuple

import typer

from . import provenance as prov
from . import workspace


class Report(NamedTuple):
    """What one pass over the tree found. `errors` fail the gate; `warnings` do not."""

    errors: list[tuple[str, str]]
    warnings: list[tuple[str, str]]
    records: list[prov.Record]
    tracked: list[prov.Entry]
    obligated: list[prov.Entry]


def check_file(
    record: prov.Record, root: Path
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Return (errors, warnings) for one parsed file."""
    errors, warnings = [], []
    rel = os.path.relpath(record.path, root).replace("\\", "/")

    for problem in record.malformed:
        errors.append(
            (
                rel,
                problem + " - a provenance block that parses to nothing "
                "stops being tracked silently",
            )
        )

    declared = record.declared
    effective = record.effective
    if declared and declared not in prov.KNOWN_LICENSES:
        errors.append(
            (
                rel,
                "declares unknown licence `{}`; known: {}".format(
                    declared, ", ".join(prov.KNOWN_LICENSES)
                ),
            )
        )

    for entry in record.entries:
        fidelity = prov.effective_fidelity(entry)
        where = f"{entry.kind} -> {entry.url}"

        if entry.fidelity and entry.fidelity not in prov.FIDELITIES:
            errors.append(
                (
                    rel,
                    "{}: unknown fidelity `{}`; allowed: {}".format(
                        where, entry.fidelity, ", ".join(prov.FIDELITIES)
                    ),
                )
            )
            continue

        if not prov.OBLIGATION.get(fidelity, True):
            # Nothing protected was copied, so no upstream terms attach. A licence
            # may still be recorded for the notices, but is not required.
            if entry.license and entry.license not in prov.KNOWN_LICENSES:
                warnings.append((rel, f"{where}: unrecognised licence `{entry.license}`"))
            continue

        upstream = entry.license
        if not upstream:
            errors.append(
                (
                    rel,
                    f"{where}: fidelity `{fidelity}` copies expression, so the "
                    "upstream `license:` is required",
                )
            )
            continue
        if upstream not in prov.PERMITTED_OUTBOUND:
            errors.append((rel, f"{where}: unknown upstream licence `{upstream}`"))
            continue

        permitted = prov.PERMITTED_OUTBOUND[upstream]
        if not permitted:
            errors.append(
                (
                    rel,
                    f"{where}: upstream is `{upstream}` - no grant of rights, so no "
                    "licence can carry it. Reduce the borrowing until "
                    "fidelity is inspiration-only, or drop it",
                )
            )
            continue
        if effective not in permitted:
            errors.append(
                (
                    rel,
                    "{}: upstream `{}` at fidelity `{}` requires this file "
                    "to be one of [{}], but it is `{}`{}".format(
                        where,
                        upstream,
                        fidelity,
                        ", ".join(permitted),
                        effective,
                        " (repo default)" if not declared else " (declared)",
                    ),
                )
            )
    return errors, warnings


def check(root: Path) -> Report:
    """Every file's findings, plus the counts the summary line reports."""
    errors, warnings, records = [], [], []
    for path in prov.iter_files(root):
        record = prov.parse(path)
        records.append(record)
        e, w = check_file(record, root)
        errors.extend(e)
        warnings.extend(w)
    tracked = [e for r in records for e in r.entries if e.kind == "adaptedFrom"]
    obligated = [
        e
        for r in records
        for e in r.entries
        if prov.OBLIGATION.get(prov.effective_fidelity(e), True)
    ]
    return Report(errors, warnings, records, tracked, obligated)


def summary(report: Report) -> str:
    entries = sum(len(r.entries) for r in report.records)
    return (
        f"checked {len(report.records)} file(s): {entries} provenance entr(ies), "
        f"{len(report.obligated)} carrying an upstream obligation"
    )


def main(
    repo: Path = workspace.REPO_OPTION,
    json_out: bool = typer.Option(False, "--json", help="Machine-readable output on stdout."),
) -> None:
    """Check every file's licence against the upstream terms its provenance records."""
    root = repo.resolve()
    report = check(root)

    if json_out:
        print(
            json.dumps(
                {
                    "files": len(report.records),
                    "trackedEntries": len(report.tracked),
                    "obligationBearing": len(report.obligated),
                    "errors": [{"file": f, "message": m} for f, m in report.errors],
                    "warnings": [{"file": f, "message": m} for f, m in report.warnings],
                    "entries": [
                        {
                            "file": os.path.relpath(r.path, root).replace("\\", "/"),
                            "kind": e.kind,
                            "url": e.url,
                            "license": e.license,
                            "fidelity": prov.effective_fidelity(e),
                            "effectiveLicense": r.effective,
                        }
                        for r in report.records
                        for e in r.entries
                    ],
                },
                indent=2,
            )
        )
        raise typer.Exit(1 if report.errors else 0)

    for rel, message in report.warnings:
        print(f"warning: {rel}: {message}", file=sys.stderr)
    for rel, message in report.errors:
        print(f"error: {rel}: {message}", file=sys.stderr)
    print(summary(report))
    if report.errors:
        print(f"{len(report.errors)} error(s)", file=sys.stderr)
        raise typer.Exit(1)
    print("licences OK")


def cli() -> None:
    typer.run(main)
