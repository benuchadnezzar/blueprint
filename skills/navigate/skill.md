---
name: navigate
description: "Strategic roadmap planning skill. Reads team strategy docs from a shared Drive folder, analyzes six months of Asana history for the full team, reviews the user's Slack and Granola meetings from the past two weeks, and synthesizes a prioritized, quarter-aware roadmap for the specified time horizon (fiscal year, one quarter, or two quarters). Produces a Google Doc and a Google Sheet version of the roadmap after interactive discussion and confirmation. Configure STRATEGY_FOLDER_ID and TEAM_MEMBERS in the Constants section before use. Invoke with /navigate followed by the time horizon, e.g. /navigate fiscal year, /navigate Q2, /navigate Q2 and Q3."
compatibility: "Claude Code — requires workspace-mcp, Asana MCP, Granola MCP, Slack MCP"
---

# Navigate (Strategic Roadmap Planning)

## Constants

```
STRATEGY_FOLDER_ID = "<your-strategy-drive-folder-id>"

TEAM_MEMBERS = [
  "<Team Lead Name>",   # user — team lead
  "<Team Member 2>",
  "<Team Member 3>",
  # add more as needed
]

FISCAL_YEAR_START_MONTH = 1   # January 1 — adjust to your org's fiscal year start
# FY quarters (standard calendar year example):
#   Q1: Jan 1 – Mar 31
#   Q2: Apr 1 – Jun 30
#   Q3: Jul 1 – Sep 30
#   Q4: Oct 1 – Dec 31
```

---

## Phase 0 — Parse horizon and orient

### 0A — Determine the planning window

Parse `$ARGUMENTS` to identify the time horizon. Classify as one of:

| Input | `$HORIZON` | Notes |
|---|---|---|
| "fiscal year" / "full year" / "FY" | `fy` | Defaults to the upcoming FY unless we're ≥ 3 months into the current one |
| "Q1" / "first quarter" | `q_single` + `$QUARTERS=[1]` | |
| "Q2" / "second quarter" | `q_single` + `$QUARTERS=[2]` | |
| "Q3" / "third quarter" | `q_single` + `$QUARTERS=[3]` | |
| "Q4" / "fourth quarter" | `q_single` + `$QUARTERS=[4]` | |
| "Q1 and Q2" / "first two quarters" / "two quarters" | `q_multi` + `$QUARTERS=[1,2]` | |
| "Q2 and Q3" / "next two quarters" etc. | `q_multi` + `$QUARTERS=[2,3]` | |

**FY orientation** — determine the target fiscal year from today's date:
- If today is within 1 month of the FY end → assume the user is planning the
  **upcoming** FY. Note: "You're N days from the end of [FY-1] — I'll plan [FY]."
- Otherwise → use the **current** FY.

Store as `$FY_LABEL` (e.g. "[FY]"), `$FY_START` ("[FY_START_DATE]"), `$FY_END` ("[FY_END_DATE]").

Derive quarter date ranges from constants and store as `$QUARTER_RANGES`:
```
Q1: { start: "YYYY-01-01", end: "YYYY-03-31" }   # derived from FISCAL_YEAR_START_MONTH
Q2: { start: "YYYY-04-01", end: "YYYY-06-30" }
Q3: { start: "YYYY-07-01", end: "YYYY-09-30" }
Q4: { start: "YYYY-10-01", end: "YYYY-12-31" }
```

Compute `$WINDOW_START` and `$WINDOW_END` from the union of the selected quarters.

### 0B — State the horizon to the user

Before gathering data, confirm the interpretation:

> "Planning **[[FY] / Q2 (Apr–Jun [YYYY]) / Q2–Q3 (Apr–Sep [YYYY])]**. I'll pull
> context from Drive, Asana (past 6 months for the full team), and your recent Slack
> and Granola — this will take a moment."

Do not wait for a reply before starting Phase 1 data gathering.

---

## Phase 1 — Gather context (all sources in parallel)

Fire all of the following simultaneously. If any single source errors or returns
empty, note it and continue — do not abort.

### 1A — Drive: strategy folder

**List all files in the strategy folder:**

