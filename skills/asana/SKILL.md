---
name: asana
description: "Task and project management via the Asana MCP. Routes /asana $ARGUMENTS to the right MCP tool for fetching tasks, creating tasks, updating status, searching projects, and more."
compatibility: "Claude Code — requires Asana MCP installed globally"
---

# Asana (via MCP)

The user's Asana workspace is accessed through the **Asana MCP**, already installed
globally. Do not construct raw API calls — use the MCP tools directly.

---

## Tool selection

Pick the narrowest tool that answers the request. The Asana MCP has two modes for
several operations: **immediate** (creates/updates without confirmation) and
**preview** (renders a visual widget and waits for user approval). Default to
immediate unless the user explicitly says "preview", "confirm first", or "show me
before creating".

| Tool | Use for | Notes |
|---|---|---|
| `get_my_tasks` | "my tasks", "what's on my plate", quick inbox check | Fastest path. Use `completed_since="now"` for incomplete only. |
| `search_tasks` | Filtered task search: by text, assignee, project, date, priority | Default tool for any "find tasks" request. Always set `completed=false` unless user asks for completed tasks. |
| `search_tasks_preview` | User explicitly asks to *see* search results rendered | Renders a UI widget — do NOT use for programmatic results you'll process further. |
| `get_task` | Full task details: description, subtasks, comments, custom fields | Use after finding a task ID. `include_comments=true` by default. |
| `create_tasks` | "create a task", "add X to my list" | Default for task creation. Requires `default_project` or `default_assignee`. |
| `create_task_preview_v3` | User says "show me before creating" or "draft a task" | Only for single tasks. Preview, then user confirms. |
| `update_tasks` | Complete, reassign, reschedule, rename, add notes | Accepts 1–50 tasks. Use `completed=true` to mark done. |
| `add_comment` | Add a comment or note to a task | Use `html_text` for rich formatting, `text` for plain. |
| `delete_task` | Delete a task | Irreversible. Confirm with user before calling. |
| `get_project` | Project details, member list, task counts, sections | Pass `include_sections=true` when you need section GIDs for task placement. |
| `get_projects` | List all projects in the workspace | Returns name, ID, task counts. Use `team` param to scope. |
| `create_project` | Create a full project with sections and tasks | Default for project creation. |
| `create_project_preview_v2` | User says "show me the project plan first" | Preview before creating. |
| `create_project_status_update` | Post a health update to a project | `color`: green (on track), yellow (at risk), red (off track), blue (on hold). |
| `get_status_overview` | "what's the status of X?", "how is project Y going?" | Searches projects by keyword, aggregates tasks + status updates. Use this first for any project health question. |
| `search_objects` | Find projects, portfolios, teams, users, tags by name | Use before `get_projects` when you know a name but not an ID. |
| `get_me` | Current user's GID and workspace | Run when you need the user's ID for filters. Tools accept `"me"` as a shorthand — prefer that over calling this. |
| `get_users` | List workspace users | Use when the user references a teammate by name. |
| `get_teams` | List teams | Use to find a team GID for project scoping. |

---

## $ARGUMENTS routing

Parse the user's request and route:

| Request pattern | Primary tool |
|---|---|
| "my tasks", "what do I have", "open tasks" | `get_my_tasks(completed_since="now")` |
| "my tasks due this week / overdue" | `search_tasks(assignee_any="me", completed=false, due_on_before=<date>)` |
| "find tasks about X", "search for Y" | `search_tasks(text="X", completed=false)` |
| "create task X [with details]" | `create_tasks` |
| "complete / close task X" | `update_tasks(completed=true)` |
| "status of project X" | `get_status_overview(keywords="X")` |
| "post a status update on X" | `create_project_status_update` |
| "create project" | `create_project` |
| "find project X" | `search_objects(resource_type="project", query="X")` then `get_project` |
| "add comment to task X" | `add_comment` |

When the user references "my" anything (tasks, projects, etc.), always scope to the
current user — pass `assignee_any="me"` or `"me"` as the assignee.

---

## Standard workflows

### Fetch my open tasks
```
get_my_tasks(completed_since="now", limit=50)
```
Group and present by due date. If the user asks for more detail on a specific task,
call `get_task(task_id=<gid>)`.

### Create a task
```
create_tasks(
  tasks=[{name: "...", notes: "...", due_on: "YYYY-MM-DD", assignee: "me"}],
  default_assignee="me"   # required when no project_id
)
```
If no project is mentioned, use `default_assignee="me"` to place the task in My Tasks.
If a project is mentioned, look it up with `search_objects` first to get the GID,
then pass `project_id`.

### Find and complete a task
1. `search_tasks(text="task name", assignee_any="me", completed=false)` → get GID
2. `update_tasks(tasks=[{task: <gid>, completed: true}])`

### Post a project status update
1. `search_objects(resource_type="project", query="project name")` → get project GID
2. `create_project_status_update(parent=<gid>, title="...", text="...", color="green|yellow|red")`

Color guide: green = on track, yellow = at risk, red = off track, blue = on hold.

### Summarize project health
```
get_status_overview(keywords="project name")
```
This is a single-call aggregation — don't manually chain `get_project` + `get_tasks`
for health summaries. Only go deeper if the user asks for task-level detail.

### Find a teammate's tasks
1. `get_users()` → find GID by name (or use email directly)
2. `search_tasks(assignee_any=<gid or email>, completed=false)`

---

## Gotchas

**`search_tasks_preview` vs `search_tasks`** — `search_tasks_preview` renders an
interactive widget the user sees in the UI. It is NOT for getting data to work with.
For anything programmatic (counting tasks, extracting IDs, further processing),
always use `search_tasks`.

**`create_tasks` requires a context** — either `default_project` (project GID) or
`default_assignee` ("me" or user GID). Without one, the API will reject the call.
When the user doesn't specify a project, default to `default_assignee="me"`.

**Section placement** — to create a task in a specific section, call
`get_project(project_id=<gid>, include_sections=true)` first to get section GIDs,
then pass `section_id` in the task.

**Deleting tasks is irreversible** — `delete_task` also deletes subtasks not in
another project. Always confirm with the user before calling it.

**`due_on` vs `due_at`** — `due_on` is a date string (YYYY-MM-DD), `due_at` is an
ISO 8601 datetime. Use `due_on` for day-level deadlines (most common).
`start_on` requires `due_on` to also be set.

**Empty search results** — if `search_tasks` or `get_my_tasks` returns nothing
unexpected, check whether the user has multiple workspaces. The MCP connects to one
workspace at a time.

---

## Caveats

- Do not cache or persist task content, assignee names, or project details beyond
  the immediate response.
- For bulk updates (50+ tasks), `update_tasks` accepts up to 50 per call — batch
  and loop if needed.
- `get_status_overview` may be slow on large workspaces; it performs multiple
  internal searches. For quick lookups, prefer `search_objects` + `get_project`.
