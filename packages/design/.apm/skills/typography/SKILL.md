---
name: "typography"
description: "Sets type by deriving a scale, measure, leading and pairing from the medium, reading distance and content rather than applying a default face or ratio. ALWAYS invoke before choosing a typeface, building a type scale, deciding line length or line height, or diagnosing why text 'feels wrong' — in print, on screen, in interfaces and projected. Covers the craft of setting type; colour belongs to the colour skill and grid construction to layout. Do not pick a font, a size ramp or a line height without this skill. Keywords: typography, typeface, font, type scale, modular scale, measure, line length, leading, line height, tracking, letter-spacing, hierarchy, pairing, legibility, readability, baseline, numerals."
metadata:
  provenance:
    adaptedFrom:
      - url: "https://github.com/Design-Machines-Studio/depot/blob/main/plugins/design-practice/skills/typography/SKILL.md"
        license: Unlicense
        fidelity: largely-derived
        took: "The five foundations, with their attributions to Vignelli, Gerstner, Bringhurst, Brown and Rutter; Bringhurst's dependency order (typeface, then size, then measure, then leading) and body-text-as-anchor; the measure table; leading as a function of typeface, size and measure; Mortensen's three-property scale with its temperament vocabulary and the named-ratios-as-one-note mapping; deriving the scale from the medium's own dimensions; asymmetric heading margins; the letterspacing table; Craig's five-family typeface classification; Santa Maria's four-step evaluation method; Gerstner's morphological box; and the web-specific set — fluid type with clamp(), text-wrap balance and pretty, OpenType features, and ranges-not-fixed-values as the responsive posture."
      - url: "https://github.com/petekp/claude-code-setup/blob/main/skills/typography/SKILL.md"
        license: MIT
        fidelity: largely-derived
        took: "Weight compensation and font smoothing on dark grounds; the numeral-style decision table; dash and quotation-mark usage; minimum sizes and the dyslexia considerations; hierarchy built from size, weight, colour and case together; the clamp() and text-wrap patterns with the bordered-container caveat; and the common-mistakes inventory."
---

# Typography

Typography exists to serve the content. Structure — hierarchy, rhythm, the relationships between sizes — matters more than which typeface carries it, and it is decided first.

Get the audience, medium and register from `design-direction` before choosing anything here.

## Five foundations

Everything below follows from these. Where a decision is contested, the one that serves a foundation wins.

1. **Structure before typeface** (Vignelli). The grid, the hierarchy and the spacing relationships matter more than which face carries them. Choose size in relation to column width. On a printed page, two type sizes are usually enough — play small against large rather than adding steps.
2. **Design as programme** (Gerstner). Decisions emerge from stated criteria, not from feeling. The more exact and complete the criteria, the *more* creative the work becomes, because the remaining freedom is spent where it matters. Define the parameters, then select within them.
3. **Measure and rhythm** (Bringhurst). Every typographic decision is interdependent, and they resolve in one order. See below.
4. **Body text as anchor** (Brown). Body text is what makes every other decision easy. Set it first; scale everything else in relation to it.
5. **Invite, then disappear** (Rutter). Type draws the reader in and then gets out of the way. If the reader notices the typography while reading, it has failed — noticing is for the scan, not the flow.

## The dependency chain

Typographic decisions are not independent, and taking them out of order produces work that has to be redone. **Decide in this sequence, because each choice constrains the next:**

1. **Typeface** — its letterfit and x-height set what everything else must accommodate.
2. **Size** — chosen against the medium and reading distance, not from a default.
3. **Measure** — line length, which follows from size.
4. **Leading** — which follows from typeface, size *and* measure together.

Two consequences do most of the work:

- **Body text is the anchor.** Set it first and derive the rest from it. A system built from the display size down is arbitrary; one built from the reading size out is grounded in the only text most readers actually read.
- **The medium generates the system.** Page or viewport dimensions produce a baseline; the baseline produces body leading; leading produces body size; body size seeds the scale. Everything flows from one source rather than from a preference.

## Measure

| Context | Characters per line |
|---|---|
| Ideal, single column | 66 |
| Comfortable range | 45–75 |
| Multiple columns | 40–50 |

**If the measure is wrong, nothing else can fix the text.** Too long and the eye loses the return; too short and it breaks the line too often to hold rhythm. Measure is a function of size, so a caption and body text at the same width are not both correct.

