# Craft Details

The details that separate set type from typed text. None of them are noticed when right; all of them are noticed when wrong.

## Contents

- [Quotation marks and apostrophes](#quotation-marks-and-apostrophes)
- [Dashes](#dashes)
- [Numerals](#numerals)
- [Widows, orphans and rags](#widows-orphans-and-rags)
- [Accessibility minimums](#accessibility-minimums)
- [Non-Latin scripts](#non-latin-scripts)
- [Common mistakes](#common-mistakes)

## Quotation marks and apostrophes

Use typographic (curly) marks, not the straight vertical ones inherited from typewriters: `"` `"` `'` `'`, not `"` and `'`.

The apostrophe is always the closing single mark — `it's`, `'90s` — which matters because naive auto-correction turns a leading apostrophe into an *opening* mark and gets `'90s` wrong.

Straight marks are correct in exactly one place: inside code, where they are syntax rather than punctuation.

## Dashes

| Mark | Character | Use |
|---|---|---|
| Hyphen | `-` | Compounds, word breaks at line ends |
| En dash | `–` | Ranges (2020–2024), relationships and connections |
| Em dash | `—` | Parenthetical breaks in a sentence |

House style decides whether em dashes are set closed (`word—word`) or with hairline spaces. Pick one and hold it.

An en dash for a range replaces the word "to", so "from 2020–2024" is wrong — either "from 2020 to 2024" or "2020–2024".

## Numerals

Numeral style is a real decision, and the default is frequently the wrong one:

| Style | Use where | Why |
|---|---|---|
| **Tabular** | Tables, prices, any column of figures, timers | Fixed width, so digits align vertically and do not shift as values change |
| **Proportional** | Running prose | Spaced like letters, so numbers do not punch holes in a line of text |
| **Old-style** | Editorial and long-form body text | Varying height and descenders, so figures sit in the line rather than shouting from it |
| **Lining** | Headings, all-caps settings, interfaces | Uniform cap-height, matching the surrounding capitals |

Two more worth setting deliberately:

- **Slashed or dotted zero** in code, data, and anywhere a zero could be read as a capital O.
- **Fractions and superiors** where a face provides them, rather than faking them with smaller type and a slash.

Anywhere digits update in place — a dashboard, a counter, a clock — tabular figures are not a preference. Without them the layout twitches on every change.

## Widows, orphans and rags

- **Widow** — a lone word or short line ending a paragraph. Most visible in prominent text: headings, pull quotes, captions.
- **Orphan** — an opening line stranded at the foot of a column or page.
- Both are worth fixing in display and prominent text always, and in long-form body text where the medium lets you.

**Rag quality** is a real property of ragged-right setting. A good rag is irregular without forming shapes — no ladder of repeated line lengths, no wedge, no accidental diagonal. Hyphenation improves rags; it is not only for justified text.

Balance headings across their lines rather than leaving a single trailing word.

## Accessibility minimums

| Element | Minimum | Preferred |
|---|---|---|
| Body text | 16px equivalent | 16–18px |
| Secondary text | 14px | 14–16px |
| Legal and caption | 12px | 12px plus opened tracking |

- **Use relative units** so a reader's own size preference still applies. A fixed pixel size overrides an accessibility setting the reader deliberately chose.
- **Contrast belongs to `colour`** — but note that thin weights and small sizes need *more* contrast than the nominal floor, because the measured ratio assumes solid strokes.
- **Dyslexia:** avoid justified setting, prefer faces with distinguishable letterforms (`a`/`α`, `l`/`1`/`I`, `rn`/`m`), and give generous leading and paragraph spacing. These help every reader, so they are not a special mode.
- **Never underline text that is not a link** on screen. The underline is a learned affordance and borrowing it for emphasis costs the reader a wasted click.

## Non-Latin scripts

- **Never letterspace Arabic.** The script is connected; tracking breaks the joins and renders words wrong rather than merely ugly.
- **Right-to-left scripts** invert layout direction, not just text alignment — mirrored margins, indents, and the reading order of adjacent elements.
- **CJK** has no word spaces and different line-breaking rules; measure in characters per line does not transfer, and leading needs are greater at the same nominal size.
- **Vertical metrics differ by script.** A face that sets Latin comfortably may clip diacritics in Vietnamese, Czech or Polish. Check with real text in the actual languages.

## Common mistakes

- All-caps used for body text or a long heading
- Centred body paragraphs
- Lines running past 80 characters
- More than two typeface families
- Decorative faces used for interface text
- Justified setting on screen
- Letterspaced lowercase
- Arbitrary sizes that are not on the scale
- Missing fallback faces, or layout shift while a webfont loads
- Inconsistent heading levels — skipping from level two to level four
