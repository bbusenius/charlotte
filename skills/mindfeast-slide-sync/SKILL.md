---
name: mindfeast-slide-sync
description: Sync already-created MindFeast / Homeschool Screen Lock tablet slides to a student's configured tablet remote endpoint. Use when the user asks to sync slides, push slides, update the tablet, refresh MindFeast, or run slide sync without asking to create new slides. Reads per-student mindfeast.remote_url and mindfeast.remote_token from students.yaml, POSTs to <remote_url>/api/sync, and never prints the token.
argument-hint: "[student name|slug|alias] [--all] [--dry-run] [--timeout SECONDS]"
---

# MindFeast Slide Sync

Sync already-created tablet slide packages to the MindFeast / Homeschool Screen Lock app.

Use this skill when the user asks to sync slides, push slides, update the tablet, refresh MindFeast, or run slide sync. Do not create new slides in this skill. If the user asks both to create slides and sync them, create the slides with `tablet-slide-builder` or `mindfeast-weekly-slides` first, then use this sync contract.

## Student Config

Read `students.yaml` at runtime. Resolve the student by slug, `display_name`, or `aliases`. Never hard-code names, paths, URLs, or tokens.

This skill expects:

```yaml
mindfeast:
  remote_url: http://192.168.1.23:8787
  remote_token: "token from MindFeast remote settings"
```

`remote_url` is the base MindFeast remote URL, including scheme, host, and port, with no path or token fragment. `remote_token` is the required bearer token. Never print the token.

## Workflow

1. Parse the prompt for a student name, slug, alias, `--all`, `--dry-run`, and timeout.
2. If a student is named, sync only that student.
3. If no student is named, sync every student with both `mindfeast.remote_url` and `mindfeast.remote_token` configured. If more than one student is configured, report each result separately.
4. Use the helper script from the repo root:

```bash
.venv/bin/python skills/mindfeast-slide-sync/scripts/sync.py --student <student-slug-or-name>
```

For all configured students:

```bash
.venv/bin/python skills/mindfeast-slide-sync/scripts/sync.py --all
```

For a reachability/configuration check without POSTing:

```bash
.venv/bin/python skills/mindfeast-slide-sync/scripts/sync.py --student <student-slug-or-name> --dry-run
```

## Sync Contract

The helper normalizes the sync endpoint:

- Strip trailing slash from `remote_url`.
- Append `/api/sync`.
- POST once with `Authorization: Bearer <remote_token>`.

Do not retry automatically. If the sync is slow, wait for the command result rather than starting another sync.

## Delivery

Report:

- Student display name or slug.
- Endpoint host and path only, not the token.
- Whether sync was skipped, completed, or failed.
- HTTP status and a short response summary when available.

If Docker or network access blocks the request, say that the slides remain on disk and report the connection error without guessing that the tablet synced.
