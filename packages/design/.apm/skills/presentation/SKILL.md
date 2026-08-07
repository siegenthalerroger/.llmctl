---
name: "presentation"
description: "Builds presentations argument-first — one assertion per slide, titles that state the finding, sequenced into a narrative — then sets each slide for a room rather than for a reader. ALWAYS invoke when creating, restructuring or reviewing a slide deck, talk, pitch or any projected material, including when asked only to 'turn this into slides'. Owns projection constraints: reading distance, ambient light and collapsed contrast. It does not generate files in any particular format. Do not write slide titles, decide a slide count or size text for a deck without this skill. Keywords: presentation, slides, slide deck, talk, pitch, keynote, projector, speaker notes, slide title, storyline, narrative, agenda."
metadata:
  provenance:
    adaptedFrom:
      - url: "https://openlibrary.org/isbn/9780273710516"
        license: NONE
        fidelity: inspiration-only
        took: "The pyramid principle -- conclusion first, support grouped beneath it, groups that neither overlap nor leave gaps -- and the situation/complication/question/answer frame. Action titles are later consulting-house practice built on this, not Minto's own term."
      - url: "https://openlibrary.org/isbn/9780470632017"
        license: NONE
        fidelity: inspiration-only
        took: "Narrative contrast as the engine of a deck -- oscillating between what is and what could be -- and the audience rather than the presenter as the one who acts."
      - url: "https://openlibrary.org/isbn/9780321811981"
        license: NONE
        fidelity: inspiration-only
        took: "Restraint and signal-to-noise as the governing constraint on a slide, and the case for showing over listing."
      - url: "https://guykawasaki.com/the_102030_rule/"
        license: NONE
        fidelity: inspiration-only
        took: "The argument that a type-size floor is really a content-density constraint in disguise. The specific 10/20/30 numbers are deliberately not carried."
---

# Presentation

A deck is a structured argument delivered to a room. The argument is built first, in words; the slides come after, and exist to carry it.

Get the audience, job and register from `design-direction` first — a board update, a conference talk and a sales pitch are different arguments before they are different designs.

## Build the argument before opening any slide

Work in plain text or on paper. Slide software encourages filling slides, and a deck assembled slide-by-slide acquires its structure by accident.

1. **State the answer first.** Lead with the conclusion, then support it. A deck that withholds its point until slide 30 has asked the audience to hold unexplained detail in memory for the whole build-up.
2. **Frame it:** the situation everyone accepts, the complication that disturbs it, the question that raises, and your answer. That frame is the spine.
3. **Group the support** so each branch genuinely backs the claim above it, and the branches do not overlap or leave gaps.
4. **Write the assertion for each slide** — one sentence, arguable, complete.
5. **Only then** decide what goes on each slide to prove it.

**The title test:** read the slide titles in order, and nothing else. If that reads as a coherent argument, the deck has one. If it reads as a table of contents, the deck is a document with page breaks.

## Titles assert; they do not label

The highest-leverage rule in deck design, and the most reliably broken.

| Instead of | Write |
|---|---|
| "Q3 Revenue" | "Revenue grew on retention, not new logos" |
| "Migration Timeline" | "The migration slips a quarter unless we hire in March" |
| "Competitive Landscape" | "We win on integration depth and lose on price" |

A label names the subject and leaves the audience to work out why they are looking at it. An assertion delivers the finding and lets the slide body serve as evidence. Everything on the slide should be there because it supports the title — anything that does not either moves or goes.

## One idea per slide

- **If a slide needs two assertions, it is two slides.** Slides are free; the audience's attention is not.
- **Cut everything that does not serve the assertion.** Every additional element competes with the one thing the slide is for.
- **A slide should be comprehensible at a glance** — a few seconds — because the audience is also listening. Anything requiring study steals attention from the speaker, and they will read rather than listen every time.
- **Show rather than list where the content permits it.** A diagram, an image or a single number often carries what a bulleted list only describes.

## Rhythm

