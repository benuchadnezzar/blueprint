# Layout Discipline

The single biggest source of placement errors in Lucid swimlane diagrams is one mental-model mistake. Internalize this:

> **Time/sequence advances along the X axis. Lane membership lives on the Y axis.** (For horizontal swimlanes. For vertical, swap X and Y.)

## What this looks like in practice

For a horizontal swimlane (lanes stacked top-to-bottom):

- **DO:** each lane gets its own horizontal track. Nodes inside a lane flow LEFT-TO-RIGHT (advancing in time) within that lane's vertical band. Connectors that cross between lanes go up or down to enter the next lane.
- **DON'T:** place nodes vertically as if y-coordinate represented the step number. This puts node #5 in lane 3 just because it's the 5th step; in reality node #5 might be owned by lane 1.

## The error mode

When you place by sequence-y, every node "ends up" in whichever lane its sequence number happens to fall through. Lucid renders them inside the swimlane container, but they show up in the wrong lanes. Visually, the lane backgrounds look striped because nodes cross lane boundaries, and the lane labels mean nothing because the labels say "Customer.io" but the nodes inside are actually about Salesforce.

This error is silent — the API doesn't reject the payload. You'll only see it when the diagram renders.

## The rule restated as a checklist

Before placing any node, ask:

1. **Which lane does this node belong to?** (Owner system, or owner function — whichever pattern you chose.)
2. **What is that lane's interior Y range?** (Use `helpers/lane_math.py::compute_lane_boundaries()`.)
3. **Does my node's y range (y_top to y_bottom) fit entirely within that lane's interior Y range?** If not, change `y` until it does.
4. **What x should the node have?** This is where sequence/time goes. Earlier-in-flow nodes have smaller x; later have larger x. Adjust the canvas width if you run out of room.

## Worked example

Suppose you have a 5-lane horizontal swimlane with these interiors:

- Entry: y=50–250
- Match: y=250–580
- Enrich: y=580–720
- Decide: y=720–1340
- Write: y=1340–2370

You're placing 11 sequential decision nodes that all belong to the **Decide** lane. They should NOT be at y=820, 940, 1060, 1180, 1300, etc. (which would push some out of the Decide lane). They should ALL be at roughly the same y (e.g., y=820–960), but at increasing x values:

| Node | x | y | Reasoning |
|------|---|---|-----------|
| dec1 | 1180 | 820 | First decision, leftmost in Decide row |
| dec2 | 1490 | 820 | Second decision, 310 to the right |
| dec3 | 1800 | 820 | Third, 310 to the right |
| ... | ... | 820 | All in Decide lane, advancing along x |

The connectors then flow LEFT-TO-RIGHT between the decisions. If a decision branches into the Route/Assign lane below, that connector goes DOWN to a node at, say, x=1180, y=1380 (which is in Route/Assign).

## Vertical swimlanes

For `vertical: true`, swap X and Y everywhere. Time/sequence flows TOP-TO-BOTTOM on the Y axis. Each lane occupies a column on the X axis. Place nodes by checking x against the lane's interior X range.

## How to confirm you got it right

Use `helpers/placement_audit.py::audit()`. Pass it your list of placements and your swimlane config; it produces a table showing each node's y range, the lane's interior y range, and a `Fits?` column. If everything says OK, your layout discipline is intact.
