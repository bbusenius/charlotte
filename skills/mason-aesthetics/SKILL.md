---
name: mason-aesthetics
description: Aesthetic guidance for homeschool materials built on Charlotte Mason pedagogy. Covers typography, color, illustration style, layout, decoration, language on the page, and the tests a material must pass (atmosphere, printability, respect for the learner as a complete person). Invoke alongside mason-print-design when making materials.
---

This skill supplies the project's aesthetic point of view for homeschool materials. Invoke it whenever you're designing, writing, or rendering a printable — a worksheet, a copywork sheet, a map, a card, a narration page, a nature-notebook page, a vocabulary or memory-verse card, a timeline, or an illustration that lives next to one.

The design prior is atmosphere — the quality a home full of living books already has, which the material should enter gently, as nourishment, not as novelty.

The guidance below is direction, not prescription. Specific fonts and colors are suggestions within traditions, not closed lists — the underlying direction is what matters. When a specific suggestion doesn't fit the material at hand, pick something else in the same register.

## Pedagogical Framework

Read these wiki pages when their language is about to be used in user-facing copy or in the material itself — the vocabulary is load-bearing and shouldn't be paraphrased loosely:

- `pedagogy/wiki/concepts/education-is-atmosphere-discipline-life.md` — the home, including its materials, is the atmosphere. Materials are part of the environment a child lives in, not a supplement to "real" schoolwork.
- `pedagogy/wiki/concepts/children-are-born-persons.md` — the material addresses a complete person, capable and curious, not a pupil to be drilled or a subject to be entertained.
- `pedagogy/wiki/concepts/knowledge-as-food.md` — the material is nourishment. No filler, no empty calories, no twaddle.
- `pedagogy/wiki/concepts/living-books.md` — any text, vocabulary, or illustration on the page draws on the register of living books: first-hand, narrative, the author's own voice. Not a textbook paraphrase.
- `pedagogy/wiki/concepts/science-of-relations.md` — materials, where they can, open relations (invitations to notice, connect, wonder) rather than close them into a single right answer.
- `pedagogy/wiki/concepts/narration.md` — the child's telling-back is the assessment. Materials support narration (blank pages, illustration frames, prompts phrased as invitations) rather than replace it with comprehension checks.

You're not dogmatic about Mason — when a parent asks for a math-practice sheet, build a math-practice sheet. But apply the framework to *how* you build it: in the language, the illustrations, the address, and the restraint.

## Aesthetic principles

### 1. Atmosphere over drama

Materials live in a home full of living books. The aesthetic is calm, ordered, beautiful. The question is never "how do I make this memorable?" The question is "does this belong in the atmosphere?"

- Bold maximalism is wrong here. So is sterile minimalism if it reads as "clinical."
- The closest cousins are the look-and-feel of a Beatrix Potter book, a McGuffey reader, an old Ladybird, a mid-century Elementary Science textbook, a botanical plate, a classical music program, a good commonplace book.
- A material can be striking — a strong nature-study illustration, a handsome calligraphic verse, a richly-colored historical map — without being loud.

### 2. Typography chosen, not defaulted

Legibility for learners, respecting the reader as a complete person. Typography is an explicit choice, not a default — but the choice has to *render*.

**Availability rule (must pass before shipping a material):** every font used in a material must be one of:

1. **Installed on the system.** Check with `fc-list : family | sort -u` before relying on a face. If it's not there, either install it (when the user has asked for a look that requires it) or pick a replacement in the same register.
2. **Loaded from Google Fonts** via `@import` / `<link>` in CSS (WeasyPrint respects this when the machine has network access). Prefer this for anything the user may iterate on or share across machines.
3. **Converted to paths** in the final SVG (Inkscape: "Object to Path") when the output is SVG and portability matters — the letterforms travel as geometry regardless of installed fonts.

When a suggested font below isn't available, substitute another in the same register rather than falling back to a generic default. Falling back to the system's default serif or sans is usually the wrong move — it reads as an unmade choice.

**Body text (paragraphs, passages, vocabulary definitions) — classical serif register:** faces like EB Garamond, Crimson Text, Crimson Pro, Cormorant Garamond, Lora, Libre Caslon Text, Libre Baskerville, Fraunces, Alegreya, Source Serif, Gentium Plus. Warm, literary, generous counters.

**Display / headings — warm serif or inscriptional register:** faces like Alegreya SC, IM Fell DW Pica, IM Fell English, Cormorant SC, Fraunces (with optical sizing used deliberately), Cinzel, Trajan Pro where available. Pair one distinctive display with a restrained body — not two display faces in competition.

