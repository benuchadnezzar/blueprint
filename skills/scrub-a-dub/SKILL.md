---
name: scrub-a-dub
description: "Workspace hygiene skill. Finds newsletters/sales emails and proposes unsubscribes (never-opened senders only), bulk-archives unread email after an importance check, and walks through overdue Asana tasks one-by-one to reschedule or archive. Invoke with /scrub-a-dub."
compatibility: "Claude Code — requires workspace-mcp (--tool-tier complete), Asana MCP"
---

# Scrub-a-Dub (Workspace Hygiene)

Run all three steps in order. Each step has a safety review before any destructive action — never skip the review phase.

> **Tier requirement**: Steps 1 and 2 use `modify_gmail_message_labels` and `batch_modify_gmail_message_labels`, which require `--tool-tier complete` in the workspace MCP config (`.mcp.json`). If these tools are unavailable, report the gap and skip those sub-steps.

---

## Step 1 — Gmail: unsubscribe from newsletters and sales emails

### 2A — Find newsletter/sales senders

```
search_gmail_messages(
  query="is:inbox (unsubscribe OR \"opt out\" OR \"manage preferences\" OR \"view in browser\") -from:noreply -from:no-reply",
  user_google_email="<your-email>",
  page_size=50
)
```

Also search for patterns common to sales outreach:
```
search_gmail_messages(
  query="is:inbox (\"just following up\" OR \"quick question\" OR \"wanted to reach out\" OR \"sales\" OR \"demo\" OR \"free trial\")",
  user_google_email="<your-email>",
  page_size=25
)
```

### 2B — Check open history per sender

For each unique sender found, check whether any email from that sender has ever been opened:

```
search_gmail_messages(
  query="from:<sender_email> is:read",
  user_google_email="<your-email>",
  page_size=1
)
```

**Only flag senders where the result is empty** (zero read messages from that sender) — these are candidates for unsubscribe. Skip any sender where you've ever opened an email from them.

### 2C — Present unsubscribe candidates

```
**Unsubscribe candidates (never opened any email from these senders):**
1. [Sender name] <[email]> — [subject of most recent email]
2. ...
```

Ask: "Want me to mark any of these as spam to suppress future emails? (I can't click unsubscribe links directly — you'd need to do that manually, or I can mark them spam in Gmail which achieves a similar result.) Reply with numbers to act on, or 'all'."

### 2D — Mark selected senders as spam

For each confirmed sender, find all their messages and add the SPAM label:

```
search_gmail_messages(
  query="from:<sender_email>",
  user_google_email="<your-email>",
  page_size=100
)
```

```
batch_modify_gmail_message_labels(
  message_ids=[...],
  add_label_ids=["SPAM"],
  remove_label_ids=["INBOX"],
  user_google_email="<your-email>"
)
```

Report: "Marked N emails from [Sender] as spam."

---

## Step 2 — Gmail: review unread inbox, then archive

### 3A — Fetch unread inbox

```
search_gmail_messages(
  query="is:inbox is:unread -category:promotions -category:updates -category:social -category:forums",
  user_google_email="<your-email>",
  page_size=50
)
```

Fetch content for up to 15 most recent results:

```
get_gmail_messages_content_batch(
  message_ids=[<ids>],
  user_google_email="<your-email>"
)
```

### 3B — Flag anything important

Before archiving, present emails that look like they need attention. Criteria:
- Direct question or action request addressed to you
- Time-sensitive language ("by EOD", "today", "before the meeting", "ASAP", "deadline")
- You're the only or last recipient and no response has been sent
- Sender is a manager, direct report, or close collaborator

Output:

```
**Emails to review before archiving:**
1. From: [Sender] — "[Subject]" ([date])
   Why: [one sentence]
```

If nothing flagged: "Nothing in unread email looks like it needs your attention."

### 3C — Bulk mark read and archive

After showing the review list, ask: "Ready to mark all unread inbox emails as read and archive them? (Flagged items above will be included — you can reply to them afterward.)"

On confirmation:

```
batch_modify_gmail_message_labels(
  message_ids=[<all unread inbox message ids>],
  remove_label_ids=["UNREAD", "INBOX"],
  user_google_email="<your-email>"
)
```

Report: "Archived N emails and marked them read."

---

## Step 3 — Asana: triage overdue tasks

### 3A — Fetch overdue tasks

```
search_tasks(
  assignee_any="me",
  completed=false,
  due_on_before="<today's date YYYY-MM-DD>"
)
```

If no overdue tasks: "No overdue Asana tasks. You're caught up."

### 3B — Present each task for a decision

For each overdue task, show:

```
**[N of M] — [Task name]**
  Project: [project name]
  Due: [original due date] ([N days overdue])
  Notes: [task description, truncated to 2 sentences if long]
  Link: [task URL if available]

Options:
  r <date>  — Reschedule to a new due date (e.g., "r 2026-05-20")
  a         — Archive (mark complete)
  s         — Skip (leave as-is)
  q         — Stop triaging
```

Wait for the user's reply before moving to the next task.

### 3C — Apply decisions

**Reschedule** (`r <date>`):
```
update_tasks(tasks=[{
  "task": "<task_gid>",
  "due_on": "<new_date>"
}])
```

**Archive** (`a`):
```
update_tasks(tasks=[{
  "task": "<task_gid>",
  "completed": true
}])
```

**Skip** (`s`): move to next task without changes.

**Quit** (`q`): stop the loop and report how many tasks were rescheduled, archived, and skipped.

### 3D — Summary

After triaging all tasks (or on `q`):

```
**Asana triage complete:**
- Rescheduled: N tasks
- Archived: N tasks
- Skipped: N tasks
- Remaining overdue: N tasks
```

---

## Output order

1. **Step 1** — Newsletter/sales unsubscribe candidates (interactive)
2. **Step 2** — Unread email importance review + archive confirmation
3. **Step 3** — Overdue Asana triage (interactive, one task at a time)

Steps 1–2 run sequentially. Step 3 is fully interactive — pause between each task and wait for the user's input.

---

## Gotchas

**`batch_modify_gmail_message_labels` requires `--tool-tier complete`** — if workspace MCP is running at `core` or `extended`, label modification will fail. Update `.mcp.json` args to `["workspace-mcp", "--tool-tier", "complete"]` and restart Claude Code to unlock this.

**Unsubscribe links require manual action** — the MCP can't click links. Marking as spam in Gmail achieves the same suppression effect and is reversible by checking the Spam folder.

**Archive is reversible** — Gmail archive removes the INBOX label but the message stays searchable. "Archive" here is safe; it is not deletion.

**Asana "archive" = mark complete** — Asana has no true archive. Marking a task complete removes it from active views while keeping the history. If you want to fully delete a task, do that manually in Asana.

**`due_on_before` with today's date** — use today's date string (`YYYY-MM-DD`), not yesterday's, so that tasks due today-but-not-yet-done are included in the overdue sweep.
