---
name: focus
description: "Planning skill for the following day, rest of the current week, or next week. Takes a priority description, sharpens tasks into bite-sized actions, runs wrap in the background to surface anything urgent that's missing from the plan, analyzes calendar availability for the planning window, syncs with Asana, and — only after user approval — books 'DW' focus blocks on the calendar. Invoke with /focus followed by a description of priorities and the planning horizon (e.g. /focus tomorrow: finish the auth spec and review Ben's PR; /focus this week: ...; /focus next week: ...)."
compatibility: "Claude Code — requires workspace-mcp, Asana MCP, Granola MCP, Slack MCP, Gmail MCP, Atlassian MCP"
---

# Focus (Daily / Weekly Planning)

`$ARGUMENTS` is a free-form description of the user's priorities plus the planning
horizon. Parse the horizon from natural language:

| Phrase | `$HORIZON` | `$WINDOW_START` | `$WINDOW_END` |
|---|---|---|---|
| "tomorrow" | `tomorrow` | tomorrow at 00:00 local | tomorrow at 23:59 local |
| "rest of this week" / "this week" | `week` | tomorrow at 00:00 local (skip today) | this Friday at 23:59 local |
| "next week" | `next_week` | next Monday at 00:00 local | next Friday at 23:59 local |

If the horizon is ambiguous, ask once before proceeding.

Store resolved ISO dates as `$START_DATE` (YYYY-MM-DD) and `$END_DATE` (YYYY-MM-DD).
Store a list of working days in `$DAYS` = array of YYYY-MM-DD strings for each
weekday in the window (Monday–Friday only).

---

## Phase 1 — Sharpen priorities (interactive, before gathering data)

Read the user's raw priority list from `$ARGUMENTS`. For each item:

1. **Check for vagueness or scale.** A task is too vague if you can't tell what
   "done" looks like. A task is too large if it would realistically take more than
   60 focused minutes. If either is true, say so and ask the user to break it down.

2. **Suggest a breakdown.** For each oversized or vague item, propose 2–4 concrete
   subtasks. Example:
   > "Finalize Q3 roadmap" is probably 3–4 hours of work. Here's a possible breakdown:
   > - Review existing roadmap doc and note gaps
   > - Sync with PM on open questions
   > - Draft updated roadmap sections
   > - Review/polish draft

3. **Confirm the refined list.** Present the full sharpened task list and ask the
   user to confirm, adjust, or add anything before moving on.

Store the confirmed list as `$TASKS` — an ordered array of task objects:
```
{ name: string, notes: string?, asana_gid: string? }
```

Do not proceed to Phase 2 until the user confirms `$TASKS`.

---

## Phase 2 — Background intelligence (all sources in parallel)

While the user is reviewing Phase 1 output, begin gathering data. Fire all of
the following simultaneously.

### 2A — Run wrap in the background

