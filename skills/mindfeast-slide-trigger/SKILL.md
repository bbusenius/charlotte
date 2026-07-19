---
name: mindfeast-slide-trigger
description: Trigger the MindFeast remote endpoint to show a slide now on a configured tablet. Use when the user asks to trigger a slide, show a slide, pop a slide, open MindFeast, or make the tablet show the next lock-screen slide without creating or syncing slides. Reads per-student mindfeast.remote_url and mindfeast.remote_token from students.yaml, POSTs to <remote_url>/api/trigger, and never prints the token.
argument-hint: "[student name|slug|alias] [--all] [--dry-run] [--timeout SECONDS]"
---

# MindFeast Slide Trigger

Trigger a configured MindFeast tablet to show a slide now.

Use this skill when the user asks to trigger a slide, show a slide, pop a slide, open MindFeast, or make the tablet show the next lock-screen slide. Do not create or sync slides in this skill. If the user asks to create slides first, use `mindfeast-slide-builder` or `mindfeast-weekly-slides`; if they ask to sync slides, use `mindfeast-slide-sync`.

## Student Config

Read `students.yaml` at runtime. Resolve the student by slug, `display_name`, or `aliases`. Never hard-code names, paths, URLs, or tokens.

This skill expects:

```yaml
mindfeast:
  remote_url: http://192.0.2.10:8787
  remote_token: "token from MindFeast remote settings"
```

`remote_url` is the base MindFeast remote URL, including scheme, host, and port, with no path or token fragment. `remote_token` is the required bearer token. Never print the token.

## Workflow

1. Parse the prompt for a student name, slug, alias, `--all`, `--dry-run`, and timeout.
2. If a student is named, trigger only that student's tablet.
3. If no student is named, trigger every student with both `mindfeast.remote_url` and `mindfeast.remote_token` configured. If more than one student is configured, report each result separately.
4. Use the helper script from the repo root:

```bash
.venv/bin/python skills/mindfeast-slide-trigger/scripts/trigger.py --student <student-slug-or-name>
```

For all configured students:

```bash
.venv/bin/python skills/mindfeast-slide-trigger/scripts/trigger.py --all
```

For a reachability/configuration check without POSTing:

```bash
.venv/bin/python skills/mindfeast-slide-trigger/scripts/trigger.py --student <student-slug-or-name> --dry-run
```

## Trigger Contract

The helper normalizes the trigger endpoint:

- Strip trailing slash from `remote_url`.
- Append `/api/trigger`.
- POST once with `Authorization: Bearer <remote_token>`.

Do not retry automatically. If the tablet reports no active slides, surface that response rather than trying to sync or create slides.

## Delivery

Report:

- Student display name or slug.
- Endpoint host and path only, not the token.
- Whether trigger was skipped, completed, or failed.
- HTTP status and a short response summary when available.
- Triggered `slideId` when MindFeast returns one.

If Docker or network access blocks the request, say that no slide was triggered and report the connection error without guessing that the tablet changed state.
