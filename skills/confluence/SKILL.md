---
name: confluence
description: "Read, search, create, and update Confluence pages and spaces via the Atlassian MCP. Routes /confluence $ARGUMENTS to the right tool for finding content, drafting pages, updating docs, and adding comments."
compatibility: "Claude Code — requires Atlassian MCP connector (configured at claude.ai account level)"
---

# Confluence (via Atlassian MCP)

Confluence is accessed through the **Atlassian MCP**, connected at the claude.ai
account level. Do not construct raw API calls — use the MCP tools directly.

All tools require a `cloudId`. Try the site hostname first (e.g.
`justworks.atlassian.net`). If a tool errors with "cloud not found", call
`getAccessibleAtlassianResources` to retrieve the correct UUID, then retry.

---

## Tool selection

| Tool | Use for | Notes |
|---|---|---|
| `search` | "find pages about X", open-ended content discovery | Rovo Search — no `cloudId` needed. Best first call for natural language queries across both Confluence and Jira. |
| `searchConfluenceUsingCql` | Precise queries: by space, author, date, label, type | Use CQL when `search` returns too much noise. Needs `cloudId`. |
| `getConfluencePage` | Read a specific page by ID | Pass `contentFormat="html"` when you'll update the page afterward — html is round-trip safe. |
| `getConfluencePageDescendants` | List child pages of a page | Use to understand a page hierarchy before creating a new child. |
| `getPagesInConfluenceSpace` | Browse all pages in a space | Use `sort="-modified-date"` for recency. Supports `title` filter. |
| `getConfluenceSpaces` | List available spaces | Run when you need a `spaceId` for page creation. Returns numeric IDs. |
| `createConfluencePage` | Create a new page or blog post | Requires `spaceId` (numeric, from `getConfluenceSpaces`). Optional `parentId` for nested pages. |
| `updateConfluencePage` | Edit an existing page | Read the page first with `getConfluencePage(contentFormat="html")` to preserve structure. |
| `createConfluenceFooterComment` | Add a comment to a page | Standard page-level comment. Supports threading via `parentCommentId`. |
| `createConfluenceInlineComment` | Annotate specific text on a page | Requires `textSelection`, `textSelectionMatchCount`, and `textSelectionMatchIndex`. |
| `getConfluencePageFooterComments` | Read comments on a page | |
| `getConfluencePageInlineComments` | Read inline annotations | Defaults to `resolutionStatus="open"`. |
| `getAccessibleAtlassianResources` | Find your `cloudId` UUID | Only call this when a tool rejects the hostname-style cloudId. |
| `atlassianUserInfo` | Current user details | Use when you need the authenticated user's accountId for CQL (`creator = currentUser()`). |
| `fetch` | Get page details by ARI | Use when you have an ARI (e.g. from `search` results) rather than a plain page ID. |

---

## $ARGUMENTS routing

| Request pattern | Primary tool |
|---|---|
| "find pages about X" | `search(query="X")` |
| "show me page X" / URL provided | `getConfluencePage(pageId=<id>)` |
| "list pages in space X" | `getConfluenceSpaces` → `getPagesInConfluenceSpace` |
| "create a page about X in space Y" | `getConfluenceSpaces` → `createConfluencePage` |
| "update / edit page X" | `getConfluencePage(contentFormat="html")` → `updateConfluencePage` |
| "add a comment to page X" | `createConfluenceFooterComment` |
| "what are the child pages of X" | `getConfluencePageDescendants` |
| "find pages I wrote / updated recently" | `searchConfluenceUsingCql` with `creator = currentUser()` |
| "find pages in space X about Y" | `searchConfluenceUsingCql(cql='space = "KEY" AND text ~ "Y"')` |

---

## Standard workflows

### Find a page
```
search(query="your search terms")
```
Results include ARIs. To read a result's full content, extract the numeric page ID
from the ARI (`ari:cloud:confluence:<cloudId>:page/<pageId>`) and call
`getConfluencePage`, or pass the ARI directly to `fetch`.

### Read a page from a URL
Extract the page ID from the URL:
- `/wiki/spaces/KEY/pages/123456/Title` → pageId is `123456`
- `/wiki/x/AbCdEf` → pageId is the tiny link ID `AbCdEf`

Then:
```
getConfluencePage(cloudId="justworks.atlassian.net", pageId="123456", contentFormat="html")
```

### Create a new page
1. `getConfluenceSpaces(cloudId=...)` → find the `id` (numeric) for the target space
2. Optionally `getConfluencePageDescendants` to find a `parentId`
3. `createConfluencePage(cloudId=..., spaceId=<numeric id>, title="...", body="...", contentFormat="html")`

