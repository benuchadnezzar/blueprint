---
name: diagram
description: Build professional process maps, lead routing diagrams, data flow diagrams, incident workflows, change management workflows, and A/B test process maps in Lucid using the Lucid MCP. Use this skill whenever the user asks to map, diagram, visualize, or document a process, workflow, lead routing flow, lifecycle, system handoff, or experiment — including phrases like "map this out," "diagram the flow," "draw the process," "show me how X works," "build a Lucid map," or "create a swimlane." Use it for both first-pass builds and iterations on existing maps. Use it even when the user doesn't explicitly mention Lucid, as long as they want a diagram of a multi-step process or workflow.
---

# diagram

A skill for building high-quality, logically sound process maps in Lucid via the Lucid MCP's `lucid_create_diagram_from_specification` tool. Backed by a template library that encodes the swimlane math, color palette, and shape conventions that prevent the common placement errors.

## When to use this skill

Trigger when the user asks for any of:

- Process maps, workflows, or lifecycle diagrams
- Lead routing diagrams (assignment, dedupe, SLA flows)
- Data flow diagrams (level 0, 1, or 2)
- Incident management or change management workflows
- A/B test / experiment process maps (showing assignment, arms, exclusions)
- System architecture handoffs across multiple platforms
- Swimlane diagrams of any kind

Also trigger when the user says "map this," "diagram this," "visualize how X works," or shows source materials (JSON exports, PRDs, system descriptions) and asks to make sense of them visually.

Do NOT trigger for non-process visuals like dashboards, charts, or one-off illustrations.

## Prerequisites — check these first

This skill cannot run without these three things in place:

1. **The Lucid MCP must be connected.** If `lucid_create_diagram_from_specification` and `Lucid:get_mcp_resource` are not in the available tools list, stop and tell the user to connect Lucid: Settings → Connectors → Lucid. Offer Mermaid as a sketch fallback but explain it imports as locked SVG, not editable native shapes.

2. **The template library must be findable.** This skill references templates by relative path. Default location: `../diagram/` relative to this skill's directory. If templates are missing, see "Template path resolution" below.

3. **Python 3.10+ must be available.** The helpers require it.

## Path resolution

This skill is part of the blueprint plugin. It needs two paths:

- `<plugin_root>/templates/diagram/` — the template library (palettes, presets, components, skeletons, examples, docs, schemas)
- `<plugin_root>/scripts/diagram/` — the Python helpers (lane_math, placement_audit, validators, builder)

Resolve `<plugin_root>` in this order:

1. Environment variable `BLUEPRINT_PLUGIN_ROOT` if set (use it directly)
2. Walk up from this SKILL.md's directory until you find a directory containing both `templates/diagram/presets/lane-presets.json` and `scripts/diagram/builder.py`. In a typical install, the plugin root is two parents up: `skills/diagram/SKILL.md` → `../..`
3. Check `~/.claude/plugins/blueprint/` (the documented default install location)
4. Ask the user: "Where is the blueprint plugin installed? I need the directory containing `templates/diagram/` and `scripts/diagram/`."

Override for templates alone: `PROCESS_MAPS_TEMPLATE_DIR` env variable (used by the builder helper as well).

Once `<plugin_root>` is located, store it for the session. All bash/python invocations in this skill use that path.

## Audience question — ask first

Before producing any map, ask the user:

> Is this map for (A) internal Marketing Ops / RevOps, or (B) cross-functional stakeholders?

Use the `ask_user_input_v0` tool if available. The audience determines language depth:

- **Internal:** Use technical, precise language. Include system names, object/field names, events, APIs, identifiers, error handling, retries, SLAs. Precision over simplicity.
- **Stakeholders:** Avoid jargon (API, ETL, schema, OAuth). Prioritize clarity, outcomes, ownership, impact. Simplify backend mechanics while preserving logical accuracy.

If the user already specified the audience in the request, skip the question and proceed.

## The build flow — every step is required

For a first-pass map of a new process, follow this order. Do not skip steps. The whole point of this skill is that it encodes the discipline that prevents rework.

### Step 1: Clarifying questions

Surface 1–4 high-signal questions. Separate "Required to Proceed" from "Nice to Have." Use `ask_user_input_v0` for any question that has 2+ discrete answer choices. Do not bury choices in prose.

For iterations on an existing map (revisions, fixes, additions), skip this step unless something is genuinely ambiguous.

### Step 2: Assumptions

List numbered, explicit assumptions. State them as assumptions, not facts. The user should be able to red-line them.

### Step 3: Pick lane pattern and preset

System lanes (lanes represent owning systems like Salesforce, Customer.io, Default) for end-to-end multi-platform flows. Function lanes (lanes represent stages like Entry, Match, Decide, Route, Notify, Write) for routing-heavy workflows in one system. Never mix the two in one map.

Read `<template_dir>/presets/lane-presets.json` and pick the preset closest to the map's needs. If no preset fits, copy the closest one and modify lane widths — but the new lane widths MUST still sum to the boundingBox stacking dimension.