A deck where every slide is equally full cannot signal what matters. Density is a hierarchy device at deck level, exactly as size is within a page.

- **Some slides carry one number, or one image, or four words.** These are the slides people remember, and they only work if the surrounding slides are denser.
- **Build contrast into the sequence** — what is now against what could be, problem against resolution. Movement between those states is what makes an argument feel like it is going somewhere rather than accumulating.
- **Slide count follows from the argument.** Never pad to a target and never compress two assertions onto one slide to hit one.

## Projection — this skill owns it

The room is the medium, and it is far more hostile than a monitor.

- **Size type from the furthest seat.** The practical test: shrink the slide to a thumbnail, or stand well back from your own screen. If it is not readable there, the back row cannot read it. Body text sized for reading is always too small projected.
- **A hard size floor is a content constraint in disguise.** If the text will not fit at a genuinely large size, there is too much text — that is the rule's real value, not the specific number.
- **Ambient light lifts blacks and collapses contrast.** Subtle low-contrast pairs and dark-on-dark detail that pass on a monitor disappear on a wall. Increase separation beyond what the screen requires, and never rely on a faint tint to carry meaning.
- **Assume a bad projector, a washed-out room, and a video-call re-encode.** Thin hairlines, fine gradients and small colour differences survive none of them.
- **Respect the safe area.** Edges get cropped by overscan, blocked by furniture, or covered by a video-call participant strip. Keep content away from the margins.
- **Verify aspect ratio before designing**, not after. Reflowing a finished deck between 16:9 and 4:3 breaks every composition in it.

## The deck is not the document

A deck that supports a speaker and a deck that is read alone are two different artefacts, and one file cannot be both — the support deck is too sparse to read, the read deck is too dense to present behind.

**Say which one is being built.** If both are needed, the answer is a sparse deck plus speaker notes or a written companion, not a compromise that fails at both.

## Routing

| For | Load |
|---|---|
| Type sizing, pairing, hierarchy | `typography` |
| Palette, contrast, colour-vision safety | `colour` |
| Composition within a slide | `layout` |
| Any chart or data graphic | `dataviz` |

This skill owns the argument, the sequence, and the projection medium.

## Gotchas

- **"Turn this into slides" is not a formatting request.** A document reflowed into slides has no argument, because documents carry their logic in prose that the slides drop. Re-derive the assertions.
- **The agenda slide usually earns nothing.** Restating the structure to the audience delays the answer. Use it only where the audience genuinely needs to navigate a long session.
- **The final slide is the most-remembered position in the deck.** Spending it on "Thank you" or "Questions?" wastes it. End on the assertion you want them to leave with.
- **Speaker notes are where detail belongs.** Detail that matters but does not fit belongs in the notes or an appendix, never squeezed onto the slide at a smaller size.
- **Do not generate files here.** This skill decides what the deck says and how it is set; producing a file in some format is a separate, tool-specific job.

## Verification

**Write the title sequence out in full for step 1.** Reading it back is the check; asserting that it reads well is not, and this is the step that gets skipped.

1. Read only the titles, top to bottom. Is it an argument?
2. Does every slide carry exactly one assertion, and does its content support that assertion?
3. Is each slide comprehensible at a glance?
4. Does the deck have density variation, or is every slide equally full?
5. At thumbnail size, is every slide still readable?
6. Do contrast and separation survive a lit room?
7. Is it clear whether this is a support deck or a standalone read — and does it commit to one?
8. Does the last slide land the point?

## References

- [references/structures.md](./references/structures.md) — narrative structures for a deck (situation-complication-question-answer, current-versus-possible, problem-solution, chronological, and the case for each), plus how to pick one from the audience and the ask.

---

Built on the published presentation literature: Barbara Minto's pyramid principle and its situation–complication–question–answer framing — action titles are consulting-house practice built on top of it rather than Minto's own term — Nancy Duarte on narrative contrast and the audience as protagonist, Garr Reynolds on restraint and signal-to-noise, and Guy Kawasaki's argument that a type-size floor is really a content-density constraint. Cited, not reproduced.
