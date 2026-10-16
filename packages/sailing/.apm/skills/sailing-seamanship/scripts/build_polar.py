#!/usr/bin/env python3
"""Build a polar table from a boat's own instrument log.

Input is a CSV with a header row. Either true wind columns (tws, twa) or
apparent wind columns (aws, awa) are required, plus boat speed (bsp; stw or
sog are accepted as aliases). Angles are degrees off the bow, 0-180; a signed
angle (-180..180, port negative) is folded to 0-180. An optional column named
"exclude" with any non-empty value drops that row (motoring, sail change,
manoeuvre).

Usage:
  python3 -I build_polar.py LOG.csv [--tws-bin 2] [--twa-bin 10]
                           [--pct 90] [--min-samples 10] [--json]

Defaults, and why:
  2 kn x 10 deg bins - coarse enough that a day's log fills most bins, fine
                       enough to show where the best VMG angle sits.
  90th percentile    - the polar is what the boat does when trimmed well, so a
                       high percentile, not the mean; not the max, which is
                       usually a gust or a wave.
  10 samples per bin - fewer is noise; such bins are left empty, not guessed.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path

HALF_TURN = 180.0
BEAM_REACH = 90.0
ALIASES = {"bsp": ("bsp", "stw", "sog", "boatspeed", "speed")}


def fold(angle: float) -> float:
    a = abs(angle) % 360
    return 360 - a if a > HALF_TURN else a


def true_wind(aws: float, awa: float, bsp: float) -> tuple[float, float]:
    """True wind speed and angle from apparent wind and boat speed (no leeway)."""
    rad = math.radians(awa)
    x = aws * math.cos(rad) - bsp
    y = aws * math.sin(rad)
    return math.hypot(x, y), math.degrees(math.atan2(y, x))


def pick(row: dict[str, str], *names: str) -> str | None:
    for n in names:
        if n in row and row[n].strip():
            return row[n]
    return None


def read_rows(path: Path) -> list[tuple[float, float, float]]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames:
            sys.exit(f"error: {path} has no header row")
        cols = {c.strip().lower() for c in reader.fieldnames}
        has_true = {"tws", "twa"} <= cols
        has_app = {"aws", "awa"} <= cols
        if not (has_true or has_app) or not cols & set(ALIASES["bsp"]):
            sys.exit("error: need tws+twa or aws+awa, and a boat speed column (bsp, stw or sog)")
        out = []
        for raw in reader:
            row = {k.strip().lower(): (v or "") for k, v in raw.items() if k}
            if row.get("exclude", "").strip():
                continue
            try:
                bsp = float(pick(row, *ALIASES["bsp"]) or "nan")
                if has_true:
                    tws, twa = float(row["tws"]), fold(float(row["twa"]))
                else:
                    tws, twa = true_wind(float(row["aws"]), fold(float(row["awa"])), bsp)
            except ValueError:
                continue
            if math.isnan(bsp) or bsp < 0 or tws <= 0:
                continue
            out.append((tws, twa, bsp))
    if not out:
        sys.exit(f"error: no usable rows in {path}")
    return out


def percentile(values: list[float], pct: float) -> float:
    s = sorted(values)
    k = (len(s) - 1) * pct / 100
    lo, hi = math.floor(k), math.ceil(k)
    return s[lo] if lo == hi else s[lo] + (s[hi] - s[lo]) * (k - lo)


def main() -> None:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("log", type=Path)
    p.add_argument("--tws-bin", type=float, default=2.0)
    p.add_argument("--twa-bin", type=float, default=10.0)
    p.add_argument("--pct", type=float, default=90.0)
    p.add_argument("--min-samples", type=int, default=10)
    p.add_argument("--json", action="store_true")
    args = p.parse_args()
    if not args.log.is_file():
        sys.exit(f"error: {args.log} not found")

    bins: dict[tuple[float, float], list[float]] = {}
    for tws, twa, bsp in read_rows(args.log):
        key = (
            math.floor(tws / args.tws_bin) * args.tws_bin,
            math.floor(twa / args.twa_bin) * args.twa_bin,
        )
        bins.setdefault(key, []).append(bsp)

    polar = {
        k: round(percentile(v, args.pct), 2) for k, v in bins.items() if len(v) >= args.min_samples
    }
    if not polar:
        sys.exit(f"error: no bin reached {args.min_samples} samples; log more or widen the bins")
    tws_keys = sorted({k[0] for k in polar})
    twa_keys = sorted({k[1] for k in polar})

    best = {}
    for tws in tws_keys:
        cells = [(twa, polar[(tws, twa)]) for twa in twa_keys if (tws, twa) in polar]
        for side, test, ref in (
            ("up", lambda a: a < BEAM_REACH, 0.0),
            ("down", lambda a: a >= BEAM_REACH, HALF_TURN),
        ):
            side_cells = [
                (twa, s, s * abs(math.cos(math.radians(twa + args.twa_bin / 2 - ref))))
                for twa, s in cells
                if test(twa)
            ]
            if side_cells:
                twa, s, v = max(side_cells, key=lambda c: c[2])
                best[(tws, side)] = (twa, s, round(v, 2))

    if args.json:
        print(
            json.dumps(
                {
                    "bins": {"tws": args.tws_bin, "twa": args.twa_bin, "percentile": args.pct},
                    "polar": [
                        {"tws": k[0], "twa": k[1], "bsp": v} for k, v in sorted(polar.items())
                    ],
                    "best_vmg": [
                        {"tws": k[0], "side": k[1], "twa": t, "bsp": s, "vmg": v}
                        for k, (t, s, v) in sorted(best.items())
                    ],
                },
                indent=2,
            )
        )
        return
    print("| TWA \\ TWS | " + " | ".join(f"{t:g}-{t + args.tws_bin:g}" for t in tws_keys) + " |")
    print("| --- |" + " --- |" * len(tws_keys))
    for twa in twa_keys:
        cells = [f"{polar[(t, twa)]:.1f}" if (t, twa) in polar else "" for t in tws_keys]
        print(f"| {twa:g}-{twa + args.twa_bin:g} | " + " | ".join(cells) + " |")
    print("\n| TWS | Best upwind TWA | VMG | Best downwind TWA | VMG |")
    print("| --- | --- | --- | --- | --- |")
    for t in tws_keys:
        up, dn = best.get((t, "up")), best.get((t, "down"))
        u = f"{up[0]:g}-{up[0] + args.twa_bin:g} | {up[2]:.2f}" if up else " | "
        d = f"{dn[0]:g}-{dn[0] + args.twa_bin:g} | {dn[2]:.2f}" if dn else " | "
        print(f"| {t:g}-{t + args.tws_bin:g} | {u} | {d} |")


if __name__ == "__main__":
    main()
