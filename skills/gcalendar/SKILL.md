---
name: gcalendar
description: "Read, create, update, delete, and RSVP to Google Calendar events via the Google Workspace MCP. Routes /gcalendar $ARGUMENTS to the right tool for listing calendars, fetching events, managing events, and checking availability."
compatibility: "Claude Code — requires workspace-mcp installed (see .mcp.json)"
---

# Google Calendar (via Google Workspace MCP)

Calendar is accessed through the **workspace MCP** server. Tool names appear as
`workspace:<tool_name>` — match by suffix. All tools require `user_google_email`
(the authenticated user's email). If not known, ask once and reuse.

The current MCP config uses `--tool-tier core`. Tools marked **extended** below
require upgrading the tier in `.mcp.json`.

---

## Tool selection

| Tool | Tier | Use for | Notes |
|---|---|---|---|
| `list_calendars` | core | Discover all calendars the user has access to | Returns calendar names, IDs, and primary status. Run first when you need a non-primary `calendar_id`. |
| `get_events` | core | Fetch events by time range, ID, or keyword search | Primary read tool. Defaults to `calendar_id="primary"`. |
| `manage_event` | core | Create, update, delete, or RSVP to an event | Single unified action tool. `action` is "create", "update", "delete", or "rsvp". |
| `query_freebusy` | extended | Check free/busy availability for one or more calendars | Use before scheduling to avoid conflicts. Returns busy intervals. |
| `create_calendar` | extended | Create a new secondary calendar | Use for project or team calendars. |
| `manage_out_of_office` | extended | Create/list/update/delete OOO blocks | |
| `manage_focus_time` | extended | Create/list/update/delete focus time blocks | |

---

## $ARGUMENTS routing

| Request pattern | Primary tool |
|---|---|
| "what's on my calendar today / this week" | `get_events(time_min=..., time_max=...)` |
| "find event X" | `get_events(query="X")` |
| "show me event ID X" | `get_events(event_id="X")` |
| "create an event" | `manage_event(action="create", ...)` |
| "update / reschedule event X" | `manage_event(action="update", event_id="X", ...)` |
| "cancel / delete event X" | `manage_event(action="delete", event_id="X")` |
| "RSVP yes/no/maybe to event X" | `manage_event(action="rsvp", event_id="X", response="accepted|declined|tentative")` |
| "am I free Thursday afternoon?" | `query_freebusy(time_min=..., time_max=...)` |
| "what calendars do I have?" | `list_calendars` |

---

## Standard workflows

### Fetch today's events

```
get_events(
  user_google_email="user@gmail.com",
  calendar_id="primary",
  time_min="2026-05-09T00:00:00Z",
  time_max="2026-05-09T23:59:59Z",
  max_results=25
)
```

Use RFC3339 format. `time_min` defaults to now if omitted.

### Search events by keyword

```
get_events(
  user_google_email="user@gmail.com",
  query="all-hands",
  time_min="2026-05-01",
  time_max="2026-06-01"
)
```

### Create an event

```
manage_event(
  action="create",
  summary="Team Sync",
  start_time="2026-05-15T10:00:00",
  end_time="2026-05-15T10:30:00",
  timezone="America/New_York",
  attendees=["alice@example.com", "bob@example.com"],
  description="Weekly check-in",
  add_google_meet=True,
  user_google_email="user@gmail.com"
)
```

`timezone` is required when start/end times don't include a UTC offset.

### Update an event

```
# 1. Find the event ID via get_events
get_events(user_google_email="...", query="Team Sync", time_min=...)

# 2. Update it
manage_event(
  action="update",
  event_id="<event_id>",
  start_time="2026-05-15T11:00:00",
  end_time="2026-05-15T11:30:00",
  timezone="America/New_York",
  user_google_email="..."
)
```

Only pass the fields you want to change — unset fields are preserved.

### Delete an event

```
manage_event(
  action="delete",
  event_id="<event_id>",
  send_updates="all",   # notify attendees
  user_google_email="..."
)
```

### RSVP to an event

```
manage_event(
  action="rsvp",
  event_id="<event_id>",
  response="accepted",   # or "declined" or "tentative"
  rsvp_comment="See you there!",
  user_google_email="..."
)
```

### Check availability before scheduling

```
query_freebusy(
  user_google_email="user@gmail.com",
  time_min="2026-05-15T09:00:00Z",
  time_max="2026-05-15T17:00:00Z",
  calendar_ids=["primary", "other-calendar-id"]
)
```

Returns busy intervals for each calendar. Schedule in the gaps.

---

## Gotchas

**`manage_event` action is required** — always pass `action` explicitly: "create",
"update", "delete", or "rsvp". Forgetting it causes an error.

**`event_id` is required for update/delete/rsvp** — get the ID via `get_events`
first. Event IDs look like `abc123xyz456@google.com` or a shorter opaque string.

**Time format** — all times are RFC3339. For date-only events (all-day), use
`"2026-05-15"`. For timed events, use `"2026-05-15T10:00:00"` plus `timezone`
or include the UTC offset: `"2026-05-15T10:00:00-05:00"`.

**Non-primary calendars need a `calendar_id`** — call `list_calendars` first to
get the ID. The primary calendar can always be referenced as `"primary"`.

**`send_updates` controls attendee notifications** — defaults to `"all"` for
create. Pass `"none"` to silently update without emailing attendees.

**Recurring events** — updating one occurrence changes only that occurrence.
To modify the series, you'll need the series root event ID and typically must
set `recurrence` again.

**Tier gating** — `query_freebusy`, `create_calendar`, `manage_out_of_office`,
and `manage_focus_time` require `--tool-tier extended`.

---

## Caveats

- Do not cache event IDs or calendar IDs beyond the immediate session — they
  remain stable but the user may have different events in future conversations.
- `max_results` defaults to 25 in `get_events`. Use `detailed=True` to include
  full description, attendees, and attachments.
- Deleting an event is immediate and irreversible from Claude's perspective.
  Confirm with the user before calling `manage_event(action="delete")`.