```
list_drive_items(
  folder_id="<STRATEGY_FOLDER_ID>",
  user_google_email="<user_email>"
)
```

**Read all files found** (in parallel, up to 20). For each file returned:

```
get_drive_file_content(
  file_id="<file_id>",
  user_google_email="<user_email>"
)
```

If any file is itself a folder, recursively list and read its contents (max 2
levels deep). Prefer native Google Docs over PDFs of the same content when both
exist.

Extract and note:
- Team name, charter, and mission statement
- Each team member's name, role/title, and areas of ownership
- Martech/data tool stack (any mention of tools the team uses or maintains)
- Company-level goals and strategy
- Team-level OKRs, priorities, and strategy
- Any explicit "not doing" lists or de-prioritized areas
- Key stakeholders and partner teams

### 1B — Asana: six months of team history

**Step 1** — Resolve team member GIDs:

```
get_users(user_google_email="<user_email>")
```

Match returned users against `TEAM_MEMBERS` by name (fuzzy match okay). Store
as `$TEAM_GIDS` = comma-separated list of GIDs. If a name doesn't match, note it
and proceed with the ones that do.

**Step 2** — Fetch all tasks assigned to any team member in the last 6 months:

```
search_tasks(
  assignee_any="<$TEAM_GIDS>",
  completed=false,
  modified_on_after="<6_MONTHS_AGO>"
)
```

```
search_tasks(
  assignee_any="<$TEAM_GIDS>",
  completed=true,
  completed_on_after="<6_MONTHS_AGO>"
)
```

Run both in parallel. Six months ago = today minus 183 days (ISO date).

For each task returned, note: name, assignee, project, due date, completion date
(if complete), and any tags.

**Step 3** — Identify active projects (at least 3 tasks):

```
get_projects(
  user_google_email="<user_email>"  # not needed for Asana — Asana is scoped already
)
```

Actually use `search_objects(resource_type="project", query="")` to find all
workspace projects, then cross-reference with the task results to identify which
projects the team is actively contributing to. For each project with ≥ 3 team
tasks, call `get_project(project_id=<gid>, include_sections=true)` to get the
full picture.

Summarize: what has the team shipped, what's in flight, what categories of work
they've been doing, and rough time allocation by person.

### 1C — Slack: user's last two weeks

Two weeks ago = today minus 14 days (ISO date).

```
slack_search_public_and_private(
  query="from:me after:<TWO_WEEKS_AGO_DATE>"
)
```

```
slack_search_public_and_private(
  query="to:me after:<TWO_WEEKS_AGO_DATE>"
)
```

```
slack_search_public_and_private(
  query="@<user_slack_name> after:<TWO_WEEKS_AGO_DATE>"
)
```

Run all three in parallel. If the user's Slack username is unknown, call
`slack_search_users(query="<user_name>")` first.

Extract: any strategic discussions, asks for the team, stakeholder requests,
mentions of upcoming work or priorities, blockers, and cross-team dependencies.

### 1D — Granola: user's last two weeks

```
list_meetings(time_range="last_30_days")
```

Filter to meetings within the last 14 days. Then:

```
get_meetings(meeting_ids=[<ids from the last 14 days>])
```

Extract: decisions made, action items, strategic context shared by leadership,
asks directed at the team, recurring themes across meetings.

---

## Phase 2 — Synthesize intelligence (internal — do not output yet)

Build a working model in memory before presenting anything. Organize by:

### 2A — Team profile

For each team member, synthesize:
- **Role**: from Drive docs
- **Areas of ownership**: what projects/tools/processes they own (from Drive + Asana)
- **Recent work**: what they've been shipping (from Asana)
- **Approximate capacity signal**: how loaded they look (volume of recent tasks)
- **Strengths/specialties**: inferred from their project history and role description

### 2B — Strategic priorities

Organize what you've learned into a hierarchy:
- **Company-level**: goals, themes, key metrics
- **Team-level**: OKRs, stated priorities, charter commitments
- **Implicit priorities**: what's been getting attention (Slack, meetings, Asana)
- **Gaps**: things implied by strategy but not yet in flight