### Step 4: Plan node placements

Plan as a list of `(node_id, semantic_kind, target_lane, x, y, w, h, text)`. Semantic kinds: `terminator_start_end`, `terminator_success_end`, `process`, `system_action`, `decision`, `database_write`, `out_of_scope`, `warning_callout`, `sub_process_link`. Each has a pre-defined fill/stroke/dimensions in `<template_dir>/components/node-components.json`.

**Layout discipline rule:** for horizontal swimlanes, time/sequence flows along the X axis; lane membership lives on the Y axis. Every node's Y range must fall within its target lane's interior Y range. Same idea inverted for vertical swimlanes. Read `<template_dir>/docs/layout-discipline.md` if uncertain.

**Decision shape dimensions:** minimum 280w × 140h. Smaller diamonds rotate text vertically and become unreadable.

### Step 5: Build with the helpers — REQUIRED

Do NOT hand-write the Lucid JSON. Use the `DiagramBuilder` class. This is the highest-leverage rule in the skill — most of the errors this skill prevents come from doing the math by hand.

Write a Python script that:

1. Adds `<template_dir>/helpers` to `sys.path`
2. Imports `DiagramBuilder`
3. Calls `set_swimlanes(preset_name=...)` (or custom lanes if no preset fits)
4. Calls `add_node(...)` for each node, with `lane=` specifying the target lane title exactly
5. Calls `connect(source_id, target_id, kind=..., label=...)` for each connector
6. For warnings/risks identified during the build, calls `add_warning(callout_id, near_node_id, lane, x, y, text)` — this adds a red rectangle and a red dashed link automatically
7. Calls `run_audit()` and prints the markdown table
8. Calls `validate()` and prints the report
9. If both pass, calls `build()` and writes the payload to a JSON file

Run the script with `python3 build_map.py`. Read the audit table and validation report.

Example template for the script:

\```python
import sys, json
sys.path.insert(0, "<plugin_root>/scripts/diagram")
from builder import DiagramBuilder

b = DiagramBuilder()
b.set_swimlanes(preset_name="horizontal_5_lane_system_end_to_end")

b.add_node("nl_in", "terminator_start_end", lane="Lane 1",
           x=100, y=100, text="IN: New Lead")
b.add_node("nl_match", "process", lane="Lane 1",
           x=400, y=100, text="Match Contact")
b.connect("nl_in", "nl_match")

ok, audit_table = b.run_audit()
print("PLACEMENT AUDIT:")
print(audit_table)

report = b.validate()
print("\nVALIDATION:")
print(report.to_markdown())

if ok and report.ok:
    payload = b.build()
    with open("payload.json", "w") as f:
        json.dump(payload, f, indent=2)
    print("\nPayload written.")
else:
    print("\nBuild halted — fix errors above before sending to Lucid.")
\```

### Step 6: Handle the validation result

**If errors are reported**, halt the build. Surface the errors to the user with a clear explanation of what failed. Do not send to Lucid. Iterate on the script until errors are resolved.

**If only warnings are reported**, show the warnings to the user but proceed to step 7. Warnings are informational (e.g., "this color isn't in the sanctioned set," "consider splitting this dense map").

### Step 7: Send to Lucid MCP

Load the saved payload JSON. Pass its contents (NOT a path, the actual JSON string) to `lucid_create_diagram_from_specification` as `standard_import_json`. Set `use_assisted_layout: false` at the tool call level for any map with 30+ nodes.

### Step 8: Report results to the user

Provide:

- Lucid edit URL for the new document
- A summary of structural choices (lane pattern, preset used, node count)
- The pre-build placement audit table
- Any validation warnings that fired
- An honest expectation of manual cleanup needed (see the table below)

| Node count | Expected manual cleanup |
|------------|------------------------|
| ≤ 30 | 0–5% |
| 30–50 | 5–15% |
| 50+ | 15–30%, strongly consider splitting |

### Step 9: Gap & risk review (for internal audience)

After delivering the map, run through the source materials and process logic and surface concerns the user may not have asked about. Look for:

- **Code bugs** (assignment vs. comparison operators, off-by-one, null handling)
- **Field overloading** (one field carrying multiple unrelated meanings)
- **Naming inconsistencies** across systems (e.g., `experiment_variant` vs `experiment_arm`)
- **Asymmetric branches** (condition checked in workflow A but not in parallel workflow B)
- **Missing observability** (feature-flag assignments without logging, async events without traces)
- **Slack channels with no defined triage owner**
- **Dedupe gaps** (arrays/lists that append without dedupe)
- **SLA gaps** and undefined timing expectations
- **Implicit assumptions** not documented anywhere

For each concern, codify it both inline in the map (using `add_warning(...)` to create a red callout linked to the affected node) AND in a written Gap & Risk Review section below the map.

This step is REQUIRED for internal audience maps. Skip for stakeholder maps unless the user explicitly asks for it.

### Step 10: Process Maturity Assessment

After Gap & Risk Review, score the process on six dimensions: Governance, Data Integrity, Exception Handling, Observability, Scalability, Clarity. Each 1–5 with rationale and "to reach next level." If critical controls are missing (owner, exception path, monitoring), cap overall maturity at 2.5.

Format:

```
## Process Maturity Assessment

