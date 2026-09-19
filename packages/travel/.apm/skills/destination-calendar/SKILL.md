---
name: "destination-calendar"
description: "Checks what is happening at a destination across a travel window — public holidays, school holidays, observances, and the major events no holiday API carries: races, festivals, Pride and commemorative weekends, trade fairs and congresses, summits, marathons, strikes. ALWAYS invoke before travel dates are fixed, recommended, priced or booked, and whenever asked whether a date range is a good time to visit somewhere. Do not answer a holiday or event question from recall — holiday dates move between years and jurisdictions, event calendars are published per city, and a missed trade-fair week or race weekend doubles hotel rates and empties availability. Keywords: travel dates, when to visit, public holiday, bank holiday, school holiday, term dates, festival, event, trade fair, congress, conference, race weekend, marathon, pride, peak season, shoulder season, crowds, hotel prices, strike, closures."
metadata:
  provenance:
    authoritativeSpec:
      - https://github.com/nager/Nager.Date
      - https://www.openholidaysapi.org/en/
---

# Destination Calendar

One question: **what is happening at this destination during this window, and does it change the plan?**

Answer it before dates are fixed. After booking, the same finding is only bad news.

## The two halves

The work splits by what a machine can be trusted with.

| Half | Covers | How |
|---|---|---|
| Deterministic | Public holidays, school holidays, observances | `scripts/destination_calendar.py` |
| Judgement | Races, festivals, fairs, summits, marathons, strikes | [search-protocol.md](references/search-protocol.md) |

Run both. The script never finds a Grand Prix; a search never reliably enumerates Bavarian school terms.

## 1. Run the script

```bash
python3 scripts/destination_calendar.py report GB 2026-06-20 2026-07-10
python3 scripts/destination_calendar.py report DE 2026-04-01 2026-04-20 --subdivision DE-BY
```

Two keyless sources: Nager.Date for public holidays in 200+ countries, OpenHolidays for European public **and school** holidays with subdivisions. `selftest` runs offline.

Read the output as follows.

- **Bridge days are the finding, not the holiday.** A Thursday holiday in France, Germany or Switzerland takes Friday with it; the script says so. Four-day weekends are when rates peak and inventory vanishes.
- **School holidays outrank public holidays** for price and crowding, and they are regional. Bavaria and Berlin break weeks apart; so do Swiss cantons and French zones A/B/C. Always pass `--subdivision` when the destination is one region of a federal country.
- **Exit 2 means UNKNOWN, never "clear".** A failed source is not an empty calendar. Say the check did not complete.
- **Outside Europe, school coverage is absent.** The script says so. Report it as a gap and fall back to searching the destination's own school-term publication.

## 2. Work the event classes

The script's last line is a reminder that it found no events. Go through
[event-classes.md](references/event-classes.md) — the eight classes that
actually move prices — and rule each in or out using
[search-protocol.md](references/search-protocol.md), which fixes the sources to
check and how to date-bound the queries.

Do not stop at the first hit. A Pride weekend and a congress can land on the
same dates, and the combination is what makes a city unbookable.

## 3. Reach a verdict

Findings are not a report. Turn them into one of four decisions, using
[verdict.md](references/verdict.md):

| Verdict | Means |
|---|---|
| **Shift the dates** | The gain from moving beats the cost |
| **Book now** | Dates are fixed and supply is about to go |
| **Fine, plan around it** | Real but local — avoid one district or one day |
| **Go because of it** | The event is a reason to be there |

State the verdict first, then the evidence.

## Rules

- **Never answer from recall.** Dates shift between years and between jurisdictions; anniversaries land on different weekends; fair calendars rotate between cities. Run the script and search.
- **State the window you actually observed** and the sources you actually reached. "Checked 20 June – 10 July against Nager.Date and two venue calendars" is an answer; "I checked" is not.
- **Name the residual unknown.** Municipal events, local saints' days, school sports days and short-notice strikes are not in any source you just used. Say which stone was left unturned rather than implying completeness.
- **Do not let a clean holiday table read as a clean window.** Most damaging dates are not holidays at all.
- **Distinguish the effects.** Price, availability, crowding, closures, transport disruption and atmosphere are separate axes, and an event can be terrible on one and irrelevant on the rest. A congress wrecks hotel rates and does nothing to museums; a marathon closes roads for a morning and touches nothing else.

## When the destination is a region, not a country

Country codes are the script's input, but holidays are frequently sub-national
and events always are. Run the country, then narrow: `--subdivision DE-BY` for
Munich, `CH-ZH` for Zurich. For the event half, the unit is the city and its
principal venues, never the country.
