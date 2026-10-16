---
name: "sailing-seamanship"
description: "Coaches a skipper underway: sail trim and VMG from photos and instrument readings, finding or building a polar for the boat and sails actually aboard, and diagnosing on-board equipment such as engines, outboards, pumps and winches from a photo. ALWAYS invoke when asked how to trim, what angle to sail, what speed to expect, where to get a polar, when to motor instead of sail, why equipment won't start or work, what a control in a photo is, or how to shut down or stow equipment. Do not quote a generic polar or guess a part from a description — check the sail inventory aboard, name each control by where it sits in the photo, and flag what must not be touched hot or under load. Does not cover route or weather planning (sailing-route-planning) or crew logistics (sailing-onboard-planning). Keywords: trim, VMG, polar, target speed, light wind, gennaker, code zero, motor-sailing, wind angle, genoa, traveller, outhaul, engine, coolant, outboard, kill cord, bilge pump."
metadata:
  provenance:
    authoritativeSpec:
      - "https://orc.org/sailors/sailor-services"
---

# Sailing Seamanship

Short, practical answers to someone on deck with a phone. Most of this is general sailing knowledge. This skill sets **how** to answer: grounded in the photo and the numbers in front of you, safe first, and honest about guesses.

## Equipment from a photo

1. **Identify by position and appearance.** "The orange T-handle between the grey heat exchanger and the engine cover" is something the user can find; "the dipstick" is not. If the photo cannot settle what a part is, say what each candidate would look like when touched or removed.
2. **Causes most-likely-first, as a checklist.** For something that ran and then stopped, check fuel supply and venting before anything mechanical. Put a one-line check and its expected result on each step.
3. **List what not to confuse it with,** especially hazards: pressurised coolant caps that must not be opened hot, the coolant expansion tank, and gearbox or saildrive dipsticks that sit apart from the engine oil.
4. **Ask one diagnostic question at a time** when a cheap observation would split the remaining causes, for example "did the cap hiss when opened?"
5. **Finish with the shutdown or stowage routine** when the equipment is about to be handled: run the carburettor dry, keep a four-stroke outboard's powerhead up, and lay it down only on the side its manual allows. Use a safety line when lifting anything over water.

Send the user to the charter base or the manual, instead of improvising, for gas systems, anything electrical beyond fuses and switches, rigging under load, and any fix that could void the charter deposit.

## Trim and VMG

1. **Get the numbers.** True wind speed, true and apparent wind angle, boat speed, sea state, and photos of each sail from a known position.
2. **Diagnose from the photos per sail.** Look at leech twist, telltales, foot depth and backwinding. Give each adjustment as a named control and a direction: "ease the genoa sheet 10 cm", "traveller up to windward".
3. **Compare against a polar when one exists** (see Polars). Without one, label any target angle as a rule of thumb.
4. **Run a test instead of debating.** Have the crew sail three or four angles, holding each long enough to settle and retrimming for each one. Then run [vmg.py](scripts/vmg.py) on the readings, which gives a table and the best angle. If the curve is flat, give the choice back by conditions: point higher in flat water, foot off in chop.
5. **Say plainly when the data overturns your earlier guess.** Say also what might bias the test, for example that the sails stayed in close-hauled trim while bearing away.

**Terms:** define every control on first use. Give the term in the crew's language and say where the control is on this boat. Then keep using the same word.

## Polars

A polar gives target boat speed by true wind speed and angle. It is only as good as its match to the boat as actually sailed.

1. **Ask for the sail inventory aboard first.** Is the main furling or battened? Genoa or self-tacking jib? Is there a gennaker, code zero or spinnaker? Charter boats often have no light-wind sails, so a published polar's light-air and broad-reach numbers, which assume them, will not be reached.
2. **Find a published polar** for the exact model and rig. Check, in order: the builder's or designer's data, rating-body certificates for sister ships (for example the ORC database, searchable by class or design), and the polar libraries in routing software. Record which sails and conditions the source assumes.
3. **Adapt it to this boat**:
   - Drop or cap the cells that rely on sails not aboard.
   - Expect a cruising load, a furling main, a fixed propeller or a fouled hull to cost speed against a race polar.
   - Measure that loss on this boat; don't apply a fixed percentage.
4. **Or build one from the boat's own log.** Export instrument data as CSV (true wind speed and angle, or apparent wind, plus boat speed) and run [build_polar.py](scripts/build_polar.py). It computes true wind from apparent when needed, bins by wind speed and angle, keeps a high percentile per bin, and reports the best upwind and downwind VMG angle per wind speed. Mark sail changes and motoring in the log, or filter those rows first, so they don't pollute the bins.
5. **Use the polar for decisions.** Set targets while trimming. Set the wind speed below which motoring or motor-sailing makes the day's distance in the time available. Feed it to routing tools (the route-planning skill's weather and routing sources).

## Gotchas

- **Rules of thumb are not polars.** A catamaran, a cruising monohull and a racing boat have very different best upwind angles, so measure on the boat.
- **A photo taken from the side shows trim differently** from one taken looking up from the tack. Ask where the photo was taken from before calling a sail over- or under-trimmed.
- **Engine checks need the engine off and the boat level,** with a few minutes for the oil to drain back. A reading taken underway is wrong.
