---
name: "colour"
description: "Derives colour palettes from perceptual reasoning — lightness, chroma and hue as separable axes — rather than from named harmony rules or handed-over values, and covers how colours alter each other in combination and what a combination makes a viewer feel. ALWAYS invoke before choosing, naming, adjusting or judging any colour, palette or colour token, and when encoding data by colour. Owns colour-vision-deficiency and contrast verification for every medium; it does not cover layout, type, print production or projection. Do not pick a hex value, apply a complementary or triadic scheme, or eyeball a contrast ratio without this skill. Keywords: colour, color, palette, hue, chroma, saturation, lightness, contrast, accessibility, colour blindness, OKLCH, accent, neutrals, theme, dark mode."
metadata:
  provenance:
    adaptedFrom:
      - url: "https://github.com/meodai/skill.color-expert/blob/main/SKILL.md"
        license: CC-BY-4.0
        fidelity: largely-derived
        took: "The hue-first-harmony debunk and the character-first finding that chroma and lightness predict emotional response better than hue; the chroma/saturation/lightness/brightness distinctions; the space-per-task selection table; HSL's three non-perceptual axes with the yellow-versus-blue lightness example; gamut clipping resolved by reducing chroma rather than clamping channels, and that CSS gamut-maps automatically where code does not; the WCAG and APCA pass-rate figures over all sRGB pairs; the 60-30-10 dominance shorthand; reference-to-semantic-to-component token layering with the encode-the-decision vocabulary and token graph; the CSS Color 4/5 feature set; and Ström's border trick for chart fills."
      - url: "https://github.com/Myndex/apca-w3"
        license: W3C-20150513
        fidelity: inspiration-only
        took: "The published APCA-W3 0.1.9 G-4g constants -- transfer exponent, luminance coefficients, both polarity exponent pairs, the black soft-clamp, scale, offset and clip thresholds -- plus the guidance-level bands, reimplemented in scripts/check-contrast.py. Not a line-for-line base: no upstream code was read across, and the comparison target is the constants in `SA98G`, not the file. Tracked here rather than on the script because the provenance parser reads .md only; the licence obliges implementations to keep current, which is what the drift audit on this URL is for."
---

# Colour

Derives colour from the brief rather than carrying one. **This skill ships no palette.** Every value in the output traces to a decision made here, to something the project already had, or to what the user asked for.

Colour choice is downstream of direction — get the audience, medium and register from `design-direction` first.

## The three axes

Reason in **OKLCH**, where lightness, chroma and hue move independently. Changing one there leaves the other two intact, which is what makes derivation possible at all.

| Axis | Is | Does the work of |
|---|---|---|
| **Lightness** | Perceived reflectance against a similarly lit white | Legibility, hierarchy, depth |
| **Chroma** | Colourfulness relative to a neutral of the same lightness | Intensity, energy, mood |
| **Hue** | Position on the colour circle | Identity and recognition — and less else than assumed |

Two more terms get used as if they were the ones above, and are not:

- **Saturation** — colourfulness relative to the colour's *own* brightness. A dark saturated blue still reads muted. Same chroma ≠ same saturation; they are different dimensions and move independently.
- **Brightness** — perceived intensity of light coming from the stimulus, as against lightness, which is judged relative to a similarly lit white.

### OKLCH is the default, not the only answer

| Task | Space | Why |
|---|---|---|
| Perceptual manipulation, scales, ramps | **OKLCH** | Best uniformity across L, C, H; fixes CIELAB's blue problem |
| Mixing and gradients | **OKLab** | No grey mid-gradient the way sRGB and HSL produce |
| Gamut-aware picking | **OkHSL / OkHSV** | Cylindrical like HSL but perceptually grounded |
| Saturation normalised 0–100% per hue | **HSLuv** | CIELUV chroma normalised by hue and lightness |
| Print | **CIELAB D50** | The ICC standard illuminant |
| Matching appearance across media or lighting | **CAM16** | Models surround, adaptation and viewing conditions |
| High dynamic range | **Jzazbz / ICtCp** | Built for extended range; OKLab is not |
| Colour difference, precision | **CIEDE2000** | The reference metric |
| Colour difference, quick | **Euclidean in OKLab** | Close enough for palette separation work |
| Colormap uniformity | **CAM02-UCS** or OKLab | CIELAB is poor for *nearby* colours, which is what even sampling depends on |

Reach past OKLCH deliberately. Naming the space is part of stating the decision.

### Why HSL misleads

HSL is a geometric rearrangement of RGB, not a perceptual model. Three failures matter:

- **Its lightness is arithmetic.** `hsl(60 100% 50%)` and `hsl(240 100% 50%)` share L=50%; the yellow is dazzling and the blue is nearly black.
- **Its hue circle is unevenly spaced.** 20° near red is a dramatic shift; 20° near green is barely visible.
- **Its saturation does not track perceived saturation.**