Governance: X/5
- Rationale:
- To reach next level:

Data Integrity: X/5
- Rationale:
- To reach next level:

[etc. for the other four dimensions]

Overall Maturity: X.X / 5

[Brief executive interpretation]
```

Required on every map (first pass and iteration), per the project conventions.

## Iteration mode (lean output)

When the user is iterating on an existing approved map (revisions, fixes, additions), use this leaner sequence instead of the full first-pass flow:

1. Brief description of what's changing and why
2. Run the placement audit ONLY for new or moved nodes
3. Build (full helper script — same step 5 as before)
4. Process Maturity Assessment

Skip clarifying questions, assumptions, and Gap & Risk Review unless something new surfaces.

For substantial restructuring (changed lane assignments, repositioning most nodes), recreate the document from scratch with a version-suffixed title (e.g., "Map 5 v3") rather than editing dozens of items. The MCP cannot delete entire documents — tell the user which old doc URL to manually trash in the Lucid UI.

## Splitting dense maps

Hard limits:

- ≤ 30 nodes: single map
- 30–50 nodes: consider splitting if natural sub-process boundaries exist
- 50+ nodes: split by default

When splitting, build a master/overview map with purple `sub_process_link` placeholder shapes pointing at the sub-process maps. Each sub-process is a separate Lucid document. **Cross-document hyperlinks must be added manually** — right-click the placeholder in Lucid → Link → paste URL. The MCP cannot do this. Tell the user.

## Things the Lucid MCP cannot do

Set realistic expectations:

- Delete entire documents (only items within them)
- Edit lane header colors after creation
- Auto-route connectors reliably in dense clusters (manual cleanup expected for 30+ node maps)
- Place nodes precisely when `assistedLayout: true` (use `false` for dense maps)
- Add cross-document hyperlinks (user does this manually in Lucid)

## What's available in the plugin

Templates (under `<plugin_root>/templates/diagram/`):

- `presets/lane-presets.json` — 6 pre-validated swimlane configurations
- `palettes/colors.json` — standardized color palette
- `palettes/colors-justworks.json` — optional Justworks-specific extensions
- `components/node-components.json` — 9 node templates + 4 connector templates
- `skeletons/empty-with-legend.json` — empty payload with color/shape key
- `skeletons/empty-no-legend.json` — empty payload for sub-process maps
- `examples/` — three minimal validated reference diagrams
- `docs/build-procedure.md` — the long-form build procedure
- `docs/layout-discipline.md` — the lane-y vs sequence-y rule
- `docs/known-constraints.md` — what the Lucid MCP can and cannot do
- `schemas/lucid-standard-import.md` — annotated schema reference

Helpers (under `<plugin_root>/scripts/diagram/`):

- `lane_math.py` — lane width validation, Y-boundary computation
- `placement_audit.py` — pre-build audit
- `validators.py` — pre-flight payload validation
- `builder.py` — `DiagramBuilder` class (the primary entry point)

For map-type-specific guidance, read `references/map-types.md` in this skill.

## When to read what

Don't read every reference on every invocation. Load on demand:

- **First time using the skill:** read this SKILL.md only.
- **Stuck on lane math or layout:** read `<plugin_root>/templates/diagram/docs/layout-discipline.md`.
- **Building a specific map type (lead routing, DFD, etc.):** read `references/map-types.md` in this skill.
- **Unclear on Lucid schema details:** read `<plugin_root>/templates/diagram/schemas/lucid-standard-import.md`.
- **Need realistic expectations to set with user:** read `<plugin_root>/templates/diagram/docs/known-constraints.md`.

## Failure modes — recognize and respond

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| API rejects payload with "lane widths must sum to..." | Lane width sum doesn't match boundingBox.h (or .w for vertical) | Adjust lane widths via `helpers/lane_math.py::adjust_lane_widths_to_sum`, re-run |
| Decision text renders vertically | Diamond is smaller than 280×140 | Increase decision shape dimensions |
| Nodes appear in wrong lanes | Placed by sequence-y instead of lane-y | Run `run_audit()`; for failing nodes, shift y into target lane's interior |
| Connectors overlap shape text | Default-center attachment | Specify position on BOTH endpoints (or omit position entirely for smart routing) |
| Diagram looks crowded | Too many nodes per lane | Split into sub-process maps |

## What this skill does NOT do

- Decide what the process should be. That requires understanding the business logic. The user supplies the process; this skill renders it correctly.
- Edit lane colors after creation (Lucid MCP limitation).
- Generate non-process diagrams (dashboards, illustrations, charts).
- Send Mermaid output as a final deliverable. Mermaid is only for quick sketches before Lucid is available.
