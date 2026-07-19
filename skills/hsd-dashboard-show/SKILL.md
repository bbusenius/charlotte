---
name: hsd-dashboard-show
description: Generate or show a student's visual Homeschool Dashboard from Homeschool-Dashboard-compatible time spreadsheets configured in students.yaml. Use when the user asks to show, open, view, render, generate, or send a homeschool dashboard.
argument-hint: [student-name]
---

# HSD Dashboard Show

Generate visual Homeschool-Dashboard HTML for a configured student.

## Workflow

1. Resolve the student from `students.yaml` by slug, display name, or alias. Never hard-code spreadsheet paths.
2. Run:

```bash
.venv/bin/python scripts/hsd_dashboard.py --student <student>
```

3. The script writes HTML to `dashboards/<student-slug>.html` unless `--output` is supplied. Existing dashboard HTML is generated output and should be replaced on each run.
4. Deliver the dashboard according to the active runtime:
   - Local desktop agent: open the file in a browser only when the user asked to open/show it and the runtime permits GUI access.
   - CLI/text agent: report the generated HTML path.
   - Chat gateway: attach or link the generated HTML if the gateway supports files.

## Notes

- This skill is for visual dashboards, not compact question answering. Use `hsd-records-read` for questions such as "what did Alice last do in Math?"
- `scripts/hsd_dashboard.py` depends on the `homeschool_dashboard` Python package from `pyproject.toml`. If missing, run the normal Charlotte install command and retry:

```bash
.venv/bin/python -m pip install -e .
```

- The dashboard package may include reading-list tables when the time workbook contains the expected `Reading List` metadata column.
