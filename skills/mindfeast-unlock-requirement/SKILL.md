---
name: mindfeast-unlock-requirement
description: Set the MindFeast unlock requirement on a configured tablet. Use when the user asks to set, reset, raise, lower, apply, or schedule the number of slides required to unlock the tablet, including no-tablet day policies. Reads per-student mindfeast.remote_url, mindfeast.remote_token, and mindfeast.unlock_requirement from students.yaml, POSTs to <remote_url>/api/settings/unlock-requirement, and never prints the token.
argument-hint: "[student name|slug|alias] [--all] [--count N|--default|--no-tablet|--today-policy] [--dry-run] [--timeout SECONDS]"
---

# MindFeast Unlock Requirement

Set the configured MindFeast tablet unlock requirement.

Use this skill when the user asks to set, reset, raise, lower, apply, or schedule the number of slides required to unlock the tablet. This includes no-tablet day policies. Do not create, sync, or trigger slides in this skill.

## Student Config

Read `students.yaml` at runtime. Resolve the student by slug, `display_name`, or `aliases`. Never hard-code names, paths, URLs, tokens, days, or counts.

This skill expects the normal MindFeast remote config plus optional unlock policy:

```yaml
mindfeast:
  remote_url: http://192.0.2.10:8787
  remote_token: "token from MindFeast remote settings"
  unlock_requirement:
    default: 1
    no_tablet:
      days: [sunday]
      count: 50
```

`remote_url` is the base MindFeast remote URL, including scheme, host, and port, with no path or token fragment. `remote_token` is the required bearer token. Never print the token.

`unlock_requirement.default` is the normal slides-required-per-unlock count. `unlock_requirement.no_tablet.count` is the high requirement for configured no-tablet days. `unlock_requirement.no_tablet.days` is a list of weekday names such as `sunday`, `monday`, or `friday`.

MindFeast currently accepts counts in the app-defined range, presently `1..50`. Do not enforce the max in the skill; send the requested count and surface the app response.

## Workflow

1. Parse the prompt for a student name, slug, alias, `--all`, mode, `--dry-run`, and timeout.
2. Choose exactly one mode:
   - Explicit count: use `--count N`.
   - Reset normal unlocks: use `--default`.
   - Apply no-tablet policy: use `--no-tablet`.
   - Apply whichever policy matches today: use `--today-policy`.
3. If a student is named, set only that student's tablet.
4. If no student is named, set every student with both `mindfeast.remote_url` and `mindfeast.remote_token` configured. If more than one student is configured, report each result separately.
5. Use the helper script from the repo root:

```bash
.venv/bin/python skills/mindfeast-unlock-requirement/scripts/set_requirement.py --student <student-slug-or-name> --count 50
```

Reset to the student's configured default:

```bash
.venv/bin/python skills/mindfeast-unlock-requirement/scripts/set_requirement.py --student <student-slug-or-name> --default
```

Apply the student's configured no-tablet policy:

```bash
.venv/bin/python skills/mindfeast-unlock-requirement/scripts/set_requirement.py --student <student-slug-or-name> --no-tablet
```

Apply today's configured policy for all configured students:

```bash
.venv/bin/python skills/mindfeast-unlock-requirement/scripts/set_requirement.py --all --today-policy
```

For a reachability/configuration check without POSTing:

```bash
.venv/bin/python skills/mindfeast-unlock-requirement/scripts/set_requirement.py --student <student-slug-or-name> --no-tablet --dry-run
```

## Remote Contract

The helper normalizes the unlock requirement endpoint:

- Strip trailing slash from `remote_url`.
- Append `/api/settings/unlock-requirement`.
- POST once with `Authorization: Bearer <remote_token>`.
- Send JSON body `{"count": <slides-required-per-unlock>}`.

Do not retry automatically. If the tablet rejects the count, surface that response.

## Delivery

Report:

- Student display name or slug.
- Endpoint host and path only, not the token.
- Requested count and policy mode.
- Whether the request was skipped, completed, or failed.
- HTTP status and a short response summary when available.
- Saved `slidesRequiredPerUnlock` when MindFeast returns one.

If Docker or network access blocks the request, say that the unlock requirement was not changed and report the connection error without guessing that the tablet changed state.
