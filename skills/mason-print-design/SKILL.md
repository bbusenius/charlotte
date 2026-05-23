---
name: mason-print-design
description: Create print-ready educational materials (worksheets, copywork sheets, maps, flashcards, narration pages, nature-notebook pages, certificates) using HTML/WeasyPrint or SVG/Inkscape. Use this skill when the user asks to render homeschool materials intended for print, PDF, or tablet display.
---

This skill guides creation of print-ready educational materials that render correctly when converted to PDF or PNG. It covers worksheets, copywork sheets, maps, flashcards, picture-study and composer cards, nature-notebook pages, timelines, narration templates, vocabulary cards, memory-verse cards, and related printables. Output is suitable for home printing or tablet display.

## Aesthetic Guidelines

**Invoke the `mason-aesthetics` skill alongside this one.** It owns the project's aesthetic point of view (typography, color, illustration style, layout, decoration, language on the page, printability and atmosphere tests). This skill is about getting the rendering right; `mason-aesthetics` is about what "right" looks like.

If `mason-aesthetics` is unavailable for any reason, fall back to:

- A calm, considered aesthetic suited to a home full of living books
- Classical serifs for body text; no Comic Sans, no stylized cursive for beginners
- Ink-on-paper palettes; no neon or rainbow gradients
- Illustration styles drawn from pen-and-ink, watercolor, botanical plate, or vintage textbook traditions
- Hierarchy that serves the learner's eye, not novelty for the designer's sake

## Default Behavior: PDF First

When the user doesn't specify an output format, **default to HTML + WeasyPrint for PDF output**. PDF travels well between tablet and printer, stays searchable, and is the most common expectation. Only switch to SVG/Inkscape if:

- The design requires effects WeasyPrint can't render (glows, shadows, complex filters)
- HTML has been attempted and PDF output has rendering issues
- The user explicitly requests PNG or SVG output
- The material is fundamentally graphical (a map, a diagram, a decorative card) and SVG is the natural source format

## Vector Text — Default, with a Carve-Out for Lettering-as-Art

**Default rule: all text is rendered as proper vector text in the final PDF, not baked into a generated image.**

**Correct default approach:**

1. Generate an image that is decorative / background / illustration only — no text in the image
2. Create HTML with that image placed in the composition
3. Add **all text in HTML** — titles, copywork passages, prompts, captions
4. Convert to PDF — text is proper vector, searchable, legible at any scale

**Why this matters for educational materials:**

- Vector text stays sharp at every print size and every tablet zoom
- Text is searchable and selectable (useful for indexing materials in a future lesson-plan builder)
- Text can be edited without regenerating images
- Proper typographic control (kerning, leading, font choice) — important for copywork and early-reader legibility
- Home-printer ink economics: vector text prints crisp even on faded cartridges

**When generating images, prompt for:**

- "Illustration of [subject] — no text, no lettering, no captions"
- "Decorative [subject] — leave clear space for title and caption overlay"
- "Botanical plate of [subject], no labels"

### Carve-out: when the lettering *is* the art

A strict vector-only rule is a poster convention; it's not always right for educational materials. Allow baked-in text when the lettering is part of the artistic intent, not merely *text* that happens to sit inside an image:

- Hand-lettered memory-verse wall cards where the calligraphy is the point
- Illuminated decorative initials at the head of a copywork passage
- Painted or chalked style banners on a themed wall card
- Calligraphic practice models (the child is observing letterforms — the letterforms *are* the material)
- A hand-drawn map label rendered in a period hand for historical atmosphere

The test: would the material be meaningfully diminished if the lettering were swapped for a vector font? If yes, baked-in lettering is warranted. If no, keep text in HTML/SVG. When in doubt, default to vector.

## Typography Sizing

