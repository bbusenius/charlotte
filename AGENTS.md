# homeschool-hub

Authoring tools for a Mason-shaped homeschool: lessons, units, curricula, materials, and field trips, grounded in the pedagogy wiki under `pedagogy/wiki/`. The canonical skills live under `skills/` — `lesson-plan-builder`, `unit-builder`, `curriculum-builder`, `materials-builder`, `mason-aesthetics`, `mason-print-design`, `field-trip-planner`, plus the data-pipeline skills `time-log` and `book-log`. Harness-specific skill directories such as `.claude/skills/` and `.agents/skills/` are adapters, usually symlinks, back to the canonical skill directories. Per-student configuration lives in `students.yaml` at the repo root.

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
