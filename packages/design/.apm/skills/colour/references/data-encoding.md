# Encoding Data by Colour

How to pick a colour scale for a chart, map, diagram or heatmap, and how to keep it readable for everyone.

## Contents

- [Pick the scale from the data](#pick-the-scale-from-the-data)
- [Categorical](#categorical)
- [Sequential](#sequential)
- [Diverging](#diverging)
- [The colour-vision floor](#the-colour-vision-floor)
- [Verification checklist](#verification-checklist)

## Pick the scale from the data

The data type decides the scale type. This is not a stylistic choice.

| Data | Scale | What varies |
|---|---|---|
| Nominal — categories with no order | **Categorical** | Hue, at roughly constant lightness |
| Quantitative, running one direction | **Sequential** | Lightness, monotonically, usually with hue drift |
| Quantitative with a real midpoint — zero, a target, a baseline | **Diverging** | Lightness from both ends toward a light or neutral middle |

Two errors account for most bad chart colour:

- **A sequential ramp on nominal categories.** A light-to-dark ramp asserts an order the data does not have, and readers will read that order as real.
- **Varied hue on ordered data.** Hue has no intrinsic sequence, so the order is destroyed and the reader must consult the legend for every value.

## Categorical

- **Eight is the demonstrated ceiling.** Okabe–Ito reaches eight and nothing reliably separates beyond it. Well before that the reader is doing legend lookup on every mark, so treat five or six as the working target and eight as the hard stop. Past it, group the tail into "other", split into small multiples, or encode by position instead.
- **Vary hue; hold lightness and chroma roughly constant.** A category that is darker than its neighbours reads as more important, which is a claim the data does not make.
- **"Roughly" is doing real work.** Identical lightness is fragile under colour-vision deficiency and collapses entirely in greyscale; a wide lightness range implies rank. A modest spread satisfies both.
- **Okabe–Ito is the reference standard** for a colour-vision-safe categorical palette — eight values including black, free to use, and the default in much of scientific publishing. Treat it as evidence of workable *intervals*, not as a house palette to paste in; check it against the actual ground and any brand constraint first.
- **Reserve a low-chroma neutral for "other" and "unknown"** so the residual category recedes rather than competing.

## Sequential

- **Lightness must be monotonic across the whole ramp.** Lightness carries the quantity. Hue drift is discriminability and colour-vision insurance, not the encoding.
- **Test the step size, not the appearance.** Perceptual distance between consecutive samples should be flat — plotted, a horizontal line. A bump is a region where the ramp exaggerates change the data does not contain, and a flat spot hides change it does.
- **Do not use rainbow or jet for magnitude.** Non-monotonic lightness manufactures boundaries where the data is smooth, hides real transitions elsewhere, and collapses under colour-vision deficiency. The countervailing evidence is real but narrow: from Ware (1988) to the 2023 review *Rainbow Colormaps Are Not All Bad*, rainbow ramps test **better for reading one value off a map**, because their strong colour categories work as an implicit legend. A direct label or an annotated contour wins that same task without the cost. Where shape, gradient or comparison is the point, monotonic lightness is not negotiable.
- **Multi-hue sequential beats single-hue for discriminability** (dark blue through green to light yellow). Prefer single-hue when the ramp must coexist with other colour encodings and needs to stay visually subordinate.
- **Bind direction to convention and state it.** More is darker on a light ground; flip for dark grounds, and let the legend say which.

## Diverging

- **Only where a midpoint is genuinely meaningful** — zero, a baseline, a target, a neutral state. Applying a diverging scale to data with no midpoint fabricates a "normal" the reader will believe.
- **Centre the domain on that midpoint.** An uncentred diverging scale misstates which side of the midpoint a value sits on. This is the most common and most serious diverging error, and it is invisible unless checked deliberately.
- Two hues, each monotonic in lightness from its end toward a light or neutral middle.
- **Do not use red-green.** It is the most common colour-vision collision, and a diverging scale is exactly where the collision is unrecoverable. Blue-orange and blue-red are the standard substitutes.

## The colour-vision floor

Red-green deficiency runs at roughly 8% of men of Northern European ancestry, 4–6% of East Asian and 2–3% of African populations, and about 0.5% of women throughout; deuteranomaly is the most common form. Blue-yellow deficiency is far rarer, monochromacy rarer still. **Quote the 8% only where the audience actually is Northern European** — elsewhere it overstates, and the design floor below holds regardless of the number.

- **Colour is never the sole encoding of anything the reader must distinguish.** This is the floor, not an enhancement. Add direct labels, shape, pattern, position or ordering.
- **Verify by simulation, per deficiency type** — deuteranopia and protanopia at minimum. A greyscale check tests lightness separation only and will pass palettes that collide.
- **Red-green semantics collide with the thing they encode.** Success-and-danger is the pairing charts most want and the one deficiency most affects. Pair it with shape or position, or move the *chart* to blue-orange and leave red-green to labelled UI states.
- **Downstream media compress the palette further.** If the artefact may be photocopied, printed mono, or projected, greyscale survival stops being a proxy check and becomes the real one.

## Verification checklist

- [ ] Scale type matches the data type
- [ ] Sequential and diverging ramps are monotonic in lightness, with even perceptual steps
- [ ] Diverging domain is centred on the real midpoint
- [ ] Categorical set is eight or fewer, implies no order, and has a modest lightness spread
- [ ] Simulated under deuteranopia and protanopia — `check-contrast.py cvd <colours>`, output pasted
- [ ] Survives greyscale, or the loss is deliberate and covered by another channel
- [ ] Every mark is distinguishable by something other than colour
- [ ] Fills meet 3:1 against their border rather than against each other — see the border trick in [SKILL.md](../SKILL.md#verify--never-eyeball)

---

Built on the openly published research behind ColorBrewer (Cynthia Brewer), the Okabe–Ito colour-vision-safe palette, and the viridis/viscm design rationale. The rainbow position weighs Borland and Taylor's *Rainbow Color Map (Still) Considered Harmful* (2007) against Ware et al., *Rainbow Colormaps Are Not All Bad* (IEEE CG&A, 2023) and Gołębiowska and Çöltekin's review of the empirical evidence (2022). Nothing from those sources is reproduced here.