Material type drives size more than length does. Sizes assume letter-size (8.5 × 11") unless noted.

**Copywork sheets (for children):**

- Passage text: **24–36pt** for early readers (Level 1–3), **18–24pt** for mid-grade (Level 4–6), 14–18pt for older
- Line-height must give the child room to write beneath or between lines; typical pen-ruled spacing is 1/2" for beginners, 3/8" mid-grade, 1/4" older
- Instruction line ("Copy this passage in your best hand."): 12–14pt, set modestly below the passage

**Flashcards / vocabulary / memory-verse cards:**

- Front-of-card term or verse: 48–96pt depending on length
- Definition / reference / back-of-card text: 18–28pt
- Multiple cards per sheet: size down to fit cleanly inside each card's bleed area

**Narration templates:**

- Title/prompt: 18–24pt
- Writing lines: leave space, not size — the material is the blank
- Illustration frame label (e.g. "Draw what you saw:"): 12–14pt, unobtrusive

**Math / phonics / handwriting practice:**

- Problem text: 18–28pt (bigger for earlier grades)
- Directions: 14–16pt
- Practice rows or boxes sized to the grade's hand

**Picture-study / composer / nature-study cards:**

- Subject name: 20–28pt
- Caption or identification details: 12–16pt

**Posters / wall cards / larger-format materials:**

- Headlines: scale to fit; use 96–144pt for short headings, 60–84pt for medium headings, and 48–60pt for long headings
- Supporting lines: 20–36pt depending on hierarchy

**Always verify text fits within the page bounds.** Overflow is never acceptable on a child-facing material. If text doesn't fit, reduce size; if still cramped, reduce content or reflow. The page must be calm to read.

## Layout: Tablet-Friendly and Printable Both

Materials are frequently *displayed* on a tablet, not printed. Design for both:

- **Full bleed is fine** when it suits the material (picture-study cards, wall cards, atmospheric copywork sheets). The margin default from print-poster work is not mandatory here.
- **Print-safe zone** still matters for anything that *will* be printed on a home printer — leave 0.25–0.5" unprinted at the edges or accept that home printers may clip.
- **Landscape orientation** is often right for tablet display and for two-page spreads (timelines, maps). Don't default to portrait by reflex.
- **Aspect-ratio awareness:** if the material is primarily for a 16:10 or 4:3 tablet, design the page at that ratio rather than stretching a letter-sized sheet.

## Choose Your Approach

### Approach 1: HTML + WeasyPrint (for PDF output)

**Best for:** text-heavy materials, copywork, worksheets, multi-card sheets, narration pages, documents.

**WeasyPrint CSS limitations** — these properties are ignored:

- `box-shadow` — will not render
- `text-shadow` — will not render
- `filter` (blur, contrast, brightness) — will not render
- `@keyframes` / CSS animations — will not render
- `backdrop-filter` — will not render
- `background-clip: text` — **DANGER: causes gray boxes behind text**. If WeasyPrint ignores this, a gradient meant to clip to the text renders as a full rectangle *behind* the text. Use solid-color text, or move to SVG if gradient text is essential.

**What *does* work in WeasyPrint:**

- `linear-gradient`, `radial-gradient` for backgrounds
- `border`, `border-radius`
- `opacity`
- `transform` (rotate, scale) — static only
- Google Fonts via `@import` (internet connection required)
- Flexbox and Grid
- `@page` rules for print control

### Approach 2: SVG + Inkscape (for PNG or SVG output)

**Best for:** maps, timelines, diagrams, decorative flashcards, any material where the image *is* the page.

**SVG advantages:**

- `<filter>` elements for glow, shadow, blur effects actually render
- Predictable output across renderers
- Embed raster images with `<image xlink:href="...">`
- Export to PNG at any resolution via Inkscape (`inkscape input.svg --export-type=png --export-dpi=300 --export-filename=out.png`)

**SVG filter example:**

```xml
<filter id="soft-shadow">
  <feGaussianBlur stdDeviation="2" result="blur"/>
  <feOffset dx="1" dy="1" result="offsetBlur"/>
  <feMerge>
    <feMergeNode in="offsetBlur"/>
    <feMergeNode in="SourceGraphic"/>
  </feMerge>
</filter>
```

## Full-Bleed CSS Template (for HTML/WeasyPrint)

If a full-bleed layout is desired, use this template. Omit or adjust the padding if the material needs its own margins.

```css
@page {
  margin: 0;
  size: 8.5in 11in;  /* or 11in 8.5in for landscape, 10.5in 8in for tablet-friendly, etc. */
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  width: 8.5in;
  height: 11in;
  margin: 0;
  padding: 0;
  overflow: hidden;
}

.page {
  width: 100%;
  height: 100%;
  padding: 0.5in;  /* internal safe area — adjust per material; can be 0 for full-bleed art */
  position: relative;
}

.background-image {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  z-index: -1;
}
```

### Full-Bleed Checklist

- [ ] `@page { margin: 0; }` is present
- [ ] Body has explicit `width` and `height` in inches (or mm for A-sizes)
- [ ] Body has `margin: 0` and `padding: 0`
- [ ] Body has `overflow: hidden`
- [ ] Background image uses `position: absolute` with `top/left: 0`
- [ ] Text content has internal padding on the content container (not on `body`)

**Do NOT use:**

- `height: 100vh` — WeasyPrint ignores viewport units
- `margin: auto` for centering — use flexbox or explicit positioning
- Percentage-based dimensions without a fixed parent

## Common Dimensions

| Format                    | Size (inches)  | Pixels @ 300 dpi |
|---------------------------|----------------|------------------|
| Letter (portrait)         | 8.5 × 11       | 2550 × 3300      |
| Letter (landscape)        | 11 × 8.5       | 3300 × 2550      |
| Half-letter (landscape)   | 8.5 × 5.5      | 2550 × 1650      |
| A4 (portrait)             | 8.27 × 11.69   | 2480 × 3508      |
| A4 (landscape)            | 11.69 × 8.27   | 3508 × 2480      |
| Tabloid / Ledger          | 11 × 17        | 3300 × 5100      |
| Index card (3 × 5)        | 3 × 5          | 900 × 1500       |
| Index card (4 × 6)        | 4 × 6          | 1200 × 1800      |
| iPad landscape (10.9")    | ~10.9 × 8.2    | design at ~2360 × 1640 |
| Wall card (small)         | 11 × 14        | 3300 × 4200      |

## Pre-Conversion Checklist

Before converting HTML → PDF or SVG → PNG, verify:

1. **All text is in HTML/SVG** — unless you have explicitly invoked the lettering carve-out above
2. **Generated image is referenced** — filename matches exactly
3. **Full-bleed CSS is correct** (if used) — review checklist above
4. **Text fits on the page** — no overflow, no clipping, no awkward line breaks on the last line of a passage
5. **Images positioned correctly** — backgrounds absolute; illustrations sized sanely
6. **No forbidden CSS** — no `100vh`, no `text-shadow` / `box-shadow` / `filter`, no `background-clip: text`
7. **Prints cleanly in grayscale** — if the material is expected to be printed, the page still reads when color is stripped

**After generating the PDF:**

- **Do not use the Read tool on PDF files** — they're binary and can crash the session if large
- The PDF can be opened for the user to verify
- You cannot reliably verify PDF rendering yourself — trust the HTML and fix from user feedback
- If the user reports issues, fix the HTML and regenerate

## Image Handling

**HTML/WeasyPrint:**

```css
.image-container {
  display: flex;
  justify-content: center;
  align-items: center;
  overflow: hidden;
}

.image-container img {
  width: 100%;
  height: auto;
  object-fit: contain;
}
```

**SVG:**

```xml
<image x="76" y="175" width="460" height="420"
       xlink:href="image.png"
       preserveAspectRatio="xMidYMid meet"/>
```

## When to Switch Approaches

**Start with HTML/WeasyPrint** if:

- The material is primarily text (copywork, worksheet, narration page, vocabulary sheet)
- Layout is simple and typography drives the page
- No glows / shadows / complex filters are needed

**Switch to SVG/Inkscape** if:

- The material is fundamentally graphical (map, timeline, diagram, decorative card)
- WeasyPrint output looks wrong (missing effects)
- The design needs filters that WeasyPrint drops
- You've iterated twice on HTML and still have rendering issues
- PNG output is natively appropriate (e.g. a single flashcard image)

## Rendering Commands

**HTML → PDF via WeasyPrint:**

```bash
weasyprint input.html output.pdf
```

Works out of the box with Google Fonts via `@import` if the machine has network access.

**SVG → PNG via Inkscape:**

```bash
inkscape input.svg --export-type=png --export-dpi=300 --export-filename=output.png
```

**SVG → PDF via Inkscape:**

```bash
inkscape input.svg --export-type=pdf --export-filename=output.pdf
```

**PDF → PNG preview (for quick visual check via ImageMagick):**

```bash
magick -density 150 output.pdf[0] preview.png
```

## Workflow Summary

### For HTML/WeasyPrint (PDF output)

1. **Understand requirements** — material type, dimensions, text content, age of reader
2. **Invoke `mason-aesthetics`** for typography, color, illustration-style guidance
3. **Generate any illustration** — decorative / subject only, no text (unless lettering carve-out applies)
4. **Create HTML** — start from the full-bleed template when full-bleed is wanted; plain-margin otherwise
5. **Place illustration** — `position: absolute` for backgrounds; inline `<img>` for content illustrations
6. **Add all text in HTML** — titles, passages, prompts, captions, page footer if any
7. **Apply aesthetics** — typography from `mason-aesthetics`, restrained decoration, calm hierarchy
8. **Run the Pre-Conversion Checklist**
9. **Convert to PDF** — `weasyprint input.html output.pdf`
10. **Iterate on feedback** from the user if rendering issues surface

### For SVG/Inkscape (PNG or SVG output)

1. **Understand requirements** — material type, dimensions, effects needed
2. **Invoke `mason-aesthetics`** for visual direction
3. **Generate decorative image if needed** — no text, unless the lettering carve-out applies
4. **Create SVG** — proper `viewBox`; design at the target dimensions
5. **Embed imagery and add vector text** — `<image>` for raster, `<text>` for labels, unless hand-lettering is the art
6. **Apply filters sparingly** — shadows, glows, soft washes; do not lean on them as a substitute for composition
7. **Export** — PNG at 300 dpi for print, PDF for archival, or ship SVG directly for tablet display

**Never one-shot a complete material with AI image generation when it could be composed with proper vector text.** Even when the lettering carve-out applies, most of the page's text should be vector — the carve-out covers the *decorative* lettering, not the whole page.
