---
name: gdrive
description: "Search, read, create, upload, and share files and folders in Google Drive via the Google Workspace MCP. Routes /gdrive $ARGUMENTS to the right tool for file discovery, content access, upload, sharing, and permission management."
compatibility: "Claude Code — requires workspace-mcp installed (see .mcp.json)"
---

# Google Drive (via Google Workspace MCP)

Drive is accessed through the **workspace MCP** server. Tool names appear as
`workspace:<tool_name>` — match by suffix. All tools require `user_google_email`
(the authenticated user's email). If not known, ask once and reuse.

The current MCP config uses `--tool-tier core`. Tools marked **extended** or
**complete** below require upgrading the tier in `.mcp.json`.

---

## Tool selection

| Tool | Tier | Use for | Notes |
|---|---|---|---|
| `search_drive_files` | core | Find files and folders by name, type, or Drive query | Searches personal + shared drives by default. Use `file_type` filter for speed. |
| `get_drive_file_content` | core | Read file content | Handles Docs (text), Sheets (CSV), Slides, PDFs, Office formats (.docx/.xlsx), images (base64). |
| `get_drive_file_download_url` | core | Get a short-lived download URL for any file | Use when the user needs to download a file rather than read it in context. |
| `create_drive_file` | core | Create a new file in Drive | Pass `content` directly or `fileUrl` to fetch from a URL. `mime_type` defaults to `"text/plain"`. |
| `create_drive_folder` | core | Create a new folder | Returns the folder ID for use as `parent_folder_id` in subsequent creates. |
| `import_to_google_doc` | core | Convert Markdown / DOCX / TXT / HTML / RTF / ODT to a native Google Doc | Best path for rich-text content. Drive auto-converts format. |
| `get_drive_shareable_link` | core | Get the shareable link for a file or folder | Returns current link + sharing status. |
| `list_drive_items` | extended | Browse folder contents | Pass `folder_id`; use `"root"` for the top level. |
| `copy_drive_file` | extended | Duplicate a file | Returns the new file ID. |
| `update_drive_file` | extended | Overwrite a file's content or rename it | For native Docs/Sheets, prefer their dedicated tools. |
| `manage_drive_access` | extended | Share, update permissions, revoke, or transfer ownership | Single unified action tool. `action`: "grant", "grant_batch", "update", "revoke", "transfer_owner". |
| `set_drive_file_permissions` | extended | Low-level permission setter | Prefer `manage_drive_access` for most sharing tasks. |
| `get_drive_file_permissions` | complete | List all permissions on a file | |
| `check_drive_file_public_access` | complete | Verify whether a file is publicly accessible | |

---

## $ARGUMENTS routing

| Request pattern | Primary tool |
|---|---|
| "find file X in Drive" | `search_drive_files(query="name contains 'X'")` |
| "show me / read file X" | `get_drive_file_content(file_id=...)` |
| "download link for file X" | `get_drive_file_download_url(file_id=...)` |
| "create a file / upload content" | `create_drive_file` |
| "create a folder" | `create_drive_folder` |
| "import this Markdown / DOCX as a Google Doc" | `import_to_google_doc` |
| "share file X with Y" | `manage_drive_access(action="grant", ...)` |
| "get link to file X" | `get_drive_shareable_link(file_id=...)` |
| "list files in folder X" | `list_drive_items(folder_id=...)` |
| "copy file X" | `copy_drive_file(file_id=...)` |

---

## Standard workflows

### Find a file

```
search_drive_files(
  query="name contains 'Q1 Report'",
  user_google_email="user@gmail.com",
  file_type="document",   # optional: document, spreadsheet, presentation, pdf
  page_size=10
)
```

Returns file IDs, names, MIME types, and parent folders.

### Read a file's content

```
get_drive_file_content(
  file_id="<file_id>",
  user_google_email="user@gmail.com"
)
```

For native Google Docs → plain text. For Sheets → CSV. For PDFs → extracted text.
For `.docx`/`.xlsx` → parsed text. For images → base64 with MIME type.

### Create a plain text file

```
create_drive_file(
  file_name="notes.txt",
  content="My notes here...",
  folder_id="root",        # or a specific folder ID
  mime_type="text/plain",
  user_google_email="user@gmail.com"
)
```

### Import Markdown as a Google Doc

```
import_to_google_doc(
  file_name="Project Plan",
  content="# Heading\n\nBody text...",
  source_format="md",
  folder_id="root",
  user_google_email="user@gmail.com"
)
```

Or from a local file: `file_path="/tmp/plan.md"`. Drive auto-converts to
native Doc format, preserving headings, lists, and bold/italic.

### Share a file

```
manage_drive_access(
  file_id="<file_id>",
  action="grant",
  share_with="colleague@example.com",
  role="commenter",       # "reader", "commenter", or "writer"
  share_type="user",
  send_notification=True,
  email_message="Here's the doc for your review.",
  user_google_email="user@gmail.com"
)
```

To share with multiple people at once:

```
manage_drive_access(
  file_id="<file_id>",
  action="grant_batch",
  recipients=[
    {"email": "alice@example.com", "role": "writer", "type": "user"},
    {"email": "bob@example.com",   "role": "reader", "type": "user"},
  ],
  user_google_email="user@gmail.com"
)
```

### Revoke access

```
# 1. Find the permission_id via get_drive_file_permissions
# 2. Revoke it
manage_drive_access(
  file_id="<file_id>",
  action="revoke",
  permission_id="<permission_id>",
  user_google_email="user@gmail.com"
)
```

---

## Drive query syntax (for `search_drive_files`)

| Filter | Example |
|---|---|
| Name contains | `name contains 'budget'` |
| Exact name | `name = 'Q1 Report'` |
| MIME type | `mimeType = 'application/vnd.google-apps.spreadsheet'` |
| In folder | `'folderID' in parents` |
| Starred | `starred = true` |
| Not trashed | `trashed = false` (included automatically) |
| Owner | `'user@example.com' in owners` |
| Modified after | `modifiedTime > '2026-01-01T00:00:00'` |

Pass `file_type` for common shortcuts: `"document"`, `"spreadsheet"`,
`"presentation"`, `"pdf"`, `"folder"`.

---

## Gotchas

**File IDs vs URLs** — tools expect a `file_id` (e.g. `1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms`),
not a full URL. Extract the ID from a Drive URL:
`https://docs.google.com/document/d/<FILE_ID>/edit`.

**`get_drive_file_content` auto-converts** — native Docs/Sheets/Slides are
exported to text/CSV by the API; you won't get the raw JSON representation.
For Sheets data, prefer `read_sheet_values` from the Sheets skill which gives
structured cell data.

**`create_drive_file` vs `import_to_google_doc`** — use `create_drive_file`
for raw files (text, CSV, images). Use `import_to_google_doc` when you want a
native Google Doc with preserved formatting.

**`manage_drive_access` roles** — "viewer" is not a valid API role; use
`"reader"` instead. Valid roles: `"reader"`, `"commenter"`, `"writer"`.
`"owner"` is only valid for `"transfer_owner"` action.

**Tier gating** — `list_drive_items`, `copy_drive_file`, `update_drive_file`,
`manage_drive_access`, and `set_drive_file_permissions` require `--tool-tier
extended`.

---

## Caveats

- Do not cache file IDs or sharing links beyond the immediate task — they remain
  stable but stale links can mislead future conversations.
- `search_drive_files` includes shared drive files by default
  (`include_items_from_all_drives=True`). Pass `drive_id` to scope to one shared drive.
- Transferring ownership is irreversible without the new owner re-sharing.
  Confirm with the user before calling `manage_drive_access(action="transfer_owner")`.
