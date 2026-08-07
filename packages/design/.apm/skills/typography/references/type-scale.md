# The Type Scale

How to build a size scale that is derived rather than picked, and how to make it sit on the vertical rhythm.

## Contents

- [Three properties, not two](#three-properties-not-two)
- [Temperaments — choosing n](#temperaments--choosing-n)
- [Named ratios, translated](#named-ratios-translated)
- [The morphological box](#the-morphological-box)
- [Deriving the scale from print](#deriving-the-scale-from-print)
- [Deriving the scale from a screen](#deriving-the-scale-from-a-screen)
- [The verification step](#the-verification-step)

## Three properties, not two

Any typographic scale is defined by three independent values, exactly analogous to a musical scale:

| Property | Musical equivalent | Typographic meaning |
|---|---|---|
| **f₀** — fundamental | Concert pitch | Base size, from which everything derives |
| **r** — interval ratio | The octave (2× frequency) | The display-to-body relationship |
| **n** — notes per interval | 12 chromatic, 7 diatonic, 5 pentatonic | How many sizes exist between doublings |

```text
fᵢ = f₀ × r^(i/n)
```

The classical printer's scale — 6, 7, 8, 9, 10, 11, 12, 14, 16, 18, 21, 24, 36, 48, 60, 72 — is this formula with f₀ = 12pt, r = 2, n = 5, giving a step ratio of ⁵√2 ≈ 1.1487. The historical sequence carries small errors against the maths: 11pt is an extra note, 42pt is missing from the 10→21→42→84 progression, and 30 and 60 sit halfway between proper steps.

**Why the third property matters.** Two-property tools give you a base and one ratio, which welds two unrelated decisions together:

- The Golden Ratio (1.618) yields 1em → 1.618em → 2.618em. Three sizes before doubling, with jumps too large to build a nuanced hierarchy from.
- A Minor Second (1.067) yields many sizes, all too close together to read as distinct levels.

With `r` and `n` separate, **`r` controls how dramatic the hierarchy is and `n` controls how many sizes you have to work with.** You can have a strong display-to-body contrast *and* a fine-grained set of intermediate steps. With one ratio you must trade one for the other.

## Temperaments — choosing n

The number of steps per interval is a design vocabulary, not a technicality:

| n | Character | Suits |
|---|---|---|
| 2 | Stark, minimal | Posters, bold editorial |
| 3 | Decisive | Marketing pages, landing pages |
| 4 | Balanced | General editorial |
| 5 | Classical, rich | Long-form publishing, books |
| 6+ | Granular | Complex documents, data-dense interfaces |

Pick `n` from how many distinct levels the *content* actually has. A document with three kinds of heading does not need a hexatonic scale, and giving it one guarantees the extra steps get used arbitrarily.

## Named ratios, translated

The familiar named ratios are three-property scales with n = 1. They remain useful shorthand — they are just not the full picture:

| Named ratio | Value | Equivalent |
|---|---|---|
| Augmented Fourth | 1.414 | = r = 2, n = 2 (exactly √2) |
| Major Third | 1.250 | ≈ r = 2, n = 3 (exactly ³√2 = 1.2599) |
| Classical step | 1.1487 | = r = 2, n = 5 (exactly ⁵√2) |

The pattern: a named ratio is the step ratio, so `n` is however many of those steps fit in a doubling — `n = log(2) / log(ratio)`. [scripts/check-type.py](../scripts/check-type.py) computes it, and its `selftest` holds this table to the arithmetic.

Note that the classical "two sizes on a page, play large against small" doctrine is simply r = 2. The doubling *is* the interval; `n` then decides how many intermediate sizes are permitted between the two.

Ratios are starting points. Set the scale, then look at it — a computed size that reads wrong at the actual size is wrong, and the scale bends before the reader does.

## Deriving the scale from print

Bottom-up, because the physical page is the fixed constraint:

1. **Page dimensions → fitted baseline.** Divide the page height by a whole number of rows so the baseline divides the page exactly.
2. **Fitted baseline = body leading.**
3. **Body size = leading ÷ target line-height ratio** (roughly ÷1.4 for a serif, ÷1.5 for a sans).
4. **That body size is f₀.**
5. **Choose r and n**, then apply `fᵢ = f₀ × r^(i/n)`.
6. **Verify** every resulting size against the baseline — see below.

## Deriving the scale from a screen

The viewport is a range rather than a fixed dimension, so the scale is derived twice and interpolated:

1. Define the viewport range you are designing across.
2. Choose the body size at each end of that range.
3. Body leading = size × line-height ratio, at each end.
4. Apply the three-property scale at each end independently.
5. Interpolate each step between its two endpoints so type scales continuously rather than jumping at breakpoints.

Size, measure and leading all change together as the viewport changes. Changing size alone breaks the measure, which breaks the leading.

## The morphological box

Gerstner's method for working systematically instead of by association: list every parameter and its available treatments, then select across rows.

| Parameter | Options |
|---|---|
| Typeface | Serif, sans, slab, monospace |
| Size | Scale positions — body, small, large, display |
| Weight | Light, regular, medium, bold, black |
| Width | Condensed, normal, extended |
| Style | Roman, italic, oblique |
| Spacing | Tight, normal, loose |
| Alignment | Left, centred, right, justified |
| Colour | Primary text, secondary, accent, muted |
| Case | Lowercase, uppercase, small caps, title case |

Two things this buys. It makes the *unused* dimensions visible — most weak type systems push size and ignore width, case and colour entirely. And it converts "what should this look like" into a finite set of selections, which is the difference between a system and a preference. Fill the box before setting anything; the combinations you rule out are as much a decision as the ones you keep.

## The verification step

**This is the step that gets skipped, and skipping it is what makes a system feel loose.**

Every size in the scale must produce a leading that is a whole multiple of the baseline unit — 1×, 2×, 3×, 4×. Where a computed step does not, adjust that size or drop the step entirely.

A type scale that does not land on the baseline grid is two independent systems in the same document, and the conflict shows up as vertical drift that accumulates down the page. The baseline is non-negotiable; the scale bends to serve the rhythm.

---

The three-property model is Spencer Mortensen's ("The Typographic Scale"). The classical scale, the dependency order and the measure ranges are Bringhurst's *The Elements of Typographic Style*; body-text-as-anchor is Tim Brown's. Cited, not reproduced.