### 2C — Tool and capability inventory

List the martech and data tools the team uses, maintains, or plans to work with.
This will inform which projects are realistic to scope.

### 2D — Draft project candidates

Generate a list of candidate projects — more than you'll propose, so you can
prune. For each candidate:

```
{
  name: string,
  description: string (2–3 sentences),
  strategic_rationale: string (which goal/priority does this serve?),
  estimated_effort: "small" | "medium" | "large",  // S=1 person <1 quarter, M=1-2 people 1 quarter, L=2+ people 1+ quarters
  suggested_owner: string (primary team member),
  suggested_supporters: [string] (others involved),
  quarter_placement: [Q1, Q2, Q3, Q4] (which FY quarters),
  dependencies: [string] (other projects or external teams it depends on),
  source_signals: [string] (which Drive doc / Asana project / Slack thread / meeting informed this)
}
```

Aim for 8–16 candidates total. Prune for:
- Feasibility given team size and capacity
- Strategic fit (every project must ladder up to a stated goal)
- Balance across team members (no one person overloaded)

---

## Phase 3 — Draft roadmap and discuss (interactive)

Present the proposed roadmap to the user. **Do not produce the final Doc/Sheet yet.**

### 3A — Present the roadmap

Structure the output based on the horizon:

**For `fy` (full year):**

Present a quarter-by-quarter narrative, then a summary table:

```
## [FY] Roadmap — [Your Team Name]

### Strategic Themes
- [Theme 1]: [brief rationale]
- [Theme 2]: [brief rationale]
- [Theme 3]: [brief rationale]

### Q1 (Jan–Mar [YYYY])
**Focus:** [one sentence on the quarter's theme]

| Project | Owner | Size | Description |
|---|---|---|---|
| Project A | [Team Member A] | M | ... |
| Project B | [Team Member B + C] | L (starts Q1) | ... |

### Q2 (Apr–Jun [YYYY])
...

### Q3 (Jul–Sep [YYYY])
...

### Q4 (Oct–Dec [YYYY])
...

### Projects spanning multiple quarters
- **Project B** ([Team Member B + C]): Q1–Q2 — [one-sentence description of Q1 vs Q2 deliverable]
```

**For `q_single` or `q_multi`:**

Present a flat project list for the window, with per-month or per-sprint
breakdown if useful, but don't force it:

```
## Q2 Roadmap — [Your Team Name] (Apr–Jun [YYYY])

**Focus for the quarter:** [one sentence]

| Project | Owner | Month | Description |
|---|---|---|---|
| ... | ... | Sep | ... |
```

### 3B — Capacity check

After presenting projects, show a rough capacity check per person:

```
| Team Member | Q1 | Q2 | Q3 | Q4 |
|---|---|---|---|---|
| [Team Lead] | Project A (M), Project C (S) | ... | | |
| [Team Member] | Project B (L) | Project B (L, cont.) | | |
| ...
```

"S = ~1–4 weeks, M = ~1 quarter, L = multi-quarter. If anyone looks overloaded,
flag it here."

### 3C — Questions and gaps to resolve

Before the user confirms, surface any open questions:

