#!/usr/bin/env python3
"""List overnight and day stops in a boat's track log (KML or GPX).

A stop is a run of consecutive fixes that stays within RADIUS_NM of where it
began for at least MIN_MINUTES. A stop that spans local midnight, or the last
stop of a day when the log has a gap overnight, is an overnight stop; every
other stop is a day stop.

Defaults, and why:
  0.15 nm radius  - covers swinging at anchor or on a buoy (about 280 m) without
                    merging two neighbouring bays.
  20 min minimum  - drops waiting and drifting halts, keeps a lunch or swim
                    stop. A fuel dock usually exceeds it: --exclude it.

Usage:
  python3 -I track_stops.py LOG.kml [--tz <IANA zone>] [--exclude LAT,LON]
                           [--radius-nm 0.15] [--min-minutes 20] [--json]

--exclude drops stops within the radius of a point (the charter base, a fuel
dock); repeat it for several points. Output is a Markdown table by default.
Names are not resolved here: reverse-geocode each stop's coordinate afterwards.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

NM_PER_DEG_LAT = 60.0
# Two stops this close on consecutive days are the same night's berth, split by a
# gap in logging or a swing on the anchor.
SAME_BERTH_NM = 0.5
# --exclude never matches tighter than this, so a base marina's whole basin drops.
MIN_EXCLUDE_NM = 0.3


@dataclass
class Fix:
    t: datetime
    lat: float
    lon: float


@dataclass
class Stop:
    arrive: datetime
    depart: datetime
    lat: float
    lon: float
    kind: str = "day"

    @property
    def minutes(self) -> int:
        return int((self.depart - self.arrive).total_seconds() // 60)


def distance_nm(a: Fix, lat: float, lon: float) -> float:
    dlat = (a.lat - lat) * NM_PER_DEG_LAT
    dlon = (a.lon - lon) * NM_PER_DEG_LAT * math.cos(math.radians((a.lat + lat) / 2))
    return math.hypot(dlat, dlon)


def parse_time(text: str) -> datetime:
    text = text.strip().replace("Z", "+00:00")
    t = datetime.fromisoformat(text)
    return t if t.tzinfo else t.replace(tzinfo=UTC)


def local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def read_fixes(path: Path) -> list[Fix]:
    try:
        # The log is the user's own export, not untrusted network input.
        root = ET.parse(path).getroot()  # noqa: S314
    except ET.ParseError as exc:
        sys.exit(f"error: {path} is not well-formed XML: {exc}")
    fixes: list[Fix] = []
    elements = list(root.iter())

    # GPX: <trkpt lat lon><time>
    for el in elements:
        lat, lon = el.get("lat"), el.get("lon")
        if local(el.tag) in ("trkpt", "rtept", "wpt") and lat and lon:
            when = next((c.text for c in el if local(c.tag) == "time"), None)
            if when:
                fixes.append(Fix(parse_time(when), float(lat), float(lon)))

    # KML gx:Track: alternating <when> and <gx:coord lon lat alt>
    for el in elements:
        if local(el.tag) == "Track":
            whens = [c.text for c in el if local(c.tag) == "when" and c.text]
            coords = [c.text for c in el if local(c.tag) == "coord" and c.text]
            if len(whens) != len(coords):
                sys.exit(
                    f"error: a gx:Track in {path} has {len(whens)} times "
                    f"but {len(coords)} positions"
                )
            for when, coord in zip(whens, coords, strict=True):
                lon, lat, *_ = (float(v) for v in coord.split())
                fixes.append(Fix(parse_time(when), lat, lon))

    # KML Placemarks: <TimeStamp><when> with a <Point><coordinates lon,lat>
    for el in elements:
        if local(el.tag) != "Placemark":
            continue
        when = next((c.text for c in el.iter() if local(c.tag) == "when"), None)
        coords = next((c.text for c in el.iter() if local(c.tag) == "coordinates"), None)
        point = any(local(c.tag) == "Point" for c in el.iter())
        if when and coords and point:
            lon, lat, *_ = (float(v) for v in coords.strip().split(","))
            fixes.append(Fix(parse_time(when), lat, lon))

    if not fixes:
        sys.exit(
            f"error: no timestamped positions found in {path} "
            "(expected GPX trkpt/time, KML gx:Track or timestamped Placemark points)"
        )
    fixes.sort(key=lambda f: f.t)
    return fixes


def find_stops(fixes: list[Fix], radius_nm: float, min_minutes: int) -> list[Stop]:
    stops: list[Stop] = []
    i = 0
    while i < len(fixes):
        anchor = fixes[i]
        j = i
        while j + 1 < len(fixes) and distance_nm(fixes[j + 1], anchor.lat, anchor.lon) <= radius_nm:
            j += 1
        if fixes[j].t - anchor.t >= timedelta(minutes=min_minutes):
            run = fixes[i : j + 1]
            stops.append(
                Stop(
                    arrive=anchor.t,
                    depart=fixes[j].t,
                    lat=sum(f.lat for f in run) / len(run),
                    lon=sum(f.lon for f in run) / len(run),
                )
            )
        i = j + 1
    return stops


def classify(stops: list[Stop], tz: ZoneInfo) -> None:
    for n, stop in enumerate(stops):
        a, d = stop.arrive.astimezone(tz), stop.depart.astimezone(tz)
        if a.date() != d.date():
            stop.kind = "overnight"
            continue
        # Logs often pause overnight: the last stop of a day is the night's
        # berth when the next stop starts on a later date at the same place.
        nxt = stops[n + 1] if n + 1 < len(stops) else None
        if nxt and nxt.arrive.astimezone(tz).date() > d.date():
            same_place = (
                distance_nm(Fix(nxt.arrive, nxt.lat, nxt.lon), stop.lat, stop.lon) <= SAME_BERTH_NM
            )
            if same_place:
                stop.kind = "overnight"


def merge_overnights(stops: list[Stop]) -> list[Stop]:
    merged: list[Stop] = []
    for stop in stops:
        prev = merged[-1] if merged else None
        if (
            prev
            and prev.kind == "overnight"
            and distance_nm(Fix(stop.arrive, stop.lat, stop.lon), prev.lat, prev.lon)
            <= SAME_BERTH_NM
        ):
            prev.depart = stop.depart
            continue
        merged.append(stop)
    return merged


def main() -> None:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("log", type=Path)
    p.add_argument(
        "--tz", default="UTC", help="IANA time zone of the cruising area, for day boundaries"
    )
    p.add_argument("--radius-nm", type=float, default=0.15)
    p.add_argument("--min-minutes", type=int, default=20)
    p.add_argument("--exclude", action="append", default=[], metavar="LAT,LON")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    if not args.log.is_file():
        sys.exit(f"error: {args.log} not found")
    try:
        tz = ZoneInfo(args.tz)
    except Exception:
        sys.exit(f"error: unknown time zone {args.tz!r}")
    excludes = []
    for item in args.exclude:
        try:
            lat, lon = (float(v) for v in item.split(","))
        except ValueError:
            sys.exit(f"error: --exclude expects LAT,LON, got {item!r}")
        excludes.append((lat, lon))

    stops = find_stops(read_fixes(args.log), args.radius_nm, args.min_minutes)
    classify(stops, tz)
    stops = merge_overnights(stops)
    stops = [
        s
        for s in stops
        if not any(
            distance_nm(Fix(s.arrive, s.lat, s.lon), lat, lon)
            <= max(args.radius_nm, MIN_EXCLUDE_NM)
            for lat, lon in excludes
        )
    ]

    rows = [
        {
            "date": s.arrive.astimezone(tz).date().isoformat(),
            "kind": s.kind,
            "arrive": s.arrive.astimezone(tz).strftime("%Y-%m-%d %H:%M"),
            "depart": s.depart.astimezone(tz).strftime("%Y-%m-%d %H:%M"),
            "minutes": s.minutes,
            "lat": round(s.lat, 5),
            "lon": round(s.lon, 5),
        }
        for s in stops
    ]
    if args.json:
        print(json.dumps(rows, indent=2))
        return
    print("| # | Date | Kind | Arrive | Depart | Lat | Lon |")
    print("| --- | --- | --- | --- | --- | --- | --- |")
    for n, s in enumerate(stops, 1):
        arrive, depart = s.arrive.astimezone(tz), s.depart.astimezone(tz)
        cells: list[object] = [n, arrive.date(), s.kind, f"{arrive:%H:%M}"]
        cells += [f"{depart:%m-%d %H:%M}", round(s.lat, 5), round(s.lon, 5)]
        print("| " + " | ".join(str(c) for c in cells) + " |")


if __name__ == "__main__":
    main()
