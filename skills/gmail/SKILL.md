---
name: gmail
description: "Read, search, send, and manage Gmail messages and labels via the Google Workspace MCP. Routes /gmail $ARGUMENTS to the right tool for searching, reading, sending, replying, and organizing email."
compatibility: "Claude Code — requires workspace-mcp installed (see .mcp.json)"
---

# Gmail (via Google Workspace MCP)

Gmail is accessed through the **workspace MCP** server. Tool names appear as
`workspace:<tool_name>` — match by suffix. All tools require `user_google_email`
(the authenticated user's Gmail address). If not known, ask once and reuse.

The current MCP config uses `--tool-tier core`. Tools marked **extended** or
**complete** below require upgrading the tier in `.mcp.json`.

---

## Tool selection

| Tool | Tier | Use for | Notes |
|---|---|---|---|
| `search_gmail_messages` | core | Find messages by sender, subject, date, label, etc. | Uses Gmail search syntax. Returns message IDs — follow up with content tools. |
| `get_gmail_message_content` | core | Full content of a single message | Use `body_format="text"` (default) for plain text, `"html"` to preserve layout. |
| `get_gmail_messages_content_batch` | core | Content of 2–25 messages at once | Pass message IDs from `search_gmail_messages`. Up to 25 per call. |
| `send_gmail_message` | core | Send a new email or reply to a thread | Supports `thread_id`/`in_reply_to` for replies, file attachments, HTML body. |
| `draft_gmail_message` | extended | Save a draft without sending | Returns draft ID. |
| `get_gmail_thread_content` | extended | Full conversation thread | Returns all messages in a thread as a single blob. |
| `get_gmail_attachment_content` | extended | Download an attachment | Pass `message_id` + `attachment_id`. |
| `modify_gmail_message_labels` | extended | Archive, mark read/unread, label/unlabel one message | Pass `add_label_ids` / `remove_label_ids`. Use label IDs from `list_gmail_labels`. |
| `batch_modify_gmail_message_labels` | complete | Label/unlabel many messages at once | Same as above but accepts a list of `message_ids`. |
| `list_gmail_labels` | extended | See all labels and their IDs | Run this first when you need a label ID. |
| `manage_gmail_label` | extended | Create, rename, or delete a label | `action`: "create", "update", "delete". |
| `list_gmail_filters` | extended | See all inbox filters | |
| `manage_gmail_filter` | extended | Create or delete a filter | `action`: "create" or "delete". |

---

## $ARGUMENTS routing

| Request pattern | Primary tool |
|---|---|
| "find emails from X", "search for emails about Y" | `search_gmail_messages(query="from:X")` |
| "show me that email" / "read email ID X" | `get_gmail_message_content(message_id=X)` |
| "read these emails" (multiple IDs) | `get_gmail_messages_content_batch(message_ids=[...])` |
| "send email to X about Y" | `send_gmail_message` |
| "reply to this email" | `send_gmail_message(thread_id=..., in_reply_to=...)` |
| "draft an email" | `draft_gmail_message` |
| "show me the full thread" | `get_gmail_thread_content(thread_id=...)` |
| "archive this email" | `modify_gmail_message_labels(remove_label_ids=["INBOX"])` |
| "mark as read" | `modify_gmail_message_labels(remove_label_ids=["UNREAD"])` |
| "what labels do I have" | `list_gmail_labels` |

---

## Standard workflows

### Search and read emails

```
# Search
search_gmail_messages(
  query="from:someone@example.com is:unread",
  user_google_email="user@gmail.com",
  page_size=10
)
# → returns list of {id, threadId, subject, from, date}

# Read one
get_gmail_message_content(
  message_id="<id from search>",
  user_google_email="user@gmail.com"
)

# Or read several at once (up to 25)
get_gmail_messages_content_batch(
  message_ids=["id1", "id2", "id3"],
  user_google_email="user@gmail.com"
)
```

### Send a new email

```
send_gmail_message(
  to="recipient@example.com",
  subject="Re: Project Update",
  body="Hi,\n\nThanks for the update...",
  user_google_email="user@gmail.com"
)
```

### Reply to an existing thread

```
# 1. Find the message to get thread_id and Message-ID header
get_gmail_message_content(message_id="<id>", user_google_email="...")

# 2. Send reply
send_gmail_message(
  to="...",
  subject="Re: ...",
  body="...",
  thread_id="<threadId>",
  in_reply_to="<Message-ID header>",
  references="<Message-ID header>",
  user_google_email="..."
)
```

### Archive emails (remove from inbox)

```
# Get message IDs first via search_gmail_messages
modify_gmail_message_labels(
  message_id="<id>",
  remove_label_ids=["INBOX"],
  user_google_email="..."
)
```

---

## Gmail search syntax

Pass any valid Gmail query to `search_gmail_messages(query=...)`:

| Filter | Example |
|---|---|
| Sender | `from:boss@example.com` |
| Recipient | `to:me` |
| Subject | `subject:weekly update` |
| Unread | `is:unread` |
| Date range | `after:2026/01/01 before:2026/02/01` |
| Has attachment | `has:attachment` |
| Label | `label:inbox` or `in:inbox` |
| Thread | `thread:123abc` |
| Combine | `from:sales is:unread after:2026/05/01` |

---

## Gotchas

**`search_gmail_messages` returns IDs, not content** — the result is a list of
message metadata. Always follow up with `get_gmail_message_content` or
`get_gmail_messages_content_batch` to read body text.

**Replying requires `thread_id` and `in_reply_to`** — without these, Gmail
creates a new thread instead of appending to the existing one. Both values are
in the original message's content response (`threadId` and `Message-ID` header).

**Label IDs vs label names** — `modify_gmail_message_labels` and
`batch_modify_gmail_message_labels` accept label **IDs**, not names. System
labels use fixed IDs (`INBOX`, `UNREAD`, `STARRED`, `SPAM`, `TRASH`). For
custom labels, call `list_gmail_labels` first to get the ID.

**`body_format="html"` for layout-sensitive emails** — use `"text"` (default)
for plain reading. Switch to `"html"` only when you need to see newsletter
formatting, table structure, or extract links. HTML bodies can be very large.

**Tier gating** — `draft_gmail_message`, `get_gmail_thread_content`,
`modify_gmail_message_labels`, and label management tools require `--tool-tier
extended`. The current MCP config is `--tool-tier core`. To unlock, edit
`.mcp.json` and change the arg.

---

## Caveats

- Do not cache or persist email content, sender info, or attachments beyond the
  immediate task.
- `page_size` defaults to 10 in `search_gmail_messages`. Use `page_token` for
  pagination when you need more results.
- Sending email is irreversible. Confirm recipient and content before calling
  `send_gmail_message`. Prefer `draft_gmail_message` when the user wants to
  review first.
