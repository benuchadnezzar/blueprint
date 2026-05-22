# Build Procedure

Step-by-step procedure for building a process map. Follow this every time to keep iteration rounds low.

## Step 0: Decide if a single map is right

Hard limits:

- ≤ 30 nodes: single map
- 30–50 nodes: consider splitting at natural sub-process boundaries
- 50+ nodes: split by default

If splitting, build a master overview map first, then build each sub-process as a separate Lucid document. The master uses purple sub-process placeholder shapes (`components/node-components.json::sub_process_link`) to point at the sub-processes.

## Step 1: Pick a lane pattern

System lanes or function lanes — never both in the same map.

- **System lanes** when the map crosses 2+ platforms (e.g., Customer.io → Default → Salesforce) and the question is which system owns which step.
- **Function lanes** when most steps live in one system but the map shows phases of work (Entry, Match, Decide, Route, Notify, Write).

## Step 2: Pick a lane preset

Open `presets/lane-presets.json` and select the preset closest to your need. The lane widths are pre-validated; the y-boundaries are pre-computed.

If no preset fits exactly, copy the closest one and modify. After modifying, validate with `helpers/lane_math.py::validate_lane_widths()`.

## Step 3: Cache lane Y-boundaries

You'll be checking every node's y against these boundaries during placement. Compute once with `helpers/lane_math.py::compute_lane_boundaries()` and keep the result alongside your planning notes.

## Step 4: Plan node placements

For each node, decide:

- **Semantic kind:** terminator, process, decision, system_action, database_write, etc. (See `components/node-components.json`.)
- **Target lane:** which lane title from the swimlane spec.
- **Position (x, y, w, h):** in canvas coordinates. The most important rule:

> Time/sequence advances along the X axis (for horizontal swimlanes) or Y axis (for vertical swimlanes). Lane membership lives on the OTHER axis.

Concretely: for a horizontal swimlane, the node's `y` must fall within its target lane's interior Y range. Don't place by sequence order on the y axis — that's the #1 source of "everything ends up in the wrong lane" errors.

## Step 5: Run the pre-build placement audit

REQUIRED. Use `helpers/placement_audit.py::audit()` to verify every node fits its target lane's interior. The audit produces a markdown table:

| Node ID | Target Lane | Y range | Lane Y boundaries | Fits? |
|---------|-------------|---------|-------------------|-------|
| nl_in | Entry | 100–180 | 50–250 | OK |
| nl_match_c | Match | 280–360 | 250–580 | OK |

If any row says FAIL, fix it before continuing. Common fixes:

- Shift the node's y into its lane's interior range
- Widen the lane to accommodate the node's height
- Verify the target_lane title exactly matches the lane spec

## Step 6: Assemble the payload

Start from `skeletons/empty-with-legend.json`. Replace the swimLanes config with your chosen preset. Add your nodes (using `components/node-components.json` templates) and connectors.

Or, use `helpers/builder.py::DiagramBuilder` to do this programmatically:

```python
from helpers.builder import DiagramBuilder

b = DiagramBuilder()
b.set_swimlanes(preset_name="horizontal_7_lane_functional_routing")
b.add_node("nl_in", "terminator_start_end", lane="Entry", x=30, y=100, text="IN: New Lead")
b.add_node("nl_match", "process", lane="Match", x=240, y=280, text="Match Contact")
b.connect("nl_in", "nl_match")

ok, audit_table = b.run_audit()
report = b.validate()
if ok and report.ok:
    payload = b.build()
```

## Step 7: Pre-flight validate

REQUIRED. Use `helpers/validators.py::validate_payload()` to catch:

- Lane width sum mismatches
- Duplicate IDs
- Connectors referencing non-existent shapes
- Decision shapes under the 280×140 minimum
- Partial endpoint position specifications
- Emoji in text
- Payload size approaching 2 MB

Fix all errors before sending. Review warnings.

## Step 8: Send to Lucid MCP

Pass the payload as `standard_import_json` to `lucid_create_diagram_from_specification`. Set `use_assisted_layout: false` at the call level for dense maps (the assistedLayout setting INSIDE the swimLanes container should also be false — both layers matter).

## Step 9: Expect manual cleanup

Even with everything correct, expect 5–15% of shapes in dense maps to need manual repositioning in Lucid. The API can't perfectly route connectors in dense clusters. Tell the user this upfront, not as a post-hoc apology.

## Iteration tips

- For small text/color changes on a few shapes, use `lucid_edit_item`.
- For substantial restructuring (lane reassignments, repositioning many shapes), recreate the document from scratch with the corrected spec. Name the new doc with a version suffix (e.g., "Map 5 v3") and tell the user which old doc(s) to trash from the Lucid UI.
- The MCP cannot delete entire documents. Communicate this constraint.