Consequence: a ramp built by stepping HSL lightness has uneven perceived steps and muddy mid-tones, and interpolating between two colours through sRGB or HSL greys out the middle. Interpolate in a perceptual space.

### Gamut

Asking for more chroma than exists at a given lightness and hue does not error — it clips, usually duller *and* hue-shifted. **Fix it by reducing chroma, holding lightness and hue.** Clamping RGB channels instead shifts the hue and destroys the colour's identity.

Three consequences that decide where the bug appears:

- **CSS gamut-maps for you; code does not.** Browsers map `oklch()` and `color()` automatically, so authored CSS rarely clips badly. A hand-rolled `oklch → hex` conversion just truncates channels. The same palette can be correct in the stylesheet and wrong in the script that generated it.
- **Test against the actual target gamut.** A colour that is valid in Display-P3 still clips in sRGB. "In gamut" is meaningless without saying which.
- **Or remove the failure by construction** — express chroma *relative to the gamut boundary* at that lightness and hue, so a value that does not exist cannot be requested.

## What creates feeling

> **Named harmony schemes predict almost nothing you care about.** Complementary, triadic and tetradic are hue-angle recipes, and hue angle alone forecasts neither mood, nor legibility, nor contrast compliance. The deeper problem is geometric: the volume of realisable colour differs at every hue, so two values 180° apart are not two equally-weighted colours — they are whatever their two hue planes happened to allow.

State this to yourself before every palette, because the default behaviour — absorbed from training data — is to reach for the colour wheel and treat the result as justified.

**Chroma and lightness predict emotional response more reliably than hue does.** Organise by *character* — pale, muted, deep, vivid, dark — before touching hue. A muted palette reads calm across many different hues; a vivid one reads energetic across many different hues. Relaxed versus intense is a chroma-and-lightness question.

This is measured, not asserted: Valdez and Mehrabian (1994) found brightness and saturation carried most of the variance in rated pleasure and arousal while hue effects stayed weak, and Ellen Divers' Colour Character Compass builds design practice on the same result. Both rest on Western samples — treat the *character* axis as the durable finding and any particular reading as audience-dependent.

This is the hinge that makes the skill steerable:

- A brief saying "calm", "premium", "urgent", "playful" is a **character** instruction. Pick the character band first.
- Hue then comes from the *subject* — its materials, place, era, vernacular — not from a mood-to-hue table.
- Two projects can both be correctly "calm" in completely unrelated hues.

Where hue does carry meaning it is cultural and contextual, never universal. Red is danger in one setting and prosperity in another. **Never assert a universal hue-to-emotion mapping.** If the association matters, derive it from the stated audience.

## How colours change each other

A colour has no fixed appearance. The same value looks lighter against a dark ground, darker against a light one, and shifts in hue away from whatever surrounds it — simultaneous contrast, the substance of Albers' *Interaction of Color*. Four consequences do real work:

- **Never judge a swatch in isolation.** Evaluate it at the size, and against the ground, it will actually occupy.
- **Small areas need more chroma than large ones** to read as the same colour. An accent covering 5% of a page and a background at the identical value will not feel identical.
- **A dark theme is re-derived, not inverted.** Flipping lightness makes saturated colours glare and neutrals go muddy. A hue that sits well on white usually needs more lightness and less chroma to sit on near-black.
- **A palette is a system of intervals, not a set of swatches.** Adding a colour changes every colour already in it.

**Dominance must be unambiguous.** The 60-30-10 shorthand — a dominant colour over roughly 60% of the surface, a secondary at 30%, an accent at 10% — is a starting distribution rather than a law. What it protects against is three colours at equal weight fighting for the same rank. Hold the ranking; move the ratio to suit the work.

## Deriving a palette

Order matters; each step constrains the next.

1. **Ground first.** Light, dark, or a tinted neutral. Everything after is judged against it.
2. **Neutrals second**, biased toward the accent hue by a small amount of chroma. A pure neutral reads unconsidered; a biased one reads chosen. Step lightness in even perceptual intervals.
3. **Accent third — one, at most two.** Beyond two, hierarchy collapses. A third "accent" is almost always a semantic colour in disguise.
4. **Semantic colours held apart from the accent.** Success, warning and danger are reserved before brand spends them. If the brand accent is red, danger cannot also be red.
5. **Assign roles, never raw values, at the point of use.** Emit `surface`, `on-surface`, `accent`, `danger`. A palette that is regenerated must not require rewriting whatever consumes it. **Emit the rule, not the frozen result** — `text := bestContrastWith(surface, palette)` survives a palette change; a hex pasted into a component does not. See [references/implementation.md](./references/implementation.md).

If you cannot say what each value is *for*, you have swatches rather than a palette.

## Verify — never eyeball

Measure every pair, in every theme, before shipping. A colour looking fine in the render you just produced is not evidence, and neither is a ratio you calculated in your head.