Invoke the **wrap** skill logic for the appropriate scope:
- `$HORIZON = tomorrow` or `week` → run wrap for `day` (today's activity)
- `$HORIZON = next_week` → run wrap for `week` (this week's activity)

Do not re-render the full wrap output. Instead, extract:
- Unresolved commitments and open loops not already in `$TASKS`
- Anything explicitly flagged as urgent or time-sensitive
- Any Asana tasks assigned to the user that are due within `$WINDOW_END` and not
  already reflected in `$TASKS`

Surface these as a short list after Phase 1 confirmation (see Phase 3).

### 2B — Fetch calendar for the planning window

```
get_events(
  user_google_email="<user_email>",
  calendar_id="primary",
  time_min="$START_DATE T00:00:00",
  time_max="$END_DATE T23:59:59",
  max_results=100,
  detailed=True
)
```

For each day in `$DAYS`, build a schedule model:

```
DaySchedule {
  date: YYYY-MM-DD,
  events: [{ id, summary, start, end, colorId, duration_min }],
  cyan_minutes: int,      // sum of duration for colorId="7" events
  dw_yellow_minutes: int, // sum of existing colorId="5" DW events
  dw_gray_present: bool,  // whether a colorId="8" DW noon block exists
  total_busy_minutes: int,
  free_minutes: int,      // 9am–6pm = 540 min, minus all events
  available_for_focus: int, // free_minutes minus max(90 - cyan_minutes, 0)
  noon_slot_status: "free_60" | "free_30" | "blocked"
}
```

**Noon slot logic** (12:00–13:00 = 60 min):
- If existing events consume ≥ 60 min of 12:00–13:00 → `"blocked"`
- If existing events consume 30–59 min → `"free_30"` (book a 30-min gray DW)
- Otherwise → `"free_60"` (book a 60-min gray DW)

**90-minute buffer logic**:
- Each day must keep at least 90 min open for meetings.
- If `cyan_minutes >= 90`, the buffer is already satisfied — no constraint.
- Otherwise, cap new focus blocks so that `total_busy_minutes + new_blocks ≤ (540 - 90)`.

### 2C — Fetch Asana tasks assigned to the user

```
search_tasks(
  assignee_any="me",
  completed=false,
  due_on_before="$END_DATE"
)
```

Compare results against `$TASKS` to identify:
- Tasks in `$TASKS` that already exist in Asana → record their GIDs
- Tasks in `$TASKS` with no Asana match → flag as `missing_from_asana`
- Asana tasks due within the window not yet in `$TASKS` → flag as `asana_orphans`

---

## Phase 3 — Review and gap-fill (interactive)

Present findings from Phase 2 to the user. Keep this tight — bullets only:

### 3A — Wrap-surfaced gaps

> **Things from today that may belong in your plan:**
> - [item]: [one-sentence why it seems relevant]
> - ...

Ask: "Do any of these belong in your focus list for $HORIZON? I can add them."
If the user says yes to any, append them to `$TASKS`.

### 3B — Asana orphans

> **Asana tasks due this period that aren't in your focus list:**
> - [task name] (due [date])
> - ...

Ask: "Should any of these be in your plan? If so, I'll add them."

### 3C — Calendar summary

Show a compact table of available focus time per day:

```
| Day      | Meetings (cyan) | Available for focus | Noon slot |
|----------|----------------|---------------------|-----------|
| Mon 5/13 | 90 min         | 270 min             | free 60   |
| Tue 5/14 | 45 min         | 225 min             | free 30   |
| ...      | ...            | ...                 | ...       |
```

No action needed here — this is context for Phase 4.

---

## Phase 4 — Asana sync (interactive, before calendar booking)

Present the Asana sync summary:

### 4A — Missing tasks

If `missing_from_asana` is non-empty:
> "These tasks from your focus list don't have Asana entries:
> - [task name]
> - ...
> Want me to create them in Asana?"

If yes, create each via:
```
create_tasks(
  tasks=[{ name: "...", notes: "...", due_on: "$END_DATE", assignee: "me" }],
  default_assignee="me"
)
```
Store returned GIDs back into the matching `$TASKS` entries.

### 4B — Tasks to break out

If the user broke any originally-vague task into subtasks during Phase 1, and
that original task already exists in Asana:

> "You broke '[original task]' into smaller tasks. Want me to update Asana —
> either convert it to subtasks or replace the original task with the smaller
> ones?"

Let the user decide the approach, then execute accordingly using `update_tasks`
and/or `create_tasks` with `parent` set to the original task GID for subtasks.

Do not proceed to Phase 5 until the user has answered the Asana sync questions
(or explicitly said "skip Asana").

---

## Phase 5 — Calendar blocking (only after explicit user go-ahead)

Do not book anything until the user says "go ahead", "book it", "yes", "looks
good", or similar confirmation after seeing the proposed schedule.

### 5A — Build the proposed schedule

Distribute `$TASKS` across `$DAYS` as focus blocks. Rules:

1. **Block duration**: 30 min or 60 min only. Group multiple short tasks into a
   single block when they logically fit together (same theme, sequential steps).
   Never exceed 60 min per block.
2. **Single-task blocks are fine** — but prefer grouping when tasks are related
   and fit within 60 min combined.
3. **If a task needs > 60 min** to complete, split it across multiple 30- or
   60-min blocks. If you find yourself splitting a task across 3+ blocks, flag
   it as likely needing further breakdown.
4. **Honor availability**: Schedule only within `available_for_focus` minutes
   per day. Respect the 90-min buffer (unless `cyan_minutes >= 90`).
5. **Avoid 12:00–13:00**: That window is reserved for the gray DW noon block.
   Schedule focus blocks in the working day (assume 9:00–18:00 window) but skip
   noon unless the noon block calculation explicitly leaves room.
6. **Pack earlier in the day** when possible — prefer morning slots over afternoon.
7. **Event title**: Always `"DW"`. Tasks go in the description, one per line.

Present the proposed schedule as a table before booking:

```
| Day      | Time        | Duration | Tasks |
|----------|-------------|----------|-------|
| Mon 5/13 | 9:00–10:00  | 60 min   | Review auth spec draft, note gaps |
| Mon 5/13 | 10:00–10:30 | 30 min   | Reply to Ben's PR review comments |
| Tue 5/14 | 9:00–10:00  | 60 min   | Draft updated roadmap sections |
| ...      | ...         | ...      | ...   |
```

Also show the noon blocks:

```
Noon "DW" blocks (gray, no description):
| Day      | Time        | Duration |
|----------|-------------|----------|
| Mon 5/13 | 12:00–13:00 | 60 min   |
| Tue 5/14 | 12:00–12:30 | 30 min   | (12:30 already blocked)
| Wed 5/15 | —           | skipped  | (fully blocked)
```

Ask: "Does this look right? Say 'go ahead' and I'll book everything."

### 5B — Book focus blocks (after confirmation)

For each yellow DW block in the proposed schedule:

```
manage_event(
  action="create",
  summary="DW",
  start_time="<YYYY-MM-DDThh:mm:ss>",
  end_time="<YYYY-MM-DDThh:mm:ss>",
  timezone="<user_timezone>",
  description="<task 1 name>\n<task 2 name>",
  color_id="5",
  user_google_email="<user_email>"
)
```

For each gray DW noon block:

```
manage_event(
  action="create",
  summary="DW",
  start_time="<YYYY-MM-DDT12:00:00>",
  end_time="<YYYY-MM-DDT12:30:00 or 13:00:00>",
  timezone="<user_timezone>",
  color_id="8",
  user_google_email="<user_email>"
)
```

**Skip** a noon block for a given day if:
- `noon_slot_status = "blocked"` for that day
- A gray DW noon block already exists (`dw_gray_present = true`)

Create all events in parallel where the calendar API allows. After all bookings
complete, confirm: "All done — N focus blocks and M noon blocks added."

---

## State across phases

Track these throughout the skill:

| Variable | Type | Set in |
|---|---|---|
| `$HORIZON` | string | Phase 0 (parsed from args) |
| `$START_DATE`, `$END_DATE` | YYYY-MM-DD | Phase 0 |
| `$DAYS` | array of YYYY-MM-DD | Phase 0 |
| `$TASKS` | array of task objects | Phase 1, updated in Phase 3 |
| `$DAY_SCHEDULES` | array of DaySchedule | Phase 2B |
| `missing_from_asana` | array of task names | Phase 2C |
| `asana_orphans` | array of Asana task objects | Phase 2C |
| `user_google_email` | string | Ask once if not known from memory |
| `user_timezone` | string | From calendar events or ask once |

---

## Guardrails

- **Never book calendar events until Phase 5 is explicitly confirmed.** Showing a
  proposed schedule is not confirmation — wait for an affirmative reply.
- **Never create or modify Asana tasks until Phase 4 confirmation.**
- **Never proceed to Phase 2 until `$TASKS` is confirmed in Phase 1.** Phase 2
  runs in the background but results are not presented until Phase 3.
- **Preserve existing calendar events** — only add new DW blocks; do not modify or
  delete existing events.
- If the user's available focus time across the full window is less than the
  estimated time for `$TASKS`, flag this explicitly: "You have ~X hours of focus
  time available but your task list looks like ~Y hours. Want to pare down or push
  some tasks out?"
- **colorId reference**:
  - `"5"` = YELLOW → user's DW focus blocks
  - `"7"` = CYAN → meetings (do not create these; read-only for buffer calc)
  - `"8"` = GRAY → noon DW anchor blocks

---

## User email and timezone

If `user_google_email` is not in memory, ask once at the very start and reuse
throughout. If `user_timezone` is not determinable from calendar event data, ask
once.

---

## Gotchas

**Phase 2 runs concurrently with Phase 1 output** — start firing Phase 2 tool
calls as soon as you present the Phase 1 sharpened task list to the user, so
results are ready by the time they confirm.

**Noon slot overlap detection** — check all events in the 12:00–13:00 window,
sum their durations, and compute remaining free time. An event that starts at
11:45 and ends at 12:30 consumes 30 min of the noon window.

**`color_id` vs `colorId`** — the workspace MCP `manage_event` tool may accept
either `color_id` or `colorId` as the parameter name. Try `color_id` first; if
it doesn't apply, try `colorId`.

**Cyan meeting detection** — use `colorId` field from `get_events` results.
If the field is absent (some events don't have a colorId set), do not count
those as cyan meetings.

**Wrap data reuse** — the wrap skill makes many parallel API calls. If wrap
results are already available from earlier in the session, reuse them rather
than refetching.

**Available focus window** — assume 9:00–18:00 as the working day (540 min).
Subtract all existing events. Then subtract `max(90 - cyan_minutes, 0)` as the
meeting buffer. The remainder is `available_for_focus`.

**Don't double-book** — before placing any focus block, check that the target
slot has no existing events. Gaps between back-to-back meetings may be shorter
than they appear if event end times are rounded.
