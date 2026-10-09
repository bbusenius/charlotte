---
name: mindfeast-morning-note
description: >
  Compose one household morning note from recent lesson logs and push it to
  MindFeast Agent Alarm. Use when asked to write, refresh, or run the nightly
  morning note. Reads students.yaml at runtime. Never hard-code student names.
  Does not change the picture, song, theme, alarm time, repeat days, or enable
  state.
argument-hint: "[heading]"
---

# MindFeast Morning Note

Write one morning note for the household and push it to Agent Alarm. Draw it from what the household is actually studying. The students already know what they did. The note does not tell them.

This skill reads lesson logs and pushes note text. `mindfeast-agent-alarm` pushes alarm settings and note text it is given. It does not compose this note.

## Usage

- A nightly scheduled run, or a request to write or refresh the morning note
- Heading from the prompt when the prompt sets one. Otherwise leave the heading already on the alarm and change only the body

Never hard-code student names, paths, URLs, or tokens. Never print a remote token. Do not create slides, generate images, or change the picture, song, theme, alarm time, repeat days, or enable state.

Keep the run noninteractive. A scheduled job has no one to answer a question.

## Workflow

1. Read `students.yaml`. Every student is in the pool the note may draw on, including a student with no `agent_alarm`. Alarm targets are the students with both `agent_alarm.remote_url` and `agent_alarm.remote_token` non-blank. If none are configured, say so and stop. If two alarm students share one `remote_url`, they are one push.

2. Read recent notes so you do not repeat one. For each alarm student, read `.state/agent-alarm-notes/<slug>.md` if it exists. Also run, once per distinct alarm URL:

```bash
.venv/bin/python skills/mindfeast-agent-alarm/scripts/push.py --student <slug> --status
```

Use the current note from that status. Do not print the token.

3. Read every student's lesson logs. The range is the seven calendar days ending yesterday in the timezone the job states, or the machine's local timezone when the job states none. Include today only if a log is already dated today. From the repository root, for each student slug:

```bash
.venv/bin/python scripts/lesson_log_read.py list \
  --student <slug> \
  --from YYYY-MM-DD --to YYYY-MM-DD \
  --include-section "what we did" --include-section "how it went" \
  --limit 50
```

Do not read spreadsheets. Do not run the lesson-log skill. Do not write or amend any log.

4. Choose one subject present in that range, and one note from it. Any subject in the logs is eligible. Do not prefer a subject because this skill mentions it. Nature study is allowed. It is not the default. If the recent notes have stayed on one subject and another subject in the range has something worth telling, use the other subject.

The note is one of these kinds: a fact, a cause, a person, a mechanism, or an inspirational thought. An inspirational thought is in scope. It is a real idea from the material worth carrying into the day. It is not the only kind. If the recent notes are inspirational thoughts and the range also has a fact, a cause, a person, or a mechanism, choose one of those.

5. Read that note's source before writing. `show` the chosen session. When its `lesson.sources` names a path, read that exact source with `scripts/curriculum_read.py read` for the recorded student, using `pdf_pages`, `lines`, or `section` when the source item has them. The condensed log line is a lead. The note comes from what the material teaches. Skip the source only when it is missing or its location is ambiguous. Do not invent a claim the log and that source do not support. An inspirational thought has to come from that material too.

6. Write one note. At most 3 sentences, and at most 250 characters. A sentence ends at a period, question mark, or exclamation mark. Count the sentences and the characters. If the draft is over either limit, shorten it and count again. Push only a note that is within both limits.

They already know what they did. Do not narrate the session, the outing, the weather, who held what, or who said what. Do not summarize the day. Do not name the students. A person in the material may be named.

Say the thing directly, whichever kind you chose. No scene-painting, no poetic fragments, no atmosphere, no description of light, wind, or how something felt. Do not retell a passage in elevated language. State it in ordinary sentences. A slogan, a mood, or a scene is not an inspirational thought.

The youngest student does not need to understand every word. Do not simplify the idea down to the youngest grade. Do not talk down. Do not be cute. Do not assign a task. Do not list things to go find, notice, or listen for. Do not put a greeting in the body.

A saved note that recounts what the students did, or that paints a scene, is the old failure. Do not write another one.

If the prompt gives an exact heading, use that string and do not change it. If it gives none, leave the heading already on the alarm.

If the range has no idea worth telling, do not push a filler note. Stop and say so. Leave the current note in place.

7. Push only the note, once per distinct alarm URL:

```bash
.venv/bin/python skills/mindfeast-agent-alarm/scripts/push.py \
  --student <slug> \
  --notes-heading "<heading>" \
  --notes "<the note>"
```

Omit `--notes-heading` when the prompt did not set one. Do not pass any other flags. Confirm HTTP success from the helper. If the tablet is unreachable, retry twice. If it still fails, stop. Do not clear the existing note.

8. Only after HTTP success, append the local calendar date of this run and the note to `.state/agent-alarm-notes/<slug>.md` for each alarm student on that URL. Keep the last 14 notes. Create the directory if needed. The filename is the slug. Do not put tokens in the file.

## Delivery

When the invocation says a successful push must stay silent, the entire final response is exactly `[SILENT]` and nothing else. A success message on a scheduled run is delivered to the household and wakes them.

When a person asked in conversation, report the note, the heading, which alarm received it, and whether the push succeeded. Never print the token.

If the push failed or you did not push, say so in plain text. Do not include a silence marker.