## Leading

Leading is a *function*, never a fixed number:

- **Longer measures need more leading** — the return sweep needs help finding the next line.
- **Large x-heights need more leading**, and so do heavier weights. The familiar "sans-serifs need more than serifs" is a proxy for x-height and misleads on every face that breaks the correlation — a small-x-height sans needs less than a large-x-height serif. Read the x-height, not the classification.
- **Larger sizes need proportionally less.** Body around 1.45–1.5, headings 1.2–1.3, display 1.0–1.1 — these are starting points that follow from the rule, not values to apply unexamined.

Vertical space is measured in baseline multiples. Adding or removing space in arbitrary amounts breaks the rhythm that makes a page feel composed.

**Heading margins are asymmetric: more space above than below.** Two to three baselines above, zero to one below. This is what binds a heading to the content it introduces rather than letting it float between two blocks.

## The type scale

A scale has **three** properties, not two:

| Property | Controls |
|---|---|
| **f₀** — base size | Adapts the whole system to the medium |
| **r** — interval ratio | How dramatic the display-to-body contrast is |
| **n** — steps per interval | How many intermediate sizes exist |

Sizes are `fᵢ = f₀ × r^(i/n)`.

**This is why named ratios mislead.** Golden Ratio, Major Third and the rest are three-property scales with n=1, which welds hierarchy impact to palette density — you cannot ask for dramatic headings *and* a fine-grained set of intermediate sizes. Separating `r` from `n` gives independent control over both.

Choose `n` deliberately; it is a vocabulary. Fewer steps read stark and editorial, more steps read granular and documentary. Full derivation for print and screen, the temperament table, and the mapping from named ratios: [references/type-scale.md](./references/type-scale.md).

**Verify the scale against the rhythm.** Every size must produce a leading that is a whole multiple of the baseline. A scale that does not sit on the baseline is a second system fighting the first — adjust the size or drop that step. The rhythm is non-negotiable; the scale bends. Run [scripts/check-type.py](./scripts/check-type.py) `scale` rather than working it out by hand; it reports which steps survive snapping and which do not.

## Horizontal spacing

| Applies to | Adjustment |
|---|---|
| Lowercase at reading size and above | **Never letterspace it** |
| Capitals and small caps | Open up 5–10% |
| Large headings | Tighten 2–5% |
| Lowercase below reading size | Open up slightly — optical compensation, not letterspacing for effect |
| Sentences | One word space, never two |

All-caps always needs tracking, and stays short — a few words, never a paragraph.

## Choosing a typeface

**Read the face before judging it.** The five families exist for structural reasons, and knowing which one is in front of you explains what it will and will not do:

| Family | Stress | Stroke contrast | Serifs |
|---|---|---|---|
| Old Style | Diagonal | Moderate | Heavy, bracketed |
| Transitional | Nearer vertical | Greater | Sharper |
| Modern | Vertical | Extreme | Hairline, right-angled |
| Slab | Vertical | Low | Heavy, slab |
| Sans | None | Uniform | None |

**It classifies Latin text faces and nothing else.** There is no row for display, script or non-Latin faces, and it collapses humanist, grotesque and geometric sans into one — a distinction that matters more in practice than the serif/sans line does. The Sans row describes grotesques and geometrics; a humanist sans carries real stress and modulation and sets more like a serif.

Then work the evaluation in order, rather than reacting to the specimen:

1. **Identify the context** — audience, medium, purpose.
2. **Classify the face** — family and construction, per the table above.
3. **Evaluate the letterforms** — physical characteristics first, emotional register second.
4. **Test the rendering** — hinting, available weights, format support, and how it behaves at the sizes you will actually set.

A face that answers those is a better choice than a face that is fashionable.

**Restraint:** two families at most, and often one family across several weights is enough. Weight contrast within a single well-built family substitutes for pairing entirely. When pairing, pair for contrast and match x-heights so the two sit together at the same optical size.

**Do not reach for the default.** The faces that appear in AI output by reflex — see `design-direction`'s tell inventory — are chosen for safety, not fit. Where the project already has a typeface, that decision is made; match it.

## Hierarchy

Hierarchy is built from more than size. Size, weight, colour, case and space are five independent dimensions, and using two or three together produces clearer structure at lower cost than pushing size alone.

