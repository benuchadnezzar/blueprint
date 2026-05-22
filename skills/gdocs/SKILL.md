---
name: gdocs
description: "Read, create, search, and edit Google Docs via the Google Workspace MCP. Routes /gdocs $ARGUMENTS to the right tool for reading content, creating documents, editing text, applying formatting, and exporting."
compatibility: "Claude Code — requires workspace-mcp installed (see .mcp.json)"
---

# Google Docs (via Google Workspace MCP)

Docs is accessed through the **workspace MCP** server. Tool names appear as
`workspace:<tool_name>` — match by suffix. All tools require `user_google_email`
(the authenticated user's email). If not known, ask once and reuse.

The current MCP config uses `--tool-tier core`. Tools marked **extended** or
**complete** below require upgrading the tier in `.mcp.json`.

---

## Tool selection

| Tool | Tier | Use for | Notes |
|---|---|---|---|
| `get_doc_content` | core | Read a Google Doc as plain text | Also works for `.docx` files stored in Drive. Pass the document ID or full URL. |
| `create_doc` | core | Create a new Google Doc with optional initial text | For rich content, create empty and then use `batch_update_doc`. |
| `modify_doc_text` | core | Insert/delete text and apply inline formatting at a specific index | Requires knowing the character index. Use `inspect_doc_structure` first for complex edits. |
| `search_docs` | extended | Find Docs by name | Uses Drive API `name contains` filter. For content search, use Drive's `search_drive_files`. |
| `get_doc_as_markdown` | extended | Read a Doc with formatting preserved as Markdown | Includes headings, bold/italic, links, lists, tables, and (optionally) inline comments. |
| `find_and_replace_doc` | extended | Replace all occurrences of a string | Simpler than index-based edits for search-and-replace tasks. |
| `list_docs_in_folder` | extended | List all Docs in a specific Drive folder | Returns names and IDs. |
| `insert_doc_elements` | extended | Insert tables, horizontal rules, page breaks, or section breaks | |
| `update_paragraph_style` | extended | Apply heading levels, named styles | |
| `export_doc_to_pdf` | extended | Export a Doc to PDF and save to Drive | Returns the new PDF file ID. |
| `list_document_comments` | extended | Read all comments on a Doc | |
| `manage_document_comment` | extended | Add, reply to, or resolve a comment | |
| `batch_update_doc` | complete | Low-level batch of arbitrary Docs API requests | Full power; use for complex multi-step edits. |
| `inspect_doc_structure` | complete | Get precise character indices for elements | Run before index-based edits with `modify_doc_text`. |
| `insert_doc_image` | complete | Insert an image into a Doc | |
| `update_doc_headers_footers` | complete | Set header/footer content | |
| `create_table_with_data` | complete | Insert a populated table in one call | |
| `manage_doc_tab` | complete | Create or manage tabs in a tabbed Doc | |

---

## $ARGUMENTS routing

| Request pattern | Primary tool |
|---|---|
| "read / show me doc X" | `get_doc_content(document_id=...)` |
| "show me doc X with formatting" | `get_doc_as_markdown(document_id=...)` |
| "create a doc called X" | `create_doc(title="X")` |
| "find docs named X" | `search_docs(query="X")` |
| "replace X with Y in doc" | `find_and_replace_doc` |
| "add a comment to doc X" | `manage_document_comment(action="create")` |
| "show comments on doc X" | `list_document_comments` |
| "export doc X to PDF" | `export_doc_to_pdf` |

---

## Standard workflows

### Read a document

```
get_doc_content(
  document_id="<doc_id or full URL>",
  user_google_email="user@gmail.com"
)
```

Extract the document ID from a URL:
`https://docs.google.com/document/d/<DOC_ID>/edit`

For a formatted read with heading structure, lists, and comments preserved:

```
get_doc_as_markdown(
  document_id="<doc_id>",
  include_comments=True,
  comment_mode="inline",   # comments appear next to their anchor text
  user_google_email="user@gmail.com"
)
```

### Create a document

**Simple doc with plain text content:**

```
create_doc(
  title="Meeting Notes",
  content="# Agenda\n\n1. Item one\n2. Item two",
  user_google_email="user@gmail.com"
)
```

**For rich, formatted content** — create empty then batch-update:

```
# Step 1: Create
create_doc(title="Project Proposal", user_google_email="...")
# → returns document_id

# Step 2: Insert content at end-of-segment (no index math needed)
batch_update_doc(
  document_id="<id>",
  requests=[
    {"insertText": {"location": {"index": 1}, "text": "Introduction\n\n"}},
    ...
  ],
  user_google_email="..."
)
```

### Find and replace text

```
find_and_replace_doc(
  document_id="<id>",
  old_text="Draft",
  new_text="Final",
  match_case=True,
  user_google_email="user@gmail.com"
)
```

### Make targeted text edits

For index-based edits (inserting/deleting/formatting at a position):

```
# 1. Get exact character positions
inspect_doc_structure(document_id="<id>", user_google_email="...")

# 2. Edit at the returned index
modify_doc_text(
  document_id="<id>",
  start_index=42,
  end_index=56,
  text="replacement text",
  bold=True,
  user_google_email="..."
)
```

Use `end_of_segment=True` to append without calculating an index.

### Add a comment

```
manage_document_comment(
  document_id="<id>",
  action="create",
  content="This section needs a citation.",
  anchor_text="unsupported claim",
  user_google_email="..."
)
```

---

## Gotchas

**Document ID vs URL** — `get_doc_content` and `get_doc_as_markdown` accept
either a document ID or the full Google Docs URL. Other tools require a plain ID.
Extract from `https://docs.google.com/document/d/<DOC_ID>/edit`.

**Index-based edits require `inspect_doc_structure` first** — character indices
shift after every insert/delete. Run `inspect_doc_structure` immediately before
any `modify_doc_text` call when you need precision. For append-only operations,
use `end_of_segment=True` to avoid index math.

**`create_doc` initial content is plain text only** — formatting is not applied.
For a rich document from scratch, create empty and then use `batch_update_doc`
to insert formatted content.

**`get_doc_content` vs `get_doc_as_markdown`** — `get_doc_content` returns
plain text (headings appear as plain lines). `get_doc_as_markdown` preserves
structure (headings become `#`, bold becomes `**`). Use Markdown mode when you
need to understand doc structure or when feeding content to another tool.

**`.docx` in Drive** — `get_doc_content` also handles `.docx` files stored in
Drive (it downloads and extracts text). For editing them, you'd need to convert
first with `import_to_google_doc` (Drive skill).

**Tier gating** — `search_docs`, `get_doc_as_markdown`, `find_and_replace_doc`,
`insert_doc_elements`, `update_paragraph_style`, `export_doc_to_pdf`,
`list_document_comments`, and `manage_document_comment` require `--tool-tier
extended`. `batch_update_doc`, `inspect_doc_structure`, and other complex tools
require `--tool-tier complete`.

---

## Caveats

- Do not cache document content beyond the immediate task.
- `batch_update_doc` sends raw Docs API requests — confirm your request structure
  against the Google Docs API batchUpdate documentation before calling.
- Large documents may return truncated content. If `get_doc_content` seems
  incomplete, check the document length and paginate or narrow scope.
