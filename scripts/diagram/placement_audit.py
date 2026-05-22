"""
Pre-build placement audit.

The single biggest source of layout errors in Lucid swimlane diagrams is
placing nodes by sequence-y when they should be placed by lane-y. Every node's
bounding box MUST fit entirely within its target lane's interior — straddling
lane boundaries causes Lucid to render the node in the wrong lane (or fail
silently).

This module produces a markdown audit table that catches these errors before
they ship.
"""

from dataclasses import dataclass

from lane_math import LaneBoundary, compute_lane_boundaries


@dataclass
class NodePlacement:
    """A node's intended placement: which lane, and what bounding box."""

    node_id: str
    target_lane: str  # Must match a lane title from the swimLanes spec
    x: int
    y: int
    width: int
    height: int

    @property
    def y_top(self) -> int:
        return self.y

    @property
    def y_bottom(self) -> int:
        return self.y + self.height

    @property
    def x_left(self) -> int:
        return self.x

    @property
    def x_right(self) -> int:
        return self.x + self.width


def audit(
    placements: list[NodePlacement],
    lanes: list[dict],
    titleBar_height: int = 50,
    vertical: bool = False,
) -> tuple[bool, str]:
    """
    Run the pre-build placement audit.

    Args:
        placements: list of NodePlacement objects describing every node to be placed
        lanes: list of lane spec dicts (with 'title' and 'width')
        titleBar_height: height of the swimLanes titleBar
        vertical: True if swimlanes are vertical

    Returns:
        (all_pass, markdown_table) — all_pass is True if every node fits its lane.

    The markdown_table is suitable for printing as part of a chat response or
    committing to a build log.
    """
    boundaries = compute_lane_boundaries(lanes, titleBar_height, vertical)
    by_title: dict[str, LaneBoundary] = {b.title: b for b in boundaries}

    axis_label = "X" if vertical else "Y"
    rows = []
    all_pass = True

    for p in placements:
        if p.target_lane not in by_title:
            rows.append(
                {
                    "node": p.node_id,
                    "lane": p.target_lane,
                    "range": f"{p.y_top}-{p.y_bottom}" if not vertical else f"{p.x_left}-{p.x_right}",
                    "lane_bounds": "(LANE NOT FOUND)",
                    "fits": "ERROR",
                }
            )
            all_pass = False
            continue

        b = by_title[p.target_lane]
        if vertical:
            low, high = p.x_left, p.x_right
        else:
            low, high = p.y_top, p.y_bottom

        fits = b.contains(low, high)
        if not fits:
            all_pass = False

        rows.append(
            {
                "node": p.node_id,
                "lane": p.target_lane,
                "range": f"{low}-{high}",
                "lane_bounds": f"{b.interior_min}-{b.interior_max}",
                "fits": "OK" if fits else "FAIL",
            }
        )

    # Render as markdown table
    lines = [
        f"| Node ID | Target Lane | {axis_label} range | Lane {axis_label} boundaries | Fits? |",
        "|---------|-------------|---------|-------------------|-------|",
    ]
    for r in rows:
        lines.append(
            f"| {r['node']} | {r['lane']} | {r['range']} | {r['lane_bounds']} | {r['fits']} |"
        )

    if not all_pass:
        lines.append("")
        lines.append("**Audit failed.** One or more nodes do not fit their target lane.")
        lines.append("Fix the failing nodes before sending the build to Lucid.")
        lines.append("Common fixes:")
        lines.append("- Shift the node's y (or x for vertical lanes) into its lane's interior range")
        lines.append("- Widen the lane to accommodate the node's height (or width for vertical)")
        lines.append("- Verify the target_lane title matches the lane spec exactly")

    return all_pass, "\n".join(lines)


def from_shapes(shape_dicts: list[dict], lane_assignments: dict[str, str]) -> list[NodePlacement]:
    """
    Convenience: build NodePlacement list from a list of Lucid shape dicts and
    a {node_id: lane_title} mapping.

    Useful when you've already constructed the shape definitions and just need
    to audit them.

    Args:
        shape_dicts: list of shape definitions, each with 'id' and 'boundingBox'
        lane_assignments: dict mapping shape id to lane title
    """
    placements = []
    for s in shape_dicts:
        sid = s["id"]
        if sid not in lane_assignments:
            continue
        bb = s["boundingBox"]
        placements.append(
            NodePlacement(
                node_id=sid,
                target_lane=lane_assignments[sid],
                x=bb["x"],
                y=bb["y"],
                width=bb["w"],
                height=bb["h"],
            )
        )
    return placements


if __name__ == "__main__":
    # Self-test: a few nodes against the 7-lane functional routing preset
    lanes = [
        {"title": "Entry", "width": 200},
        {"title": "Match", "width": 330},
        {"title": "Enrich", "width": 140},
        {"title": "Decide", "width": 620},
        {"title": "Route / Assign", "width": 270},
        {"title": "Cadence / Notify", "width": 370},
        {"title": "Write", "width": 440},
    ]
    placements = [
        NodePlacement("nl_in", "Entry", x=30, y=100, width=160, height=80),
        NodePlacement("nl_match_c", "Match", x=240, y=280, width=280, height=80),
        NodePlacement("nl_apollo", "Enrich", x=880, y=600, width=220, height=80),
        NodePlacement("nl_dec", "Decide", x=1240, y=820, width=280, height=140),
        NodePlacement("nl_bad", "Match", x=240, y=900, width=280, height=80),  # FAIL: y outside Match
    ]
    all_pass, table = audit(placements, lanes, titleBar_height=50, vertical=False)
    print(table)
    print(f"\nAll pass: {all_pass}")
