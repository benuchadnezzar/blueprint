---
name: wrap
description: "End-of-day or end-of-week synthesis. Pulls meetings (Granola), Slack messages and mentions, Gmail (filtered), Asana mentions and due tasks, and Confluence mentions for the current day or week. Outputs a 100–200 word summary, suggests new Asana tasks, surfaces followup gaps against the next 30 days of calendar, and flags urgent emails/Slacks needing a reply. Invoke with /wrap day or /wrap week."
compatibility: "Claude Code — requires Granola MCP, workspace-mcp, Slack MCP, Asana MCP, Atlassian MCP"
---

# Wrap (Daily / Weekly Synthesis)

`$ARGUMENTS` is either `day` or `week`. If omitted, default to `day`.

---

## Step 0 — Determine date range

Calculate dates based on argument and today's date:

| Argument | `since` (inclusive) | `until` (inclusive) |
|---|---|---|
| `day` | today at 00:00 local | today at 23:59 local |
| `week` | the most recent Monday at 00:00 local | today at 23:59 local |

Express as:
- ISO date string: `YYYY-MM-DD` for tools that take date-only filters
- RFC3339: `YYYY-MM-DDT00:00:00Z` / `YYYY-MM-DDT23:59:59Z` for tools that require timestamps

Store these as `$SINCE` and `$UNTIL` for the data gathering phase.

---

## Step 1 — Gather data (all sources in parallel)

Fire all of the following at the same time. If any single source errors or
returns empty, note it and continue — do not abort the whole wrap.

### 1A — Granola meetings

```
list_meetings(date_range="today"   # or "this_week" when $ARGUMENTS=week)
```

If meetings are found, fetch content for all of them:

```
get_meetings(ids=[<id>, <id>, ...])
```

Extract: meeting titles, attendees, key decisions, action items, and open loops.

### 1B — Slack: today/week activity

Two parallel Slack searches (both require `slack_search_public_and_private`):

