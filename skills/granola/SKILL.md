---
name: granola
description: "Reference this skill whenever a task requires reading the user's Granola meeting notes. Routes between the Granola MCP tools, gives plan-aware guidance, and covers common gotchas (account/workspace mismatch, free-plan limits, transcript-only operations)."
compatibility: "Claude Code, Claude Desktop, claude.ai — any surface that supports custom MCP connectors"
---

# Granola Notes Access (via MCP)

## Why this skill exists

The user's Granola meeting notes are accessed through the **official Granola MCP**,
not through the local filesystem. The Electron app stores its data in a Chromium
LevelDB store (`~/Library/Application Support/Granola/IndexedDB/`) which is not
meant to be read directly. The MCP gives you clean, structured access — use it.

Multiple skills in this plugin may need Granola access. This file is the single
source of truth for which MCP tool to use for each kind of task.

---

## Setup (one-time)

If the Granola MCP tools are not available in the current session, the user
needs to install the connector. Pointers by surface:

| Surface | How to install |
|---|---|
| Claude Code | `claude mcp add granola --transport http https://mcp.granola.ai/mcp`, then `/mcp` → select `granola` → Authenticate |
| Claude Desktop / claude.ai | Settings → Connectors → search "Granola" → Connect |
| Other MCP clients | Connect to `https://mcp.granola.ai/mcp` (Streamable HTTP, OAuth 2.0) |

Granola MCP requires a paid Claude plan. On Team/Enterprise, an admin may need
to approve the connector first.

---

## Tool selection

The MCP exposes six tools. **Pick the narrowest one that answers the question** —
this saves tokens and keeps responses fast.

| Tool | Use for | Notes |
|---|---|---|
| `list_meetings` | "What meetings did I have last week?" — metadata only (ID, title, date, attendees) | Cheap. Always start here when scoping by time, person, or folder. |
| `get_meetings` | Content-level questions: "What did we decide about X?", "Summarize the kickoff" | Returns enhanced notes for the meetings you ask about. Pass meeting IDs from `list_meetings`. |
| `get_meeting_transcript` | Verbatim quotes, "who said what", precise wording | **Paid plans only.** Transcripts are large — only fetch when the task genuinely needs the raw text. |
| `query_granola_meetings` | Fuzzy / open-ended: "Have we talked about pricing recently?", "Any concerns raised about the migration?" | Backed by Granola's chat-with-meetings feature. Good for discovery when you don't know which meeting to look at. |
| `list_meeting_folders` | "What folders do I have?", folder-scoped queries | **Paid plans only.** Use the returned folder IDs to filter `list_meetings`. |
| `get_account_info` | Verifying which Granola account/workspace MCP is connected to | Run this first if other tools return suspiciously empty results. |

Tool names will appear namespaced in your tool list (e.g. `Granola:list_meetings`).
Match by suffix.

---

## Standard workflows

### "What meetings did I have with $PERSON last week?"
```
list_meetings(date_range="last week", attendee="$PERSON")
```
Stop here unless the user asks about content. Returning the list is usually enough.

### "What did we decide in the $PROJECT kickoff?"
1. `list_meetings` to find the meeting → get the ID
2. `get_meetings(ids=[<id>])` to pull the enhanced notes
3. Answer from the notes content

Skip step 1 if the user has already named or linked the meeting.

### "Find every meeting where we discussed $TOPIC"
```
query_granola_meetings("$TOPIC")
```
This is what the chat-with-meetings tool is for. Don't try to brute-force this
by listing all meetings and filtering manually — it'll burn tokens and miss
semantic matches.

### "Give me the exact quote where $PERSON said $THING"
1. Find the meeting (`list_meetings` or `query_granola_meetings`)
2. `get_meeting_transcript(meeting_id=<id>)` — paid plans only
3. Search the returned transcript for the quote

If the user is on the Free plan, `get_meeting_transcript` will fail. Fall back
to `get_meetings` and tell the user transcripts require a paid plan.

### "What are my open action items?"
```
query_granola_meetings("open action items assigned to me")
```
Granola's chat tool understands this kind of cross-meeting synthesis natively.

---

## Plan-aware behavior

| Plan | Available |
|---|---|
| Free (Basic) | Notes from the last 30 days only. No transcripts. No folder listing. |
| Paid (Pro / Business / Enterprise) | All notes, shared notes, transcripts, folders. Higher rate limits. |

If a tool errors with a plan-related message, surface it to the user plainly
rather than retrying. Don't suggest workarounds that try to scrape the local
LevelDB store — that's fragile and not what the user asked for.

---

## Troubleshooting

**Empty results when you expect data** — call `get_account_info` first. Two
common causes:
- *Right email, wrong workspace*: the user has multiple Granola workspaces and
  the wrong one is active. They need to switch in the Granola desktop app.
- *Wrong email entirely*: the connector was authenticated with the wrong
  Granola account. They'll need to disconnect and reconnect.

**"No tools available" in Claude** — the connector is installed but the session
hasn't picked up the tools. The user needs to disconnect and reconnect the
Granola connector at claude.ai/customize/connectors.

**OAuth flow fails with "user has not created a Granola account yet"** — they
authenticated with an email that doesn't match a Granola account. They should
check the email under Granola desktop → Settings (⌘,) and re-authenticate
with that exact address.

---

## Consuming skills: how to reference this file

In your skill's SKILL.md, add:

```markdown
## Notes access
Before reading the user's Granola meeting notes, read
`<path>/granola/SKILL.md` for tool selection guidance and plan-aware behavior.
```

Replace `<path>` with wherever this skill lives in your skills directory
(e.g. `~/.claude/skills/granola/SKILL.md` for personal skills in Claude Code).

---

## Caveats

- **Don't read the local LevelDB store.** `~/Library/Application Support/Granola/IndexedDB/`
  is Chromium internals and not a stable interface. The MCP is the supported path.
- **Privacy.** Meeting notes and transcripts may contain sensitive content. Don't
  cache or persist them beyond the immediate task. Pull what you need, answer,
  move on.
- **Transcripts are large.** Only fetch `get_meeting_transcript` when the task
  actually needs verbatim text. For summaries and decisions, `get_meetings` is
  enough.
- **Rate limits.** Granola MCP averages ~100 requests/minute across all tools.
  Don't loop `get_meetings` over hundreds of IDs — batch where the API supports
  it, and prefer `query_granola_meetings` for cross-meeting synthesis.

---

## Alternatives (not recommended for skills)

- **Granola Personal API** (https://docs.granola.ai/help-center/sharing/integrations/personal-api):
  programmatic access without per-user OAuth. Useful for background scripts; for
  interactive skill use it's strictly more work than MCP.
- **theantichris/granola CLI** (https://github.com/theantichris/granola):
  third-party tool that reads the local LevelDB store. Brittle, unsupported,
  superseded by the official MCP.