- **Three or four heading levels in practice.** Deeper nesting is usually a content-structure problem wearing a typographic costume.
- **Stay on the scale.** An arbitrary size to solve one awkward block undoes the system everywhere else.
- **Space is a hierarchy dimension.** Separation often does the work that a size jump was reaching for.

## Medium and reading distance

The same type at the same size is correct on a page, small on a screen at arm's length, and invisible projected. Reading distance is the constraint that changes across media, and it changes size, leading and weight together.

- **Screen:** rendering, hinting and available weights vary by platform; verify rather than assume. Use relative units so a reader's own size preference still works, and scale continuously with `clamp()` rather than stepping at breakpoints — see [references/web-typography.md](./references/web-typography.md).
- **Dark grounds make type look heavier.** Reduce weight a step on dark backgrounds, and avoid pure white on pure black — the halation makes it vibrate. Off-white on near-black reads better at the same measured contrast.
- **Print:** the physical page sets the baseline. Justified setting requires hyphenation; without it, expect rivers.
- **Projection:** sizing follows from room depth. `presentation` owns this.

## Gotchas

- **A type scale is not a type system.** Sizes without stated roles, leading and tracking get applied inconsistently the first time someone is in a hurry. Ship the complete package per level.
- **Never letterspace lowercase at reading size or larger.** It is the most common and most visible amateur tell, and no amount of it fixes a face that is wrong for the job. Below reading size is the one exception, and it is compensation rather than styling.
- **Justified text on screen is a defect** — but not for the reason usually given. `hyphens: auto` has been supported for years; the problem is that browsers break lines greedily, one at a time, with no lookahead and no way to hand-fix a bad break across every viewport width. The rivers cannot be removed. Set ragged-right.
- **Centred body text has no left edge to return to.** Centring is for short display lines only.
- **Do not fix contrast failures with weight.** Thin light-grey text made bold is still low contrast. Fix the contrast — see `colour`.

## Verification

Half of this is arithmetic and half is judgement. Run the arithmetic; do not restate it.

### Measured — run [scripts/check-type.py](./scripts/check-type.py)

Standard library, no install:

```bash
python check-type.py scale   --base 16 --ratio 2 --steps 5 --baseline 8
python check-type.py measure --char-ratio 0.48 "mobile=16/288" "desktop=18/640"
python check-type.py selftest
```

`scale` builds the scale from f₀, r and n, snaps each step's leading to the baseline, and reports where snapping left the leading outside the ratio its band asked for. `measure` reports characters per line at each size and container width — pass every breakpoint you ship, because a measure correct at one end of a fluid range is not evidence about the other. Both exit non-zero on a failure, so they also work as a build gate.

`--char-ratio` has no default on purpose: average character width is a property of the typeface, and handing over a number here would be the exact defaulting this skill exists to prevent. `measure --help` carries the browser snippet that measures it for your face.

**Paste the output; those tables are the verification artefact.** A ratio worked out in your head is not evidence, and neither is "the scale checks out".

### Judged — answer these in writing

The script cannot see any of these:

1. Is the leading right for *this* typeface — read its x-height, not its classification?
2. Can you scan the page and find the structure without reading it?
3. Are there two typefaces or fewer, and does each earn its place?
4. Is the rag clean — irregular, with no ladder, wedge or diagonal?
5. Are the incidental details right — quotes, dashes, numerals, no widows in prominent text?
6. Does it hold at the actual reading distance, in the actual medium?

## References

- [scripts/check-type.py](./scripts/check-type.py) — builds the scale, snaps each step's leading to the baseline and reports what survives; and reports characters per line across a fluid range. Emits markdown tables. Run it rather than estimating.
- [references/type-scale.md](./references/type-scale.md) — the three-property scale in full: deriving it from print and screen dimensions, the temperament table, and how named ratios map onto it.
- [references/web-typography.md](./references/web-typography.md) — the browser mechanisms for expressing the system: fluid type with `clamp()`, `text-wrap: balance` and `pretty`, OpenType features, dark-ground weight and smoothing, and webfont loading without layout shift.
- [references/craft-details.md](./references/craft-details.md) — the details that separate set type from typed text: quotation marks, dashes, numeral styles, widows and orphans, accessibility minimums, and non-Latin scripts.
