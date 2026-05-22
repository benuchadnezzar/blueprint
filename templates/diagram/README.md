# Process Map Templates for Lucid

A template library for building Lucid process maps via the `lucid_create_diagram_from_specification` MCP tool. Designed to encode hard-won layout rules so consumers (LLMs or humans) don't have to rediscover them.

## Philosophy

The Lucid MCP can produce professional editable diagrams, but it's easy to make placement errors that don't surface until the diagram renders. This template library encodes the rules that prevent those errors:

- **Swimlane math** must sum exactly to the container's stacking-axis dimension
- **Nodes must fit inside lane interiors**, not just the outer container
- **Decision diamonds need minimum dimensions** (280×140) to keep text horizontal
- **Lane headers need light fills with dark text** for readability
- **Connectors prefer auto-link to shapes** over fixed coordinates that overlap text

Use the JSON files for structure and the Python helpers for math you don't want to do by hand.

## Directory layout

```
process-maps/
├── README.md                          You are here
├── schemas/
│   └── lucid-standard-import.md       Annotated reference for the Lucid Standard Import JSON
├── palettes/
│   ├── colors.json                    Standardized color palette for nodes, lanes, connectors
│   └── colors-justworks.json          Optional Justworks-specific lane colors
├── presets/
│   ├── lane-presets.json              Pre-validated swimlane configurations
│   └── lane-presets-justworks.json    Optional Justworks-specific lane configurations
├── components/
│   └── node-components.json           Reusable shape definitions (terminator, process, decision, etc.)
├── skeletons/
│   ├── empty-with-legend.json         Empty diagram with the color/shape key pre-built
│   └── empty-no-legend.json           Empty diagram without legend (for sub-process maps)
├── examples/
│   ├── 2-lane-system-handoff.json     Minimal example: 2 lanes, ~6 nodes
│   ├── 5-lane-routing.json            Minimal example: 5 functional lanes, ~12 nodes
│   └── system-end-to-end.json         Minimal example: 4 system lanes, ~10 nodes
├── helpers/
│   ├── lane_math.py                   Compute lane Y-boundaries, validate lane widths
│   ├── placement_audit.py             Generate the pre-build placement audit table
│   ├── builder.py                     Convenience builders for nodes, lines, swimlanes
│   └── validators.py                  Pre-flight validation of a complete payload
└── docs/
    ├── build-procedure.md             Step-by-step procedure for building a map
    ├── layout-discipline.md           The rules that prevent placement errors
    └── known-constraints.md           What the Lucid MCP can and cannot do
```

## Build procedure (the short version)

1. **Pick a lane pattern** — system lanes (Customer.io, Salesforce, etc.) for end-to-end flows; function lanes (Entry, Match, Decide, etc.) for routing-heavy maps. Don't mix.
2. **Pick a lane preset** from `presets/lane-presets.json` closest to your needs. Adjust lane widths if necessary — `helpers/lane_math.py` validates the sum.
3. **Compute lane Y-boundaries** with `helpers/lane_math.py::compute_lane_boundaries()`. Cache this — every node placement check uses it.
4. **Plan node placements** as a list of `(node_id, target_lane, x, y, w, h)`. Time advances along the X axis (horizontal swimlanes) or Y axis (vertical swimlanes). Lane membership is on the OTHER axis.
5. **Run pre-build placement audit** with `helpers/placement_audit.py::audit()`. Every node's Y range must fit its target lane's interior Y boundaries. If any node fails, fix before continuing.
6. **Assemble the JSON** starting from `skeletons/empty-with-legend.json`. Copy node component definitions from `components/node-components.json` and customize text + position.
7. **Run pre-flight validation** with `helpers/validators.py::validate_payload()`. Catches missing required fields, mismatched lane sums, endpoint type errors.
8. **Send to `lucid_create_diagram_from_specification`**.
9. **Expect 5–15% manual cleanup in Lucid** — the API can't perfectly route connectors in dense clusters. See `docs/known-constraints.md`.

See `docs/build-procedure.md` for the long version.

## When to split a map

Hard limits:

- ≤ 30 nodes: single map
- 30–50 nodes: consider splitting if natural sub-process boundaries exist
- 50+ nodes: split by default — density at this scale produces overlapping connectors the Lucid API can't reliably resolve

When splitting, build a master/overview map with purple sub-process placeholder shapes (see `components/node-components.json::sub_process_link`) that link to detailed sub-process maps. Cross-document hyperlinks must be added manually in Lucid (right-click shape → Link → paste URL) — the MCP does not support this.

## Generic vs. Justworks-specific files

Files without a suffix are generic and work for any GTM context. Files with `-justworks` are specific to the Justworks stack (Customer.io, Salesforce, Default, LaunchDarkly) and demonstrate how to extend the generic base for a particular company. Use them as a reference if you're building for Justworks; ignore them otherwise.

## Honesty about what this template can't do

The template handles structure, math, and styling. It cannot:

- **Decide what the process should be.** That requires understanding the underlying business logic, source materials, and stakeholder intent. The model still has to do that work.
- **Auto-route connectors through dense clusters.** Maps with 30+ nodes will need manual connector cleanup in Lucid.
- **Place nodes with absolute precision when assistedLayout is true.** For dense maps, use `assistedLayout: false` on the swimlane container.
- **Delete Lucid documents.** Superseded docs must be trashed from the Lucid UI manually.
- **Edit lane header colors after creation.** Set them correctly at creation time.
