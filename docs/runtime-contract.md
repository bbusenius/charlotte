# Charlotte Runtime Contract

Charlotte is runtime-neutral at its core. The repo owns the homeschool workflow contract; each agent runtime owns its own mechanics for skills, tools, sub-agents, permissions, secrets, and chat gateways.

The canonical project surface is:

- `AGENTS.md` for operating instructions.
- `skills/*/SKILL.md` for workflow instructions.
- `.agents/skills/*` and `.claude/skills/*` as harness adapters back to `skills/`.
- `students.yaml` for local family/student configuration.
- `runtime.yaml` for non-secret machine/tool paths.
- `image-generation.yaml` for local image route configuration.
- ignored local content roots: `curricula/`, `tablet-slides/`, `generated-images/`, `field-trips/`, `.backups/`, and `.logs/`.

Runtime adapters must not fork the skill instructions unless a runtime truly requires a shim. Prefer symlinks, external skill directories, or runtime config that points at the canonical skill tree.

## Ingress Model

Signal via `signal-sieve` is the implemented structured workflow queue.

Signal groups remain the capture path for lessons, books, screenshots, and other records that feed spreadsheet or generated-content workflows. Skills such as `hsd-time-log` and `hsd-book-log` consume captured Signal messages only when explicitly invoked.

General conversation gateways are runtime-adapter concerns. They may invoke Charlotte workflows, including logging, slide generation, planning, and material creation, but they should not replace Signal as the structured capture queue unless that behavior is explicitly designed. Gateways intended for family use should use explicit user/chat allowlists.

## Runtime Requirements

Any supported runtime should provide:

- Skill discovery for `SKILL.md` folders without duplicating canonical skills.
- A project workspace rooted at this repo.
- Writable access to ignored local content roots when requested by a skill.
- Read access to `students.yaml`, `runtime.yaml`, `image-generation.yaml`, scripts, and `pedagogy/wiki/`.
- Environment or ignored-file secret loading without committing credentials.
- MCP or equivalent external tool access for Grok, Google Maps, and future integrations.
- A sub-agent mechanism for orchestrator skills.
- A permission model that distinguishes ordinary reads/generation from sensitive writes.
- Logs sufficient to reconstruct high-level work: task, runtime, model/provider, files written, external tools called, and spawned child work.
- For container runtimes, a built workspace and Python environment installed from `pyproject.toml`; runtime mounts should provide secrets, agent state, local content roots, and canonical family data rather than replacing the built checkout.

## Safety Contract

Runtime adapters should start conservative, but normal Charlotte workflows should not be made cumbersome.

- Ordinary conversation and read-only planning can run without special approval.
- Writing generated artifacts under `curricula/`, `tablet-slides/`, `generated-images/`, `field-trips/`, `.logs/`, or another user-specified output path is allowed when requested.
- Creating new ad-hoc files, including new spreadsheets or reports, is allowed when requested.
- Updating canonical records is more sensitive. This includes time-tracking spreadsheets, reading-list spreadsheets, `students.yaml`, `runtime.yaml`, `image-generation.yaml`, and any future durable learner/profile state.
- Canonical record updates are allowed when they are the expected action of an explicitly invoked workflow, such as `hsd-time-log` or `hsd-book-log`.
- `signal-sieve mark-processed` is allowed only after the corresponding Signal messages have been successfully processed by an invoked logging workflow.
- Remote device syncs, including MindFeast slide sync, are allowed when directly requested, whether as part of a skill workflow or as a standalone action.
- Outside requested workflows/actions, canonical record edits, Signal state changes, destructive shell commands, broad filesystem writes, and credential changes must be blocked or require explicit approval.

The runtime may implement this through native approvals, sandboxing, tool allowlists, profile separation, or a combination of those mechanisms.

## Sub-Agent Contract

Skills use the neutral verb "spawn" for heavy or repeated child work. Runtime adapters map that verb to their native primitive.

- Hermes: `delegate_task(...)`
- OpenClaw: `sessions_spawn(...)` and `sessions_yield`
- Claude Code: `Agent(...)`
- Opencode: its equivalent sub-agent/session primitive

Spawn prompts must be self-contained. They should include the student record, paths, slug/id choices, output directory, constraints, and the exact expected summary. A child agent must not depend on implicit parent memory.

Default nested behavior should stay shallow: the top-level orchestrator may spawn repeated workers; spawned workers should inline their own children unless there is a specific reason to fan out again.

## Runtime Adapter Shape

Runtime-specific files live under `runtime/<runtime-name>/`.

Each adapter should include:

- A setup README.
- Example config with no secrets.
- Docker or service examples when useful.
- Notes mapping this contract to the runtime's native features.
- Current operational notes for the supported setup.

The concrete tool checklist is maintained in [Runtime Tool Surface](runtime-tool-surface.md).