Run [scripts/check-contrast.py](./scripts/check-contrast.py) — standard library, no install:

```bash
python check-contrast.py pair "body=#4a4a4a/#ffffff" "link=#0b5/#fff"
python check-contrast.py cvd  "#e69f00" "#56b4e9" "#009e73" "#cc79a7"
python check-contrast.py selftest
```

`pair` prints WCAG 2 and APCA side by side and exits non-zero on a WCAG failure, so it also works as a build gate. `cvd` simulates each colour under protanopia, deuteranopia and tritanopia and ranks how close the nearest pair ends up — the check greyscale cannot perform. **Paste the output; that table is the verification artefact.**

`pip install coloraide` is optional and worth it: input then accepts any CSS colour, including `oklch()` and Display-P3, so a value derived in OKLCH can be checked without converting it by hand first. It also composites alpha over the background instead of ignoring it — a 50%-opacity black on white measures 3.95:1 and fails, where treating it as opaque black reports 21:1 and passes. `selftest` verifies the maths against published values, and against coloraide as a second implementation when it is installed.

- **Contrast.** Measure with both, because they fail in different places. WCAG 2 is the testable standard, but its ratio **overstates contrast near black** — a dark-theme pair can clear 4.5:1 and still be unreadable. APCA is polarity- and size-aware: stricter than WCAG for body text, more permissive for large or ancillary elements. It is not uniformly the harsher of the two. Satisfy WCAG because that is what gets audited, and treat an APCA shortfall as a real defect rather than a difference of opinion.
  Both thresholds are harder to hit than intuition suggests. Brute-forced across all ~281 trillion sRGB pairs:

  | Threshold | Pairs passing |
  |---|---|
  | WCAG 3:1, large text | 26.5% — about 1 in 4 |
  | WCAG 4.5:1, AA body | 12.0% — about 1 in 8 |
  | WCAG 7:1, AAA | 3.6% — about 1 in 27 |
  | APCA Lc 60 | 7.3% — about 1 in 14 |
  | APCA Lc 75, fluent reading | 1.6% — about 1 in 64 |
  | APCA Lc 90, preferred body | **0.08% — about 1 in 1,250** |

  This is why a palette cannot be picked and then checked. At the tiers real body text needs, almost nothing passes by luck, so contrast has to be a constraint during derivation rather than a gate after it.

- **Colour-vision deficiency.** Simulate it, per deficiency type. Red-green deficiency affects roughly 8% of men of Northern European ancestry — the figure usually quoted — appreciably fewer elsewhere, and about 0.5% of women. **A greyscale check is not a CVD check.** It tests lightness separation only; two hues can separate well in greyscale and still collide under deuteranopia.
- **Greyscale as its own check.** If the design collapses when desaturated, it is encoding meaning in hue alone.
- **When a required distinction cannot be made to pass, add a channel** — shape, position, a direct label, a border — rather than pushing chroma further.

**Chart fills: use the border trick.** Holding 3:1 between three chart fills *and each other* is very hard; past three it is effectively impossible, because the number of pairs to satisfy grows as N². Put a border on the marks and require 3:1 between each fill and the border instead — one constraint per colour rather than N². (Matt Ström, *How to pick the least wrong colors*, 2022.)

**Emit the check; do not claim it.** "Contrast verified" with no numbers is indistinguishable from not having checked, which is how this step gets skipped.

## Gotchas

- **"Make it pop" is a contrast request, not a chroma request.** Raising chroma everywhere lowers the contrast between things. Prominence comes from restraint around the thing, not from intensity applied to it.
- **Accessibility floors are not style.** They hold at every register and in every theme. A palette that only passes in light mode is unfinished, not "light-mode-first".
- **Do not spend a semantic hue on brand.** It is cheap to reserve up front and expensive to reclaim once the accent is established.
- **Neutral is a decision.** A pure grey is the same kind of default as an unconsidered typeface — pick the bias deliberately, including when the answer is genuinely neutral.
- **Print and projection are out of scope here.** Print gamut is knowingly uncovered by this package; projection washout belongs to `presentation`, which owns that medium.

## References

- [scripts/check-contrast.py](./scripts/check-contrast.py) — measures WCAG 2 ratio and APCA Lc for text pairs, and simulates protanopia, deuteranopia and tritanopia to rank palette separation. Emits markdown tables. Run it rather than estimating.
- [references/implementation.md](./references/implementation.md) — getting a derived palette into code without it rotting: reference/semantic/component token layering, encoding the decision rather than its frozen result, the token graph, and the CSS Color 4/5 syntax that keeps derivations live in the browser.
- [references/data-encoding.md](./references/data-encoding.md) — encoding data by colour: categorical, sequential and diverging scales, when each applies, and the colour-vision-safe floor. Load this for any chart, map, diagram or heatmap. **Nothing else in this package covers it.**