> **Before finalizing, a few things worth discussing:**
> 1. [Question about a strategic call or tradeoff]
> 2. [Dependency or risk you're not sure how to handle]
> 3. [Something under-specified in the source material]

Ask: "Does this direction look right? Add, cut, or reshape anything before I
build the final docs."

**Wait for the user's response.** Iterate on Phase 3 until the user explicitly
says "finalize", "looks good", "ship it", or equivalent.

---

## Phase 4 — Produce outputs (after explicit user confirmation)

Do not create any files until the user has confirmed the roadmap in Phase 3.

### 4A — Determine output location

Ask the user where to save the files, or default to Drive root. Suggest placing
both files in the strategy folder (`STRATEGY_FOLDER_ID`) or a subfolder of it.
If the user has a preference from a prior conversation, use that.

### 4B — Create the Google Doc

Create a well-formatted Google Doc. Use `import_to_google_doc` with rich Markdown.

**Doc structure:**

```markdown
# [[FY] / Q2 / Q2–Q3] Roadmap — [Your Team Name]
*[Date generated] · [Time horizon label]*

---

## Table of Contents
(Manually listed — the Doc will auto-generate when opened in Google Docs)

---

## Executive Summary
[3–5 sentences. What is the team focused on, why, and what does success look like
for this time horizon.]

---

## Strategic Context

### Company Goals
[Bullet points from the Drive docs]

### Team Mission and Charter
[2–3 sentences from Drive docs]

### OKRs / Team Priorities
[Bullet points]

---

## Team

| Name | Role | Focus Areas |
|---|---|---|
| Ben K. | [title] | [areas] |
| ... | | |

---

## Roadmap

### [Q1: Jan–Mar YYYY]  *(omit this header for single-quarter plans)*

#### [Project Name]
**Owner:** [Name] | **Size:** [S/M/L] | **Quarter(s):** [Q1] | **Status:** Planned

[2–4 sentence description. What will be built, what problem it solves, and how it
ties to a strategic goal.]

**Key deliverables:**
- [deliverable 1]
- [deliverable 2]

**Dependencies:** [list or "None"]

---
*(repeat for each project)*

---

## Capacity Overview

[Capacity table from Phase 3B]

---

## Open Questions and Risks
[Numbered list of anything unresolved]

---

*Generated by /navigate · [Your Team Name] · [date]*
```

```
import_to_google_doc(
  file_name="[[FY]] [Your Team Name] Roadmap — [Month Year]",
  content="<markdown content>",
  source_format="md",
  folder_id="<STRATEGY_FOLDER_ID>",
  user_google_email="<user_email>"
)
```

### 4C — Create the Google Sheet

Create a spreadsheet with a clean, visual layout. Structure depends on horizon:

**For `fy`:**

Sheet tabs: `Overview`, `Q1`, `Q2`, `Q3`, `Q4`

**Overview tab columns:**
`Project Name | Owner | Supporters | Q1 | Q2 | Q3 | Q4 | Size | Strategic Goal | Status | Notes`

For each quarter column, use:
- `●` (filled circle) = primary work in this quarter
- `○` (open circle) = supporting / wrapping-up work
- (blank) = not in this quarter

Use color-coded rows by strategic theme. Apply header formatting (bold, dark
background with white text).

**Per-quarter tabs** (`Q1`, `Q2`, `Q3`, `Q4`):

Columns: `Project | Owner | Month (if known) | Key Deliverables | Dependencies | Notes`

**For `q_single` or `q_multi`:**

Single tab per quarter with the same per-quarter tab structure above.

**Formatting rules:**
- Header row: bold, background `#1a73e8` (Google blue), white text
- Alternate row colors: white / `#f8f9fa` (light gray)
- Strategic theme grouping rows: `#e8f0fe` (light blue) — merge cells and bold the theme name
- "Large" effort rows: left border accent in `#fbbc04` (yellow)
- Completed/shipped projects (if any): `#e6f4ea` (light green) row background

```python
# Step 1: Create spreadsheet
create_spreadsheet(
  title="[[FY]] [Your Team Name] Roadmap",
  sheet_names=["Overview", "Q1", "Q2", "Q3", "Q4"],   # adjust for non-FY horizons
  user_google_email="<user_email>"
)
# → returns spreadsheet_id

# Step 2: Write data to Overview tab
modify_sheet_values(
  spreadsheet_id="<id>",
  range_name="Overview!A1",
  values=[
    ["Project Name", "Owner", "Supporters", "Q1", "Q2", "Q3", "Q4", "Size", "Strategic Goal", "Status", "Notes"],
    ["Project A", "Igor", "", "●", "●", "", "", "L", "Goal X", "Planned", ""],
    ...
  ],
  value_input_option="USER_ENTERED",
  user_google_email="<user_email>"
)

# Step 3: Format header row
format_sheet_range(
  spreadsheet_id="<id>",
  range_name="Overview!A1:K1",
  bold=True,
  background_color="#1a73e8",
  text_color="#FFFFFF",
  horizontal_alignment="CENTER",
  user_google_email="<user_email>"
)

# Step 4: Write per-quarter tabs, format similarly
# (repeat for each quarter)
```

Move the file to the strategy folder after creation (if possible), or set the
folder at creation time using Drive tools.

### 4D — Confirm and share links

After both files are created:

> "Done! Here are your roadmap files:
> - **Google Doc**: [link]
> - **Google Sheet**: [link]
>
> Both are saved in the strategy Drive folder. Ready to share with the team whenever you are."

---

## State tracking

| Variable | Type | Set in |
|---|---|---|
| `$HORIZON` | `fy` \| `q_single` \| `q_multi` | Phase 0 |
| `$QUARTERS` | array of ints | Phase 0 |
| `$FY_LABEL` | string (e.g. "[FY]") | Phase 0 |
| `$FY_START`, `$FY_END` | YYYY-MM-DD | Phase 0 |
| `$QUARTER_RANGES` | dict | Phase 0 |
| `$WINDOW_START`, `$WINDOW_END` | YYYY-MM-DD | Phase 0 |
| `$TEAM_GIDS` | comma-separated string | Phase 1B |
| `$PROJECTS` | array of project objects | Phase 2D, updated in Phase 3 |
| `user_google_email` | string | Ask once if unknown |

---

## Guardrails

- **Never create the Doc or Sheet until the user confirms the roadmap in Phase 3.**
  Showing the draft is not confirmation — wait for an explicit "finalize" or equivalent.
- **Every project must trace to a stated strategic goal.** If you can't articulate
  the connection, don't include the project — ask the user instead.
- **Balance team capacity.** No single person should be assigned "L" efforts across
  more than one quarter at a time, unless the user specifically directs otherwise.
- **Respect the "not doing" signals.** If Drive docs or recent Slack/Asana indicate
  something is explicitly deprioritized, don't include it in the roadmap without
  flagging it as a deliberate revisit.
- **Phase 1 runs in full before Phase 2 synthesis begins.** Don't draft projects
  from partial data.

---

## Gotchas

**Drive `list_drive_items` requires `--tool-tier extended`** — if the tool is
unavailable, fall back to `search_drive_files(query="'<STRATEGY_FOLDER_ID>' in parents", ...)`.

**Asana user lookup** — `get_users` returns workspace-level users; match by
display name. If a team member's name is ambiguous (e.g. two "Danny"s), flag it
and use the one with the most recent task activity in plausible projects.

**`assignee_any` limit** — the Asana `search_tasks` tool may not accept more
than ~10 GIDs in `assignee_any`. If the call fails, split into two separate
queries (e.g., first 3 people, last 3 people) and merge results.

**FY quarter leap year** — if your fiscal year's Q3 spans February, Q3 ends
February 28 (or 29 in a leap year). Check: a year is a leap year if divisible
by 4 and (not divisible by 100 or divisible by 400).

**Google Sheet in Drive folder** — `create_spreadsheet` doesn't accept a
`folder_id`. After creating it, use Drive's `manage_drive_access` or
`update_drive_file` to move it, or accept that it lands in Drive root and share
the link.

**`format_sheet_range` requires `--tool-tier extended`** — if unavailable,
create the sheet with data only and note that the user can apply formatting
manually. Still produce all the data content.

**Granola `list_meetings` max range** — `list_meetings` accepts predefined
ranges. Use `time_range="last_30_days"` and filter to the last 14 days in
post-processing.

**Large Drive folders** — if the strategy folder has many files, `list_drive_items`
may paginate. Check for a `next_page_token` and fetch subsequent pages.
Read only files clearly related to strategy, team charter, tooling, or OKRs —
skip assets, screenshots, or archived files with dates > 1 year old.

---

## Output quality bar

The final deliverables should be things the user can print, share in a meeting,
and use to make decisions immediately. Aim for:

- **Doc**: readable top-to-bottom in 10 minutes; executive summary is genuinely
  standalone; project descriptions are crisp and jargon-free
- **Sheet**: glanceable in a single scroll; someone should be able to understand
  the whole year's shape from the Overview tab in under 2 minutes; per-quarter
  tabs give enough detail to assign work on day one of the quarter
