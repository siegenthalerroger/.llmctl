#!/usr/bin/env python3
"""Velocity made good from measured angle/speed pairs.

VMG = boat speed x cos(true wind angle) for upwind angles (< 90 deg) and
boat speed x cos(180 - TWA) for downwind ones, so both sides report a positive
speed toward or away from the wind.

Usage:
  python3 -I vmg.py 40:5.8 45:6.4 50:6.7 55:6.9

Each argument is TWA_DEGREES:BOAT_SPEED_KNOTS (speed through water or SOG,
whichever was read; say which in the answer). Prints a Markdown table sorted by
angle, the best angle, and every angle within FLAT_PCT of the best, because
a flat top means the choice can follow sea state instead.
"""

from __future__ import annotations

import math
import sys

BEAM_REACH = 90  # degrees: below it the angle counts as upwind
HALF_TURN = 180
FLAT_PCT = 2.0  # within 2% of the best VMG counts as the same, given instrument noise


def parse(arg: str) -> tuple[float, float]:
    try:
        twa, speed = (float(v) for v in arg.split(":"))
    except ValueError:
        sys.exit(f"error: expected TWA:SPEED, got {arg!r}")
    if not 0 < twa < HALF_TURN or speed < 0:
        sys.exit(f"error: TWA must be between 0 and 180 and speed non-negative, got {arg!r}")
    return twa, speed


def vmg(twa: float, speed: float) -> float:
    angle = twa if twa < BEAM_REACH else HALF_TURN - twa
    return speed * math.cos(math.radians(angle))


def main() -> None:
    if len(sys.argv) < 3:  # noqa: PLR2004 -- program name plus at least two readings
        sys.exit(__doc__)
    pairs = sorted(parse(a) for a in sys.argv[1:])
    upwind = {p[0] < BEAM_REACH for p in pairs}
    if len(upwind) > 1:
        sys.exit("error: mix of upwind and downwind angles; run them separately")
    rows = [(twa, speed, vmg(twa, speed)) for twa, speed in pairs]
    best = max(rows, key=lambda r: r[2])
    print("| TWA | Speed (kn) | VMG (kn) | vs best |")
    print("| --- | --- | --- | --- |")
    for twa, speed, v in rows:
        print(f"| {twa:g} | {speed:.2f} | {v:.2f} | {100 * (v - best[2]) / best[2]:+.1f}% |")
    flat = [f"{t:g}" for t, _, v in rows if v >= best[2] * (1 - FLAT_PCT / 100)]
    print(
        f"\nBest: {best[0]:g} TWA, VMG {best[2]:.2f} kn. "
        f"Within {FLAT_PCT:g}% of best: {', '.join(flat)}."
    )


if __name__ == "__main__":
    main()