**1B-i — Messages directed at the user** (DMs, replies, threads where they're mentioned):

```
slack_search_public_and_private(
  query="to:me after:$SINCE_DATE"
)
```

**1B-ii — Channel mentions** (the user's Slack display name @-mentioned):
This requires knowing the user's Slack username. If not known, call
`slack_search_users` with the user's name or email to find it first,
then search:

```
slack_search_public_and_private(
  query="@<slack_username> after:$SINCE_DATE"
)
```

**1B-iii — Unread DMs** (regardless of date — these are always relevant):

```
slack_search_public_and_private(
  query="to:me is:dm"
)
```

For each Slack result, note: channel/DM, sender, message preview, timestamp,
link/URL, and whether it appears to require a reply.

### 1C — Gmail: received emails (filtered)

```
search_gmail_messages(
  query="is:inbox to:me after:$SINCE_DATE -category:promotions -category:updates -category:social -category:forums -from:noreply -from:no-reply",
  user_google_email="<user_email>",
  page_size=25
)
```

If `user_google_email` is not known, ask the user once before proceeding.

Fetch content for up to 10 most relevant results:

```
get_gmail_messages_content_batch(
  message_ids=[...],
  user_google_email="<user_email>"
)
```

For each email, note: sender, subject, whether it requires a response from the user,
and whether it's time-sensitive.

### 1D — Asana: mentions and due tasks

Two parallel Asana queries:

**1D-i — Recent mentions** (tasks where the user was tagged / added as follower):

```
search_tasks(
  followers_any="me",
  modified_on_after="$SINCE_DATE",
  completed=false
)
```

**1D-ii — Tasks due this week or overdue**:

```
search_tasks(
  assignee_any="me",
  completed=false,
  due_on_before="$END_OF_WEEK"   # this Friday's date
)
```

`$END_OF_WEEK` = the coming Friday (or today if today is Friday/Saturday/Sunday
and $ARGUMENTS=day).

### 1E — Confluence: mentions

```
searchConfluenceUsingCql(
  cloudId="justworks.atlassian.net",
  cql='mention = currentUser() AND lastModified >= "$SINCE_DATE"',
  limit=10
)
```

For each result, note: page title, space, who mentioned the user, and the URL.

---

## Step 2 — Synthesize (100–200 words)

Write a summary with **exactly** these sections. Keep the total body between
100 and 200 words — be ruthless about what makes the cut.

```
## [Day/Week] Wrap — [Date or Date Range]

**Meetings:** [1–2 sentences: what happened, key outcomes or decisions]

**Slack:** [1 sentence: notable conversations, important threads, any urgent pings]

**Email:** [1 sentence: what landed that matters, any threads needing response]

**Asana:** [1 sentence: overdue/due tasks, whether anything was just assigned/mentioned]

**Confluence:** [1 sentence or "Nothing today" if empty]
```

If a section is empty, write "Nothing [today/this week]." rather than omitting it.

---

## Step 3 — Suggested new Asana tasks

Review all gathered data for **commitments, open loops, and follow-throughs**
that don't have a corresponding Asana task:

Look for:
- Things said in meetings: "I'll send...", "I'll check on...", "Let me follow up..."
- Email threads where you're the expected next actor
- Slack messages waiting on you to respond or act
- Confluence pages where you were mentioned with an implicit ask

For each candidate, output:

```
**Suggested task:** [Task name]
  Source: [meeting title / email subject / Slack channel + date]
  Why: [one sentence on what action this maps to]
```

After listing all suggestions, offer:

> "Want me to create any of these in Asana? Just say which ones (by number)
> and I'll use the Asana skill to add them."

If the user confirms, call `create_tasks` per the Asana skill for each
confirmed item, using `default_assignee="me"`.

---

## Step 4 — Followup gaps

### 4A — Identify expected followups

From the data gathered, list people or topics that warrant a scheduled followup:
- A meeting that ended with "let's reconnect" but no concrete next step
- An email thread that implied a check-in call
- A Slack conversation about something with a pending outcome
- An Asana task that's waiting on someone else and may need a nudge

For each expected followup, note the person(s), topic, and rough timeframe
("within 1 week", "2 weeks", "next month").

### 4B — Scan calendar for existing followups

Fetch the next 30 days of calendar events:

```
get_events(
  user_google_email="<user_email>",
  calendar_id="primary",
  time_min="$TODAY_RFC3339",
  time_max="$THIRTY_DAYS_OUT_RFC3339",
  max_results=50,
  query=""
)
```

For each expected followup from 4A, check whether a calendar event already
covers it (meeting with the relevant person, 1:1 already scheduled, etc.).

### 4C — Report gaps

Output a table of followup gaps — expected followups with no calendar coverage:

```
| Followup | With | Timeframe | Source |
|---|---|---|---|
| Reconnect on X proposal | Alice Smith | Within 1 week | [Meeting: Project Kickoff] |
| Check in on vendor decision | Bob Jones | 2 weeks | [Email: Re: Contract Review] |
```

If all followups are already on the calendar, say so explicitly.

After listing gaps, offer:

> "Want me to create calendar events for any of these? I can use the Calendar
> skill to schedule them."

---

## Step 5 — Urgent reply surface

List messages (email or Slack) that appear to need a reply — ordered by
urgency (explicit deadline or "today" language first, then by recency):

```
**[Email | Slack]** — [Sender]: "[Subject or message preview]"
  Link: [Gmail deep link or Slack message link if available]
  Why urgent: [one sentence]
```

Criteria for inclusion:
- Explicitly asks for a response from you
- Time-bounded language ("by EOD", "today", "ASAP", "before the meeting")
- You're the only recipient or the last person in the thread
- A direct question to you that went unanswered

Do not include: mass-addressed emails, FYI messages, newsletters that slipped
through, automated notifications, or threads where someone else already replied
covering your ground.

---

## Output order

1. **Summary** (Step 2, 100–200 words)
2. **Suggested Asana tasks** (Step 3)
3. **Followup gaps** (Step 4)
4. **Urgent replies** (Step 5)

---

## Sourcing other skills

When this skill needs to take an action the user approves:

- **Create Asana tasks** → follow the `asana` skill: `create_tasks(tasks=[...], default_assignee="me")`
- **Create calendar events** → follow the `gcalendar` skill: `manage_event(action="create", ...)`
- **Read Gmail content** → follow the `gmail` skill
- **Read Granola notes** → follow the `granola` skill
- **Confluence mentions** → follow the `confluence` skill

---

## Gotchas

**Slack unread status is approximate** — the Slack MCP doesn't expose unread
counts directly. Treat "recent DMs" and "@mentions" as the proxy. The user
will know which ones they haven't seen.

**Gmail promotions filter isn't perfect** — `search_gmail_messages` with
`-category:promotions` excludes most but not all marketing email. If a
result looks like a newsletter or automated notification that slipped through,
exclude it from the summary and urgent-reply surface.

**Confluence `mention = currentUser()` scope** — this CQL filter finds pages
where the user's account is referenced via @-mention. It does not catch
comments that spell out the user's name as plain text. If it returns nothing,
fall back to `search(query="@<username> site:confluence")`.

**Asana `followers_any` as mention proxy** — being a task follower doesn't
always mean you were @mentioned; you may have added yourself. Filter out
tasks you created yourself (where `created_by_any="me"`) to reduce noise.

**Calendar scan is for primary calendar only** — if the user has separate
work/personal calendars, `calendar_id="primary"` may miss some meetings.

**Run Step 1 entirely before Step 2** — don't write the summary until all
data is in. Partial summaries are worse than a brief wait.
