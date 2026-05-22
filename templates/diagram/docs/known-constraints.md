# Known Constraints

What the Lucid MCP and this template library can and cannot do. Setting realistic expectations prevents the "why doesn't it just work" frustration.

## Lucid MCP cannot

- **Delete entire documents.** Only items within a document can be deleted via `lucid_delete_items`. To remove a superseded doc, the user must trash it from the Lucid UI (right-click in the Documents list → Move to Trash). Always communicate this when you replace a doc with a new version — list the old doc URL and ask the user to trash it.
- **Edit lane header colors or lane fills after creation.** These are set at swimLanes creation time and aren't editable through `lucid_edit_item`. If you need to change lane colors, you must recreate the diagram.
- **Reliably auto-route connectors through dense clusters.** Maps with 30+ nodes will have some connectors overlapping shapes or crossing other connectors. Manual cleanup in Lucid is expected.
- **Place nodes with absolute precision when `assistedLayout: true`.** The layout engine overrides explicit coordinates. For dense maps, use `assistedLayout: false` on the swimLanes container.
- **Add cross-document hyperlinks.** Sub-process placeholder shapes don't auto-link to their detailed sub-process maps. The user must right-click each placeholder shape in Lucid, choose Link, and paste the URL.
- **Preserve internal IDs across API calls.** The `id` you specify in the import payload becomes the Lucid item's logical identifier, but post-import operations (edits, deletes) need IDs from a `Lucid:fetch` call to find the actual items.

## Lucid MCP can but often fails to

- **Render decision diamond text horizontally when the diamond is small.** Below 280×140, Lucid rotates text to fit the inscribed rectangle of the diamond. Always use 280×140 minimum for decisions.
- **Smart-route connectors when neither endpoint specifies a position.** It works fine for sparse diagrams. In dense diagrams, default-center attachment causes connectors to overlap shape text. Specify position on BOTH endpoints (or neither — Lucid rejects partial specifications).
- **Handle dense connector convergence.** A single node with 5+ incoming connectors is a layout headache. Consider splitting or using a fan-in pattern with an intermediate node.

## This template library cannot

- **Decide what the process should be.** Templates handle structure, math, and styling. The semantic content (which steps exist, what they do, how they relate) requires understanding the underlying business logic. The model still has to do that work.
- **Handle every conceivable lane configuration.** The presets cover common shapes; novel layouts require custom configuration. Use `helpers/lane_math.py::validate_lane_widths()` after any modification.
- **Validate that your node positions reflect the actual process flow.** The placement audit only checks that nodes fit their declared lanes. It doesn't know whether `nl_apollo` should be in Enrich vs. Decide — that's a domain decision.

## Realistic expectations for first-pass output

Even with the template library used correctly:

- **Sparse maps (≤ 30 nodes):** Usually render correctly on the first build. 0–5% of shapes may need manual nudges.
- **Medium maps (30–50 nodes):** Render mostly correctly. 5–15% of shapes need manual repositioning, especially in dense decision rows.
- **Large maps (50+ nodes):** Usually need to be split. If forced into one map, expect 15–30% manual cleanup. Strongly consider sub-process splitting.

Tell users this upfront. Setting expectations is cheaper than apologizing after the fact.
