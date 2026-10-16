---
name: "sailing-route-planning"
description: "Plans sailing days and passages and picks where to stop: weather windows, marinas, town quays, anchorages, mooring buoys and restaurant jetties, compared on facilities, shelter, depth and the berth price for this boat. ALWAYS invoke when asked where to sail, stay, anchor or moor, to compare harbours or anchorages, to price a berth, to check wind or sea state for a route, or to list the stops in a track log. Do not recommend or price a stop from recall or a generic listing — season-end closures, multihull surcharges and the bay's open sectors decide whether a stop works, and only a sourced check against this boat catches them. Does not cover crew, provisioning or crew documents (sailing-onboard-planning) or trim and repairs (sailing-seamanship). Keywords: marina, harbour, port, town quay, anchorage, mooring buoy, mooring field, restaurant jetty, berth, mooring fee, passage, route, weather window, wind, swell, forecast, shelter, national park, Navily, track log, KML, GPX."
---

# Sailing Route Planning

Decide where the boat goes and where it spends the night. Every answer is checked against **this boat**, **these dates** and **this forecast**. A berth that is fine for a 12 m monohull in July can be closed, too short or twice the price for a 14 m catamaran in October.

## Before the first answer

1. **Boat profile.** Length overall, beam, draft, monohull or multihull, air draft. Read it from the conversation, the project files or a boat-profile tool. Ask once only if none of those has it. Every price, depth and length limit depends on it.
2. **Charter constraints.** Is night sailing permitted, where are the cruising-area limits, what are the return time and fuel rules, and must the boat be on a berth on certain nights? The charter contract decides these. Ask the skipper; never assume them.
3. **Tools this session reaches.** Use the order in [sources.md](references/sources.md): marine data server, Navily, cruising guides and wikis, operator pages, then general web. Name the source behind every number.

## Weather

- **Work out the season yourself.** Find typical sea temperature, night temperature and the prevailing and seasonal winds from the dates and place with a search. State the assumption in one line and don't ask for it.
- **A usable forecast exists about five days out.** Before that, give the seasonal picture and say when to re-check.
- **Check the overnight forecast at the spot itself.** For every anchorage or buoy, compare wind direction and gusts for the whole night against the bay's open sectors. A light-wind forecast makes shelter a minor factor; say so rather than ranking on it.
- **When the decision matters, compare two models or sources.** Report any disagreement instead of averaging it away.
- **Name the local wind systems** that matter for the area and season. Say what each does to the stop: swell into the bay, gusts off the land, a shift overnight.

## Finding and choosing a stop

Default criteria, in order, unless the skipper sets others:

1. **Sanitary facilities**: whether there are showers and toilets, their rating with the number of ratings, and how recent the reviews are. A quay with water and power only has no showers; say so plainly.
2. **Distance to what the crew wants ashore**: old town, viewpoint, supermarket, restaurants. Give walking minutes, or the taxi option if it is far.
3. **Price for this boat.** Compute it; never quote a headline rate. See [berth-pricing.md](references/berth-pricing.md).

Check these for every candidate, whatever the criteria:

- **Fit.** Maximum length, depth at the berth, multihull acceptance. For buoy fields, read reviews on spacing: a field rated for the boat's length can still be cramped.
- **Season and opening.** In the shoulder season, operators of buoy fields and restaurant jetties may have left. Reception hours shorten, and restaurants close on fixed dates. Find the season end or opening hours, and recommend a phone or VHF call when an open status for the date cannot be confirmed.
- **Mooring type and terms.** Laid lines, buoy, anchor or alongside. Note "free if the crew dines" conditions (often the whole crew) and when to arrive. Protected areas need permits or tickets separate from restaurant moorings; check who runs which buoys and don't assume either way.
- **Buoys.** Find who operates the field and whether buoys carry a holding or size rating. If nobody attends, inspect the block and chain before trusting the buoy. A buoy outside a marked field may be private.
- **Approach.** Shallow passages, rocks or restricted zones on the way in.
- **Reachability.** Phone, VHF channel, booking app or reservation policy.

When a mooring term in the request is ambiguous, ask before researching. "Forward-facing mooring", for example, could mean bow-to on lines or a buoy.

## Output

- **Answer first, then a comparison table.** One row per candidate, columns for the criteria above, the price for this boat, and contact or VHF. Then **one pick per criterion** when no candidate wins on all of them, plus the combination that satisfies all of them if there is one (for example: the best showers plus a short taxi ride).
- **Eliminate weak candidates explicitly**, with the reason.
- **List what could not be verified**, such as an undated source, last year's price list or an unconfirmed opening, each with how to confirm it.
- **In-trip requests come from a phone on the boat.** Keep them short, resolve "tomorrow" against the local date, and put phone numbers and VHF channels in the table.
- Cite sources at the end, with the price-list year where one applies.

## Track logs

To list where the boat actually went (for a post-trip survey, logbook or retrospective), run [track_stops.py](scripts/track_stops.py) on the KML or GPX export. It finds overnight stops and day stops (stationary 20 minutes or more within 0.15 nm). Pass the charter base and fuel dock with `--exclude`, and the area's time zone with `--tz`. Name each stop with a reverse-geocode tool, then **flag names that come only from charts**. The crew may know the place by another name. Ask for the log instead of falling back to free text.

## Gotchas

- **Headline prices assume a monohull.** Multihull surcharges commonly run from +50% to double. Third-party price tables are often several years old.
- **Data tools label places from map data.** Geocoded names can be obscure chart names, and place-type filters differ between tools (`type` versus `types`). Read the tool's schema before the first search.
- **Municipal and port-authority rules are often only in the local language.** Search in that language using its words for "price list", "tariff", "parking" and "fee". English queries come back thin.
- **Some operator sites block automated reading.** Report the block, use a secondary source with its date, and give the phone number. Don't present the secondary figure as confirmed.
