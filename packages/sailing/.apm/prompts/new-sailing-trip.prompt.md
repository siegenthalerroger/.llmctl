---
name: "new-sailing-trip"
description: "Sets up a new sailing trip: one intake on dates, base, boat, sail inventory, charter terms and crew, then a trip sheet, a backward-dated timeline of deadlines and the list of crew documents to prepare. ALWAYS invoke when starting a new charter or cruise as a project. Do not use for a single question during a trip — load the sailing skill that covers it instead."
agent: agent
argument-hint: "dates, sailing area or base, boat, crew size, and anything already booked"
# Claude Code fields
skills: ['sailing-route-planning', 'sailing-onboard-planning', 'sailing-seamanship']
---

Set up a sailing trip from the brief supplied with this command: `${input:brief:dates, sailing area or base, boat, crew size, and anything already booked}`

## Goal

A trip sheet holding every fact the later work depends on, each marked confirmed or open; a timeline of dated deadlines; and the list of crew documents to prepare.

## 1. Read before asking

Search the project files, uploads and earlier conversations for a booking confirmation, a charter contract, a boat specification or inventory, crew lists, and the skipper's existing crew documents. Take every fact found there. Ask only for what is still missing.

## 2. Intake: one batch, skipping what step 1 answered

- **Dates and base**: boarding and return dates with check-in and check-out times; charter company and base marina; one-way or return.
- **Boat**: make, model and year; length overall, beam, draft and air draft; monohull or multihull; cabins and heads; engines; dinghy and outboard; power (solar, generator, shore-power plug) and water capacity.
- **Sail inventory**: main (furling or battened), headsail type, and whether a gennaker, code zero or spinnaker is aboard.
- **Charter terms**: bareboat or skippered; night sailing and cruising-area limits; crew-list deadline and the documents and licences it requires; deposit and insurance; what is included (bedding, towels, outboard fuel, gas).
- **Crew**: size per week; crew changes with date and place; how each person arrives; who holds which licences.
- **Intent**: the mix of marina and anchorage nights, preferred daily distance, places the crew must see, and restaurant evenings.
- **Tools and storage**: where trip documents live, the language of crew documents, whether a Windy key is Professional-tier, and which app records the track.

## 3. Checks before any plan

- If the travel plugin's skills are installed, run `destination-calendar` across the window and `travel-entry-requirements` for every nationality aboard. Otherwise, search for the same.
- Look up what the sailing area requires of a visiting boat and skipper: cruising permits or vessel fees, tourist tax, national or nature park tickets, anchoring restrictions, and the licence and radio rules for the flag state.
- Establish the season's prevailing and local winds and the sea temperature for the dates.
- Check how much of the area the marine data servers cover (see the sailing-route-planning sources reference).

## 4. Polar

Using the sailing-seamanship skill, find a polar for this model and rig and adapt it to the sail inventory aboard. If none exists, record that one will be built from the first days' log.

## 5. Deliverables

1. **Trip sheet**: the intake fields and the results of step 3, each with its source and marked confirmed or open.
2. **Timeline**, sorted by date and counted back from boarding: crew survey out; charter crew-list deadline; packing lists; provisioning plan; marina and restaurant reservations that need booking in season; park tickets; car, transfer or parking.
3. **Crew documents to prepare**: from the sailing-onboard-planning catalogue, pick the ones this trip needs and note their order.
4. **Open questions** for the skipper, in one list.

Done when every intake field is filled or listed as an open question, every timeline entry has a date, and every looked-up fact names its source.
