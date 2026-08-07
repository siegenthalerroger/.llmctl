# Web Typography

The mechanisms the browser provides for expressing a derived type system, and the ones that quietly undo it.

## Contents

- [Fluid type with clamp()](#fluid-type-with-clamp)
- [Line breaking](#line-breaking)
- [OpenType features](#opentype-features)
- [Dark grounds](#dark-grounds)
- [Loading and fallback](#loading-and-fallback)
- [Responsive discipline](#responsive-discipline)

## Fluid type with clamp()

`clamp(min, preferred, max)` interpolates a size continuously across the viewport instead of stepping it at breakpoints. This is how the two-endpoint scale derivation in [type-scale.md](./type-scale.md) gets expressed:

```css
body { font-size: clamp(1rem, 0.95rem + 0.25vw, 1.125rem); }
h1   { font-size: clamp(2rem, 1rem + 4vw, 4rem);
       line-height: clamp(1.1, 1.3 - 0.1vw, 1.3); }
```

Two rules keep it honest:

- **Clamp leading alongside size.** Size that scales while line-height stays fixed breaks the ratio at one end of the range and usually both.
- **Ship a complete package per level**, not a lone `font-size` — size, leading and tracking travel together, because separating them is how a level gets applied inconsistently.

Always include a `rem` term in the preferred value (`1rem + 4vw`, never bare `4vw`). A pure viewport unit ignores the reader's own text-size setting, which fails WCAG 1.4.4 and overrides a deliberate accessibility choice.

## Line breaking

```css
h1, h2, h3, blockquote, figcaption { text-wrap: balance; }
p, li                              { text-wrap: pretty; }
```

- **`balance`** evens line lengths across short blocks — the mechanism behind "no single trailing word in a heading". Browsers cap it at a handful of lines, so it is for headings and pull quotes, not body copy.
- **`pretty`** targets the last line, suppressing orphans in running text at far lower cost.
- **Do not use `balance` inside a bordered or tightly constrained container.** Centring the ragged edge inside a visible box reads as misalignment rather than balance.

Justified setting still does not work here — see the main skill. `text-wrap` does not add lookahead to line breaking.

## OpenType features

The face usually already contains what people fake with markup:

- `font-variant-numeric: tabular-nums` wherever digits align in columns or update in place, `oldstyle-nums` for editorial body text.
- `font-variant-caps: small-caps` for real small caps — CSS-synthesised ones are just shrunken capitals with wrong weight.
- `font-feature-settings` for ligatures, alternates and fractions where the face provides them.

Faking a feature the face already has is the most common way typographic detail goes wrong on the web.

## Dark grounds

Type looks heavier on a dark ground, so the system compensates rather than reusing light-mode values:

```css
@media (prefers-color-scheme: dark) {
  body { font-weight: 350; }          /* rather than 400 */
  h1, h2, h3 { font-weight: 600; }    /* rather than 700 */
}
```

- **Drop roughly half a weight step**, not a full one — the correction is for perceived weight, and overshooting makes text look thin and fragile.
- **Antialiasing helps on dark grounds** (`-webkit-font-smoothing: antialiased`, `-moz-osx-font-smoothing: grayscale`) because subpixel rendering exaggerates the same perceived boldness. Apply it to the dark context only; it degrades light-ground text.
- **Never pure white on pure black.** Off-white on near-black reads better at the same measured contrast — the halation on the pure pair makes it vibrate. Contrast values belong to `colour`.

## Loading and fallback

- **Match the fallback's metrics**, using `size-adjust`, `ascent-override` and `descent-override` on an `@font-face` for the fallback family. Without it the page reflows when the webfont arrives, which is a layout shift the reader is charged for.
- **`font-display: swap`** shows text immediately in the fallback. `optional` is better where the shift matters more than the face.
- **Subset to the characters actually used**, and verify the subset still covers the languages in the content — a Latin subset silently drops the diacritics that [craft-details.md](./craft-details.md) warns about.

## Responsive discipline

- **Size, measure and leading change together.** Changing one alone breaks the other two; this is the dependency chain, applied per viewport.
- **Prepare ranges and boundaries, not fixed values.** The system states the limits within which the type is correct and lets the medium resolve the rest — suggestion over decision.
- **Diagnose typographic pressure.** When a block feels wrong, name which of size, measure or leading is out of range before adjusting anything. Adjusting by feel moves all three and fixes none.
