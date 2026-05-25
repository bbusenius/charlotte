# Charlotte Mason Homeschool Agent

Charlotte is a Mason-shaped homeschool agent system: lessons, units, curricula, materials, field trips, Homeschool-Dashboard-compatible time logging, Homeschool-Dashboard-compatible book logging, tablet slide generation, and tablet slide sync, grounded in the pedagogy wiki under `pedagogy/wiki/`. The canonical skills live under `skills/` — `lesson-plan-builder`, `unit-builder`, `curriculum-builder`, `materials-builder`, `tablet-slide-builder`, `mindfeast-weekly-slides`, `mindfeast-slide-sync`, `mason-aesthetics`, `mason-print-design`, `field-trip-planner`, plus the Homeschool-Dashboard data-pipeline skills `hsd-time-log` and `hsd-book-log`. Harness-specific skill directories such as `.claude/skills/` and `.agents/skills/` are adapters, usually symlinks, back to the canonical skill directories. Per-student configuration lives in `students.yaml` at the repo root.

Plain requests to make a slide, tablet slide, lock-screen slide, unlock question, or MindFeast slide should route to `tablet-slide-builder`. Do not start those requests with `materials-builder`, `mason-aesthetics`, `mason-print-design`, WeasyPrint, or SVG/PDF rendering unless the user separately asks for a printable/static material.

Plain requests to make an image, picture, illustration, drawing, or visual asset are standalone image requests unless the user explicitly asks for a slide, tablet slide, lock-screen slide, MindFeast slide, printable material, worksheet, PDF, curriculum artifact, or names a workflow-specific output. For standalone image requests, run the Charlotte image router from the project root and deliver the generated file. In the Hermes Docker runtime, use absolute `/workspace` paths:

```bash
.venv/bin/python /workspace/scripts/charlotte_image.py \
  --prompt "<image prompt>" \
  --out /workspace/generated-images/<short-slug>.png \
  --mason-aesthetics \
  --json
```

Use the JSON `path` value exactly when delivering the image with `MEDIA:<path>`; providers may save a different extension than the requested output path. Do not use Hermes creative skills such as ComfyUI, p5js, or hand-written SVG as the first path for ordinary image requests. Do not save standalone images under `tablet-slides/`; that tree is only for valid tablet slide packages.

For standalone image requests, preserve the user's requested subject and constraints. Do not invent style adjectives, settings, lighting, camera language, emotional tone, species, props, scenery, or composition details unless the user explicitly asks for them. The `--mason-aesthetics` flag owns the default visual register; pass the user's request plainly to `--prompt`.

Plain requests to sync slides, push slides, update the tablet, or refresh MindFeast should route to `mindfeast-slide-sync`. Do not invoke `mindfeast-weekly-slides` unless the user also asks to create slides from time logs.

Plain requests to log homeschool lesson time, process lesson Signal messages, or update Homeschool-Dashboard time records should route to `hsd-time-log`. Plain requests to log books, process book Signal messages, or update Homeschool-Dashboard reading records should route to `hsd-book-log`. These workflows must resolve the student from `students.yaml` and pass the exact configured Signal alias (`signal_group_alias` or `reading.signal_group_alias`) to `signal-sieve`; do not derive the Signal group name from display names or user capitalization.

## Sub-agent spawn convention

Orchestrator skills (`unit-builder`, `curriculum-builder`) decide for each child invocation whether to **inline** it or **spawn** it as a sub-agent. Leaf skills (`materials-builder`, `lesson-plan-builder`, `field-trip-planner`, `mason-aesthetics`, `mason-print-design`) never make this decision — they are workflow-only and run wherever the caller put them.

- **Inline** a child when the call is single and cheap (e.g. one hero image). The child's instructions load into the current context and the current agent executes them, then returns to the next workflow step.
- **Spawn** a child when the call is heavy or repeats serially (e.g. one `lesson-plan-builder` call per lesson; one `unit-builder` call per unit). Each spawn runs in its own ~200K-token context, returns a summary, and the orchestrator continues. This bounds total context depth.
- **Sub-agents prefer to inline their own children.** The decision to spawn lives at the top of the tree. Once you are inside a spawned sub-agent, fan no further unless absolutely necessary — your own ~200K context is enough to absorb the work the leaf skills do.

The skill text uses the abstract verb **"spawn"** rather than naming a specific tool. Each harness adapter translates spawn to its own primitive:

- Claude Code → `Agent(subagent_type=..., prompt=..., model=...)`
- OpenClaw → `sessions_spawn(...)`
- Opencode → its equivalent

**Model / capability selection.** Spawned sub-agents should be assigned by the harness to a model capable of the child task. The skill text names the required capability class rather than a provider-specific model ID. Avoid defaulting heavy writing/planning children to low-capability worker models merely because they are child agents. Harness adapters may map these capability classes to provider-specific model IDs in their own config.

**Prompt shape for spawn.** Each spawn prompt is a self-contained prose block carrying every input the child needs (student record, slugs, paths, count, flags, parent context). The child has no access to the orchestrator's working memory, so anything implicit upstream must be made explicit in the prompt.

## Other notes

- Per-student paths and curricula come from `students.yaml`. Skills must read it at runtime — never hard-code student names, aliases, grades, or curriculum file paths.
- Generated content (lessons, units, curricula, trip files) is **date-portable by design**. No calendar-anchor dates anywhere — no `YYYY-MM-DD` filenames, no `date_planned` frontmatter, no "starting September" prose. Venue opening hours from Google Maps and time-of-day qualifiers (morning, afternoon, evening, dusk, dawn) are fine when the activity genuinely depends on them.
- Pedagogy references in generated files are **real markdown links** using the correct relative path from the generated file (for example, `[narration](../../../pedagogy/wiki/concepts/narration.md)` from a lesson under `curricula/<class>/<unit>/`). Never use Obsidian `[[wiki-links]]` in generated curriculum content. The wiki itself uses `[[…]]` internally; that's the wiki's convention, separate from generated curriculum content.