For body content, use `contentFormat="html"`. Allowed elements: standard HTML
headings, paragraphs, tables, lists, `<a>`, `<code>`, `<pre>`. Confluence-specific
elements use `data-type` attributes — see the HTML gotchas section below.

### Update an existing page
1. `getConfluencePage(cloudId=..., pageId=..., contentFormat="html")` — read current content
2. Modify the HTML body as needed
3. `updateConfluencePage(cloudId=..., pageId=..., body=<modified html>, contentFormat="html")`

Do not construct the updated body from scratch — preserve the existing structure and
only change what was asked. The tool handles version incrementing internally.

### Search within a specific space
```
searchConfluenceUsingCql(
  cloudId="justworks.atlassian.net",
  cql='space = "SPACEKEY" AND text ~ "search term"',
  limit=25
)
```

Common CQL patterns:
- `creator = currentUser() ORDER BY created DESC` — pages you created
- `lastModified >= "2026-01-01"` — recently modified
- `type = "blogpost"` — blog posts only
- `label = "meeting-notes"` — by label
- `ancestor = 12345` — all descendants of a page

### Add a comment
```
createConfluenceFooterComment(
  cloudId="justworks.atlassian.net",
  pageId="123456",
  body="<p>Your comment here.</p>",
  contentFormat="html"
)
```

---

## HTML content format

Use `contentFormat="html"` for creating and updating pages — it's round-trip safe
and supports all Confluence formatting.

**Standard HTML elements** (work as-is):
`<h1>`–`<h6>`, `<p>`, `<strong>`, `<em>`, `<u>`, `<s>`, `<ul>`, `<ol>`, `<li>`,
`<table>`, `<thead>`, `<tbody>`, `<tr>`, `<th>`, `<td>`, `<a href="...">`,
`<pre>`, `<code class="language-python">`, `<blockquote>`

**Confluence-specific elements** (use `data-type` attributes, not CSS classes):

```html
<!-- Info/warning/note/success/error panel -->
<div data-type="panel-info"><p>text</p></div>
<div data-type="panel-warning"><p>text</p></div>

<!-- Status badge -->
<span data-type="status" data-color="green">On Track</span>
<!-- Colors: green, red, yellow, blue, neutral, purple -->

<!-- Task list -->
<ul data-type="task-list">
  <li data-type="task-item"><input type="checkbox"> Item</li>
</ul>

<!-- Expand/collapse -->
<details><summary>Click to expand</summary><p>content</p></details>

<!-- User mention -->
<span data-type="mention" data-user-id="ACCOUNT_ID">@Name</span>

<!-- Two-column layout -->
<section data-type="layout-two-equal">
  <div data-type="column"><p>Left</p></div>
  <div data-type="column"><p>Right</p></div>
</section>
```

Never wrap content in `<html>`, `<head>`, or `<body>` tags — the body string is
the page content directly, not a full HTML document.

---

## Gotchas

**`spaceId` is numeric, not the space key** — `createConfluencePage` requires the
numeric `spaceId`, not a string key like `"ENG"`. Call `getConfluenceSpaces` to find
it. The `keys` param on `getConfluenceSpaces` can filter by space key to avoid
scanning everything.

**Read before updating** — always call `getConfluencePage(contentFormat="html")`
before `updateConfluencePage`. Reconstructing the body from scratch risks clobbering
macros, embedded images, or other content you can't see in plain text.

**Inline comments need exact text** — `createConfluenceInlineComment` requires
`textSelection` (the exact string to annotate), `textSelectionMatchCount` (how many
times that string appears on the page), and `textSelectionMatchIndex` (0-based which
match to annotate). Read the page content first to count matches.

**`search` vs `searchConfluenceUsingCql`** — use `search` for conversational
discovery; switch to CQL when you need precision (space-scoped, date-filtered,
label-filtered queries). CQL results don't include body content — follow up with
`getConfluencePage` for content.

**Blog posts vs pages** — most tools default to `contentType="page"`. Pass
`contentType="blog"` explicitly for blog posts. Blog posts don't support `parentId`.

**`fetch` vs `getConfluencePage`** — if you have an ARI string from `search`
results, use `fetch(id=<ari>)` directly; it extracts the cloudId automatically.
Use `getConfluencePage` when you have a plain numeric page ID or tiny link ID.

---

## Caveats

- Do not cache or persist page content beyond the immediate task.
- When rewriting a page's body, preserve any `data-type` macros or structured
  elements from the existing content — they may render complex layouts you cannot
  fully reconstruct from HTML inspection alone.
- CQL `limit` defaults to 25 and maxes at 250. For large result sets, use `cursor`
  for pagination.
