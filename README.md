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

## Restoring your personal configuration

Before this repo was committed to GitHub, org-specific and personally identifying content was replaced with placeholders. This section documents every placeholder and the original value so you can restore your configuration.

### `.mcp.json`

| Placeholder | Your value |
|---|---|
| `YOUR_GOOGLE_OAUTH_CLIENT_ID` | `<your-client-id>.apps.googleusercontent.com` |
| `YOUR_GOOGLE_OAUTH_CLIENT_SECRET` | `<your-client-secret>` |
| `you@example.com` | `<your-email@example.com>` |

### `skills/scrub-a-dub/SKILL.md`

Eight occurrences of `user_google_email="<your-email>"` → replace with your actual email.

### `skills/navigate/skill.md`

This skill had the most changes. The original configuration was for the **Systems Architecture team at Justworks** with a **June 1 fiscal year start**.

#### Frontmatter description

| Placeholder | Your value |
|---|---|
| `[your-team-name]` in the frontmatter `description` field | `Systems Architecture team (Marketing Operations and Technology at Justworks)` |

#### Constants block (near top of skill)

| Placeholder | Your value |
|---|---|
| `STRATEGY_FOLDER_ID = "<your-strategy-drive-folder-id>"` | `"12TUt9I7E1wD9PGYItgGiffLWPGZ8A9Ut"` |
| `TEAM_MEMBERS = ["Team Member A", "Team Member B", ...]` | `["Ben Kulakofsky", "Danny Keane", "Igor Arefev", "Natalie Quiles", "Nikita Tyagi", "Danielle Weiss"]` |
| `FISCAL_YEAR_START_MONTH = 1` | `6` (June) |

#### Quarter date ranges

Change the four quarter definitions back to June-start:

| Generic | Justworks |
|---|---|
| Q1: Jan–Mar (`YYYY-01-01` to `YYYY-03-31`) | Q1: Jun–Aug (`YYYY-06-01` to `YYYY-08-31`) |
| Q2: Apr–Jun (`YYYY-04-01` to `YYYY-06-30`) | Q2: Sep–Nov (`YYYY-09-01` to `YYYY-11-30`) |
| Q3: Jul–Sep (`YYYY-07-01` to `YYYY-09-30`) | Q3: Dec–Feb (`YYYY-12-01` to `YYYY-02-28`) |
| Q4: Oct–Dec (`YYYY-10-01` to `YYYY-12-31`) | Q4: Mar–May (`YYYY-03-01` to `YYYY-05-31`) |

#### FY orientation logic

| Generic | Justworks |
|---|---|
| "If today is within 1 month of the FY end → assume planning upcoming FY" | "If today is **May 1 or later** → assume planning upcoming FY. Note: 'You're 19 days from the end of [FY-1] — I'll plan [FY].'" |
| `$FY_START "[FY_START_DATE]"` | `"2026-06-01"` |
| `$FY_END "[FY_END_DATE]"` | `"2027-05-31"` |

#### Example strings throughout the skill

Search for these placeholders and replace with your values:

| Placeholder | Your value |
|---|---|
| `[FY]` (example FY label) | `FY27` |
| `[FY-1]` (previous FY label) | `FY26` |
| `[Your Team Name]` | `Systems Architecture` |
| `[Team Member A]` | `Igor` |
| `[Team Member B + C]` | `Natalie + Danny` |
| `[Team Lead]` (capacity table) | `Ben K.` |
| `[Team Member]` (capacity table) | `Danny K.` |

#### Section headers in examples

| Generic | Justworks |
|---|---|
| `Q1 (Jan–Mar [YYYY])` | `Q1 (Jun–Aug 2026)` |
| `Q2 (Apr–Jun [YYYY])` | `Q2 (Sep–Nov 2026)` |
| `Q3 (Jul–Sep [YYYY])` | `Q3 (Dec 2026–Feb 2027)` |
| `Q4 (Oct–Dec [YYYY])` | `Q4 (Mar–May 2027)` |
| `Q2 Roadmap — [Your Team Name] (Apr–Jun [YYYY])` | `Q2 Roadmap — Systems Architecture (Sep–Nov 2026)` |
| `### [Q1: Jan–Mar YYYY]` (doc section header example) | `### [Q1: Jun–Aug 2026]` |

#### Horizon confirmation example

| Generic | Justworks |
|---|---|
| `Q2 (Apr–Jun [YYYY]) / Q2–Q3 (Apr–Sep [YYYY])` | `Q2 (Sep–Nov 2026) / Q2–Q3 (Sep 2026–Feb 2027)` |

#### Gotchas — fallback folder ID

| Generic | Justworks |
|---|---|
| `'<STRATEGY_FOLDER_ID>' in parents` | `'12TUt9I7E1wD9PGYItgGiffLWPGZ8A9Ut' in parents` |

#### Gotchas — leap year note

| Generic | Justworks |
|---|---|
| "if your fiscal year's Q3 spans February, Q3 ends February 28 (or 29 in a leap year)..." | Append: "[FY] Q3 ends 2027-02-28 (not a leap year)." |

---

## `.claude/settings.local.json`

This file is gitignored. It contains auto-approved tool permissions and enabled MCP servers. Re-create it after cloning if you want the same permission set.
