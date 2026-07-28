# Charlotte Ingest Contract

How lesson and book material reaches Charlotte.

There are two ways, both first-class. A family can use either, and a finished
lesson log looks the same regardless of which one produced it.

## 1. Typed queues

A **typed queue** is a destination whose *name* says which workflow the material
belongs to and which student it is about. Dropping a photo into the queue named
`eliana` rather than `eliana-books` is itself the classification: it happens at
write time, costs the parent nothing, and leaves Charlotte with nothing to infer.

That buys two things:

- **Terse messages.** "Lesson 112, 9-9:45" is enough. The queue already supplies
  the workflow and the student.
- **Safe automation.** A scheduled run over a typed queue knows exactly what to
  do with whatever it finds. A scheduled run over a general chat channel would
  have to guess whether a message was a lesson, a request to trigger a tablet
  slide, or ordinary conversation — so it would either do nothing or do
  something wrong.

Queues are configured per student in `students.yaml`:

```yaml
inbox:
  kind: signal
  queue: eliana
reading:
  inbox:
    kind: signal
    queue: eliana-books
```

`kind` names the adapter; `queue` is the queue name as that adapter knows it.
Legacy registries spell these `signal_group_alias` and
`reading.signal_group_alias`; treat those as `kind: signal`.

### Adapter contract

An adapter needs three operations:

1. **List unprocessed items** for a queue, each with a timestamp, a sender, and
   its text.
2. **Give attachment paths** for an item, as readable paths on the local
   filesystem.
3. **Mark items consumed**, so the next run does not see them again.

Consumed-state belongs to the adapter. It is never recorded in a lesson log.

### Implemented adapters

| `kind` | Implementation | Notes |
|---|---|---|
| `signal` | [`signal-sieve`](https://github.com/bbusenius/signal-sieve) | `list --group`, attachment paths resolved against its `attachments_dir`, `mark-processed`. Requires a host-owned capture service; see the README. |

Nothing in the log format, the skills, or the scripts is Signal-specific — only
the adapter is. Other transports satisfy the same contract:

- **A chat group or forum topic** on any platform, given a bot that keeps its own
  processed-state. Note that a runtime's general chat gateway is not this: it
  delivers conversation, not a pollable queue.
- **A watched directory** (`inbox/eliana/lessons/` → move to `processed/`). This
  is the cheapest adapter to write and suits families who photograph into a
  synced folder.
- **A dedicated email address**, one per queue.

New adapters are welcome. Implement the three operations, add a `kind`, and
document it in the table above.

### Attachments

Adapters hand over paths into transient storage. Workflows **copy** those files
into the record they belong to and never reference them in place — an inbox gets
pruned, and a log pointing into one is a directory of dead links within months.
For lesson logs, `scripts/lesson_log_new.py add` does this.

## 2. Conversational

The parent tells Charlotte directly, in whatever channel the runtime provides,
attaching photos or voice notes. No configuration, works in every runtime.

This is not a degraded mode. It costs a few words of context per message —
naming the child when more than one is in play, saying that this was a lesson —
and it is what most families will use, since most do not run a capture service.

A student with no `inbox` block in `students.yaml` is a conversational-only
student, and that is a normal configuration.

## Reporting problems

When material cannot be placed into a log — for example, no student or subject
can be determined — **report to the main conversation channel, never into the
queue.** Writing into a queue that exists to be consumed pollutes it: Charlotte's
own question comes back as input on the next run.

Leave the material unprocessed so it is still there once the parent answers.

Missing times are different: write the lesson log without `start_time` and
`end_time`, mark its source material consumed, and report that the log is waiting
on times before it can reach Homeschool-Dashboard. The incomplete frontmatter is
the durable pending state; no separate queue or pending database is needed.

This places one requirement on runtimes: **an unattended run needs an outbound
path to the main conversation channel.** A scheduled queue drain with no way to
say "Tuesday's Language Arts log is waiting on times" cannot tell the parent what
still needs attention.

## The invariant

> A finished record carries nothing about which ingest mode produced it, which
> queue it came from, or how many passes assembled it.

No message IDs, no channel names in frontmatter, no processing metadata. A
lesson log written from a Signal queue and one written from a Telegram
conversation are indistinguishable, and both are just an account of what was
taught. If you can tell them apart, something has leaked.

`messages.md` does record a timestamp, a sender, and a channel label per message
— that is provenance about *the material*, it survives the inbox being pruned,
and it is the same in both modes.