**Handwriting / copywork models:** D'Nealian or Zaner-Bloser-style manuscript for beginning writers; Getty-Dubay Italic or equivalent for italic-hand models for older learners. These are *copy-model* fonts — they exist to show correct letterforms, not to be read at length. A stylized "cursive" display font is not a copy model and shouldn't be used as one; a child learning to read letterforms from such a font will mis-form letters.

**Accessibility-first contexts (early readers, vision needs, dyslexia):** Atkinson Hyperlegible (research-driven legibility, serif-adjacent), Lexend (sans, research-driven). These are legitimate first choices — not fallbacks.

**Math, science, rules, tables:** use the body serif unless the density or the subject demands a sans. If a sans is warranted, a quiet humanist sans (Source Sans 3, Alegreya Sans) or Atkinson Hyperlegible.

**What we steer away from in an educational material:**

- Comic Sans or any of its lookalikes
- Stylized "cursive" display fonts as copy models for children
- Converging on whatever the machine's default serif / sans happens to be, when a more considered choice is available and renders
- More than two distinct typefaces per page (a copy-model font in addition to body + display is fine — that's a third typeface with a specific job)

### 3. Color: ink-on-paper direction

The direction is *ink on paper*: a ground that looks like good book stock, inks that look like real inks, restraint. Specific palettes are a matter of judgement for the piece at hand — the direction is what's non-negotiable.

- **Grounds tend toward** cream / ivory / warm off-white for most printed materials; pure white where color fidelity matters; deep muted grounds (navy, oxblood, forest, charcoal) for wall cards and decorative pieces with inverted palettes.
- **Inks tend toward** deep naturals — warm black, navy, sepia, forest, burgundy, umber, sage — rather than saturated primaries. A warm near-black usually sits better than pure `#000`.
- **Accents are used sparingly**, usually one or two per page. Muted golds, tuscan reds, indigos, sages.
- **Judgement applies.** Some materials legitimately want a bolder or brighter palette — a Latin-American folk-art themed card, a child's astronomy poster, a regional map following its own visual tradition. When a stronger palette is warranted by the subject, use it with the same restraint (limited number of tones, considered relationships between them).

**What we steer away from:**

- Neon / fluorescent primaries as a default
- Purple-to-pink gradients on white (the "AI slop" cliché)
- Five or six saturated accent colors competing on one page
- Color carrying hierarchy that collapses in grayscale — run the printability test

### 4. Illustration style

When generating illustrations for a material (via Gemini, Grok, or any source), default the visual register to one of the traditions below. State the register explicitly in the prompt — vague prompts produce generic results.

**Preferred registers:**

- Pen-and-ink line drawing (Beatrix Potter, E. H. Shepard, Arthur Rackham)
- Watercolor wash with ink linework (classic children's-book illustration)
- Botanical plate (Ernst Haeckel, Maria Sibylla Merian, Pierre-Joseph Redouté)
- Victorian / Edwardian nature-study illustration
- Vintage textbook plate (mid-century scientific or historical illustration)
- Wood engraving / scratchboard for historical atmosphere
- Clean technical diagram (for math, physics, mechanisms) — thin lines, restrained labeling
- Chalkboard-style line drawing for quick instructional diagrams
- Regional / folk-art traditions when the subject itself calls for them (a Guatemalan textile motif, a Japanese woodblock, a medieval manuscript illumination) — chosen because the subject lives in that tradition, not as decoration

**What we steer away from in illustration prompts:**

- 3D cartoon, Pixar-style children's characters
- Stock-art children (smiling kids in backpacks, thumbs-up figures)
- Emoji, sparkle / rainbow filters, stickers
- Generic clip-art
- "AI poster" painterly-digital with dramatic rim-lighting
- Overly polished vector flat-design ("corporate Memphis")

**Prompt construction example:**

- Good: *"A pen-and-ink botanical plate of a monarch butterfly on a milkweed stem, in the style of an early-twentieth-century natural-history textbook. Cream background. No text, no labels."*
- Good: *"A watercolor-and-ink illustration of Guatemalan lowland jungle with a quetzal perched on a branch, in the register of Beatrix Potter. No text."*
- Weak: *"A cute butterfly for a kids worksheet, colorful, fun."* — this collapses the register into the aesthetic we steer away from.

### 5. Layout

Hierarchy serves the learner's eye, not novelty. Within that constraint, composition is open.

- **Full-bleed, margined, symmetric, asymmetric — all valid.** Pick what serves the material. A picture-study card wants full-bleed imagery. A copywork sheet wants generous writing room. A nature-notebook page wants a framed sketch area and lined space. A map wants the map.
- **Negative space is a tool, not a virtue in itself.** Use it where the page needs to breathe; pack it where density is appropriate (a vocabulary card, a reference sheet).
- **Grid-breaking for drama is out of register.** If an asymmetric layout serves the content, use it. If it serves the designer's self-expression, reject it.
- **Tablet-aware composition** — if the primary display is a tablet, design at the tablet's native aspect ratio rather than reflexively at 8.5 × 11". Landscape is often right.
- **Print-safe zone** for anything that will be printed — 0.25–0.5" unprinted at the edge, or accept that home printers may clip.

### 6. Decoration

Restraint. An ornament earns its place on the page, or it goes.

- A decorative initial at the head of a copywork passage is often exactly right.
- A single botanical vignette in the corner of a nature-notebook page is fine.
- A restrained rule below a title is fine.
- A border of five different clip-art elements around a math worksheet is wrong. Cut it.
- "Cute" seasonal decoration (pumpkins in October, snowflakes in December) is only welcome when the season is the content. Otherwise it reads as filler.

### 7. Language on the page

The copy on a material — instructions, prompts, captions, titles — is not neutral. It addresses a person (`pedagogy/wiki/concepts/children-are-born-persons.md`). Write it with care.

- **Direct, unpatronizing:** *"Copy this passage in your best hand."* Not: *"Let's practice our handwriting together!"*
- **Real vocabulary:** words drawn from living books, not simplified substitutes. If the passage uses the word *dwelt*, the instruction does not have to say *lived*.
- **Invitations, not interrogations:** *"What do you notice about the leaves?"* Not: *"What are the three parts of the leaf? (A) Stem (B) Vein (C) Edge."*
- **No emoji, no exclamation-point enthusiasm.** The material's cheerfulness comes from its beauty, not from its tone.
- **Second-person singular** when addressing the learner directly; the tone is respectful, not chummy.

### 8. Vector text — default, with a lettering carve-out

Default to vector text in the final output: searchable, scalable, crisp at any print or tablet size. See `mason-print-design` for the rendering rules.

Exception: allow baked-in text when the lettering *is* the art — hand-lettered memory-verse cards where the calligraphy carries the material's beauty, decorative initials, period map labels in a historical hand, chalked-style wall banners. The test: would swapping the lettering for a vector font materially diminish the piece? If yes, hand-lettered is warranted; if no, keep it vector.

## Tests a material must pass

Before considering a material finished, run it through these.

### Atmosphere test

*Would this look at home between a Beatrix Potter and a nature notebook, or between a textbook and a promotional flyer?*

If the honest answer is "the second," the design has drifted. Common causes: too many colors, wrong register of illustration, exclamation-point copy, clip-art decoration, a display font that's trying to be memorable.

### Printability test

*Does this still read clearly when printed in grayscale on a home printer running low on ink?*

If hierarchy collapses once color is gone, fix the hierarchy. Home-printer economics are real; most of these materials will not come out of a color laser at 300 dpi.

### Font-availability test

*Every font on this page either shows up in `fc-list`, or is loaded from Google Fonts via `@import`, or has been converted to paths in the SVG.*

If the answer is no, the page won't render the way it looks in the browser preview — it'll silently substitute the system default and the typography goes with it. Fix before shipping.

### Person test

*Does this address a person, or does it address "a student"?*

If the language talks down, swaps out real vocabulary, or performs cheerfulness at the reader, rewrite it. The tone mismatch is the first thing a capable child will feel.

### Nourishment test

*Is this delivering actual food (`concepts/knowledge-as-food`), or is it busywork dressed up?*

A copywork passage drawn from a living book is food. A worksheet asking a child to circle the nouns in a paraphrased sentence from a textbook is not. If the material is legitimately for drill (math facts, handwriting letters, phonics patterns) that's fine — drill is not twaddle. What's twaddle is pretending drill is content.

### Restraint test

*Is every element on the page doing work?*

If an ornament, a border, a color, or a line of copy isn't contributing, remove it. Restraint is not austerity — it's the discipline of a page that knows what it's for.

## When the Request Conflicts With the Framework

Never refuse the user's request. Build what they asked for.

At the end of a delivery, if the material sits in real tension with the pedagogy (a comprehension-check worksheet on a living book, for example), a single short line of reminder is welcome — never preachy, never blocking, framed as an offer rather than a correction:

> *"Happy to also make a blank narration template for this passage — Mason's method is oral or written narration after a single reading. Just say the word."*

One line. At the end. Offered once. Never more than that.
