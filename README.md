# blueprint

A Claude Code plugin with skills for Google Workspace, Asana, Slack, Granola, Confluence, and Lucid diagramming. Designed for use as a personal productivity layer on top of Claude Code.

## What's included

| Skill | Invoke | Description |
|---|---|---|
| asana | `/asana` | Asana task and project management |
| confluence | `/confluence` | Confluence page search and editing |
| diagram | `/diagram` | Lucid diagramming with script support |
| focus | `/focus` | Focus time and calendar blocking |
| gcalendar | `/gcalendar` | Google Calendar management |
| gdocs | `/gdocs` | Google Docs creation and editing |
| gdrive | `/gdrive` | Google Drive search and navigation |
| gmail | `/gmail` | Gmail search and triage |
| granola | `/granola` | Meeting notes via Granola |
| gsheets | `/gsheets` | Google Sheets read/write |
| navigate | `/navigate` | Quarterly and annual planning — roadmaps, capacity tables, strategy docs |
| scrub-a-dub | `/scrub-a-dub` | Workspace hygiene: unsubscribe from newsletters, archive unread email, triage overdue Asana tasks |
| wrap | `/wrap` | Week/quarter wrap-up summaries |

## Setup

**1. Copy and fill in `.mcp.json`:**

```sh
cp .mcp.json.example .mcp.json
```

Then edit `.mcp.json` and replace the three placeholder values:

| Placeholder | What to put there |
|---|---|
| `YOUR_GOOGLE_OAUTH_CLIENT_ID` | Your Google OAuth 2.0 client ID |
| `YOUR_GOOGLE_OAUTH_CLIENT_SECRET` | Your Google OAuth 2.0 client secret |
| `you@example.com` | Your Google Workspace email address |

To get OAuth credentials: [Google Cloud Console](https://console.cloud.google.com/) → APIs & Services → Credentials → Create OAuth 2.0 Client ID (Desktop app).

**2. Configure personal values in skills** — see the section below.

**3. Restart Claude Code** to pick up the new MCP config.

---

## Skill configuration

### `skills/scrub-a-dub/SKILL.md`

Search for `user_google_email="<your-email>"` (eight occurrences) and replace `<your-email>` with your Google Workspace email.

### `skills/navigate/skill.md`

This skill needs to know your team and fiscal calendar. Fill in the following:

**Frontmatter description** — replace `[your-team-name]` with your team's name.

**Constants block** (near the top of the file):

| Placeholder | What to put there |
|---|---|
| `STRATEGY_FOLDER_ID = "<your-strategy-drive-folder-id>"` | Google Drive folder ID for your team's strategy docs |
| `TEAM_MEMBERS = ["Team Member A", "Team Member B", ...]` | List of your team members' names |
| `FISCAL_YEAR_START_MONTH = 1` | Month number your fiscal year starts (e.g. `6` for June) |

**Quarter date ranges** — the defaults assume a January fiscal year start (Q1: Jan–Mar, Q2: Apr–Jun, etc.). If your fiscal year starts in a different month, update all four quarter definitions to match.

**Example strings** — search for `[FY]`, `[FY-1]`, `[Your Team Name]`, `[Team Lead]`, `[Team Member A]`, and `[Team Member B + C]` and replace each with your values. These appear in example outputs shown to the model.

---

## `.claude/settings.local.json`

This file is gitignored. It contains auto-approved tool permissions and enabled MCP servers. Re-create it after cloning if you want the same permission set.
