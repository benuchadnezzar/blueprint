---
name: gsheets
description: "Read, write, and format Google Sheets via the Google Workspace MCP. Routes /gsheets $ARGUMENTS to the right tool for reading cell data, writing values, creating spreadsheets, and applying formatting."
compatibility: "Claude Code — requires workspace-mcp installed (see .mcp.json)"
---

# Google Sheets (via Google Workspace MCP)

Sheets is accessed through the **workspace MCP** server. Tool names appear as
`workspace:<tool_name>` — match by suffix. All tools require `user_google_email`
(the authenticated user's email). If not known, ask once and reuse.

The current MCP config uses `--tool-tier core`. Tools marked **extended** or
**complete** below require upgrading the tier in `.mcp.json`.

---

## Tool selection

| Tool | Tier | Use for | Notes |
|---|---|---|---|
| `create_spreadsheet` | core | Create a new spreadsheet with optional sheet names | Returns spreadsheet ID and URL. |
| `read_sheet_values` | core | Read a range of cells | Defaults to `A1:Z1000`. Returns a 2D array of values. |
| `modify_sheet_values` | core | Write, update, or clear a range | Primary write tool. Accepts a 2D array or JSON string. |
| `list_spreadsheets` | extended | Find spreadsheets in Drive by recency | Returns names and IDs. Faster than `search_drive_files` for Sheets specifically. |
| `get_spreadsheet_info` | extended | Get sheet names, IDs, dimensions, and metadata | Run first when you need a sheet ID or need to know what tabs exist. |
| `format_sheet_range` | extended | Apply colors, fonts, number formats, text wrap, alignment | Accepts hex colors (`#RRGGBB`). |
| `list_sheet_tables` | extended | List named tables in a spreadsheet | |
| `create_sheet` | complete | Add a new tab/sheet to an existing spreadsheet | Returns the new sheet ID. |
| `append_table_rows` | complete | Append rows to a named table | |
| `resize_sheet_dimensions` | complete | Add/remove rows or columns | |
| `move_sheet_rows` | complete | Reorder rows within a sheet | |
| `list_spreadsheet_comments` | complete | Read comments on a spreadsheet | |
| `manage_spreadsheet_comment` | complete | Add, reply to, or resolve comments | |
| `manage_conditional_formatting` | complete | Add or remove conditional formatting rules | |

---

## $ARGUMENTS routing

| Request pattern | Primary tool |
|---|---|
| "read data from spreadsheet X" | `read_sheet_values(spreadsheet_id=...)` |
| "read range A1:D10 in sheet X" | `read_sheet_values(spreadsheet_id=..., range_name="Sheet1!A1:D10")` |
| "write / update values in sheet X" | `modify_sheet_values(spreadsheet_id=..., range_name=..., values=...)` |
| "clear range X" | `modify_sheet_values(clear_values=True)` |
| "create a spreadsheet" | `create_spreadsheet(title=...)` |
| "what sheets are in spreadsheet X?" | `get_spreadsheet_info(spreadsheet_id=...)` |
| "find my spreadsheets" | `list_spreadsheets` |
| "format range X (bold, color, etc.)" | `format_sheet_range` |
| "add a new sheet/tab" | `create_sheet` |

---

## Standard workflows

### Read data from a sheet

```
# Read the default range (A1:Z1000) from primary sheet
read_sheet_values(
  spreadsheet_id="<id>",
  user_google_email="user@gmail.com"
)

# Read a specific named range or tab
read_sheet_values(
  spreadsheet_id="<id>",
  range_name="Sheet2!B2:F50",
  include_formulas=True,    # see raw formulas
  include_notes=True,       # see cell notes
  user_google_email="user@gmail.com"
)
```

Returns a 2D array where the first row is typically the header.

### Write values

```
modify_sheet_values(
  spreadsheet_id="<id>",
  range_name="Sheet1!A1",
  values=[
    ["Name", "Score", "Grade"],
    ["Alice", 95, "A"],
    ["Bob",   82, "B"],
  ],
  value_input_option="USER_ENTERED",  # interprets formulas and dates
  user_google_email="user@gmail.com"
)
```

`value_input_option`:
- `"USER_ENTERED"` (default) — Sheets interprets the value as if typed by a user
  (parses dates, evaluates `=SUM(...)`, etc.)
- `"RAW"` — stores the value as-is, no interpretation

### Clear a range

```
modify_sheet_values(
  spreadsheet_id="<id>",
  range_name="Sheet1!A2:Z100",
  clear_values=True,
  user_google_email="user@gmail.com"
)
```

### Create a spreadsheet

```
create_spreadsheet(
  title="2026 Budget",
  sheet_names=["Jan", "Feb", "Mar", "Q1 Summary"],
  user_google_email="user@gmail.com"
)
```

Returns the spreadsheet ID and URL. Write data immediately after with
`modify_sheet_values`.

### Get sheet structure before writing

When the spreadsheet has multiple tabs or you need sheet IDs for formatting:

```
get_spreadsheet_info(
  spreadsheet_id="<id>",
  user_google_email="user@gmail.com"
)
```

Returns tab names, sheet IDs, row/column counts, and locale.

### Apply formatting

```
format_sheet_range(
  spreadsheet_id="<id>",
  range_name="Sheet1!A1:F1",       # header row
  bold=True,
  background_color="#4A90D9",
  text_color="#FFFFFF",
  horizontal_alignment="CENTER",
  user_google_email="user@gmail.com"
)
```

Color accepts `#RRGGBB`. `number_format_type` can be `"DATE"`, `"CURRENCY"`,
`"PERCENT"`, `"NUMBER"`, `"TEXT"`, `"TIME"`.

---

## Range notation

Ranges follow standard A1 notation:

| Notation | Meaning |
|---|---|
| `A1:D10` | Columns A–D, rows 1–10 (active sheet) |
| `Sheet1!A1:D10` | Explicit sheet name |
| `'My Sheet'!A1:D10` | Sheet name with spaces (single-quoted) |
| `A:D` | Entire columns A–D |
| `1:3` | Entire rows 1–3 |
| `A1` | Single cell |

Always include the sheet name (`Sheet1!...`) when the spreadsheet has multiple
tabs — otherwise Sheets defaults to the first tab.

---

## Gotchas

**Spreadsheet ID vs URL** — tools take a `spreadsheet_id`, not the full URL.
Extract from `https://docs.google.com/spreadsheets/d/<SPREADSHEET_ID>/edit`.

**`modify_sheet_values` with `values`** — pass a 2D Python list or a JSON
string representing one. A single row is `[["A", "B", "C"]]` (outer list is
rows, inner lists are columns). Do not pass a 1D list.

**A1:Z1000 default reads trailing empty rows** — the default range includes
many empty cells. If performance matters, call `get_spreadsheet_info` first
to know the actual data extent, then narrow the range.

**`value_input_option="USER_ENTERED"` for formulas and dates** — if you write
`"=SUM(A1:A10)"` as a formula, use `"USER_ENTERED"`. With `"RAW"`, it's stored
as a literal string.

**Sheet name vs sheet ID** — `format_sheet_range`, `create_sheet`, and other
formatting/structural tools use range strings (`"Sheet1!A1:D5"`) not numeric
sheet IDs. `get_spreadsheet_info` returns both names and IDs.

**Tier gating** — `list_spreadsheets`, `get_spreadsheet_info`, `format_sheet_range`,
and `list_sheet_tables` require `--tool-tier extended`. `create_sheet`,
`append_table_rows`, `resize_sheet_dimensions`, `move_sheet_rows`, comments,
and `manage_conditional_formatting` require `--tool-tier complete`.

---

## Caveats

- Do not cache spreadsheet data beyond the immediate task — data changes
  frequently.
- For large spreadsheets, avoid reading `A1:Z1000` and then filtering in
  context — narrow the range to only the data you need.
- `modify_sheet_values` overwrites the specified range. It does not insert rows.
  To add rows below existing data without overwriting, read the extent first,
  then write starting at the next empty row.
