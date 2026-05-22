"""
Lane math utilities for Lucid swimlane diagrams.

The Lucid Standard Import format requires that:
- For horizontal swimlanes (vertical: false): sum of lane widths equals boundingBox.h
- For vertical swimlanes (vertical: true): sum of lane widths equals boundingBox.w
- The titleBar height is INCLUDED in the lane width sum

This module provides:
- compute_lane_boundaries(): given a lane spec, compute each lane's interior boundaries
- validate_lane_widths(): confirm lane widths sum correctly
- adjust_lane_widths_to_sum(): rescale lanes to match a target sum
- describe_lane_layout(): human-readable summary
"""

from dataclasses import dataclass
from typing import Literal


@dataclass
class LaneBoundary:
    """Interior region of a single lane within a swimlanes container."""

    title: str
    width: int
    # For horizontal (vertical: false), interior_min/max are Y coords
    # For vertical (vertical: true), interior_min/max are X coords
    interior_min: int
    interior_max: int

    def contains(self, low: int, high: int) -> bool:
        """Return True if the range [low, high] fits inside this lane's interior."""
        return low >= self.interior_min and high <= self.interior_max


@dataclass
class ValidationResult:
    """Result of validating a lane configuration."""

    ok: bool
    expected_sum: int
    actual_sum: int
    issues: list[str]

    def __bool__(self) -> bool:
        return self.ok


def compute_lane_boundaries(
    lanes: list[dict],
    titleBar_height: int = 50,
    vertical: bool = False,
) -> list[LaneBoundary]:
    """
    Compute the interior boundary of each lane.

    Args:
        lanes: list of dicts with at least 'title' and 'width' keys
        titleBar_height: height of the titleBar (default 50)
        vertical: whether the swimlanes are vertical (lanes side-by-side)

    Returns:
        List of LaneBoundary objects in the same order as input

    For horizontal swimlanes (vertical=False), each lane's interior runs along the Y axis.
    For vertical swimlanes (vertical=True), each lane's interior runs along the X axis.
    Either way, the first lane's interior starts at `titleBar_height` (not 0) because
    the titleBar occupies the leading edge.
    """
    # Lane widths are absolute extents along the stacking axis. The first
    # lane occupies y=[0, lane[0].width); its interior (excluding the
    # titleBar) is y=[titleBar_height, lane[0].width). Subsequent lanes have
    # no titleBar overlap, so their interior matches their full extent.
    cursor = 0
    boundaries = []
    for i, lane in enumerate(lanes):
        lane_start = cursor
        lane_end = cursor + lane["width"]
        # First lane has a titleBar occupying the leading edge of the lane
        interior_min = lane_start + titleBar_height if i == 0 else lane_start
        interior_max = lane_end
        boundaries.append(
            LaneBoundary(
                title=lane["title"],
                width=lane["width"],
                interior_min=interior_min,
                interior_max=interior_max,
            )
        )
        cursor = lane_end

    return boundaries


def validate_lane_widths(
    lanes: list[dict],
    bounding_box: dict,
    vertical: bool = False,
) -> ValidationResult:
    """
    Check that lane widths sum to the correct boundingBox dimension.

    Args:
        lanes: list of dicts with 'width' keys
        bounding_box: dict with 'w' and 'h' keys
        vertical: True if swimlanes are vertical (lanes side-by-side)

    Returns:
        ValidationResult with ok flag, expected_sum, actual_sum, and any issues.
    """
    actual_sum = sum(lane["width"] for lane in lanes)
    expected_sum = bounding_box["w"] if vertical else bounding_box["h"]
    issues = []
    if actual_sum != expected_sum:
        axis = "boundingBox.w" if vertical else "boundingBox.h"
        issues.append(
            f"Lane widths sum to {actual_sum} but {axis} is {expected_sum}. "
            f"Difference: {expected_sum - actual_sum:+d}. "
            f"Adjust one or more lane widths so they sum exactly to {expected_sum}."
        )
    return ValidationResult(
        ok=(not issues),
        expected_sum=expected_sum,
        actual_sum=actual_sum,
        issues=issues,
    )


def adjust_lane_widths_to_sum(
    lanes: list[dict],
    target_sum: int,
    strategy: Literal["proportional", "last_lane", "first_lane"] = "proportional",
) -> list[dict]:
    """
    Rescale lane widths so they sum to target_sum.

    Args:
        lanes: list of lane dicts
        target_sum: the value the widths should sum to
        strategy:
            'proportional' - distribute the diff proportionally across all lanes
            'last_lane' - absorb the diff into the last lane (preserves all others)
            'first_lane' - absorb the diff into the first lane

    Returns:
        New list of lane dicts (does not mutate input).
    """
    current_sum = sum(lane["width"] for lane in lanes)
    if current_sum == target_sum:
        return [dict(lane) for lane in lanes]

    diff = target_sum - current_sum
    out = [dict(lane) for lane in lanes]

    if strategy == "last_lane":
        out[-1]["width"] += diff
    elif strategy == "first_lane":
        out[0]["width"] += diff
    elif strategy == "proportional":
        # Distribute diff proportionally; round to int; absorb any rounding
        # error into the last lane.
        scale = target_sum / current_sum
        rescaled = [round(lane["width"] * scale) for lane in lanes]
        rounding_error = target_sum - sum(rescaled)
        rescaled[-1] += rounding_error
        for lane, new_w in zip(out, rescaled):
            lane["width"] = new_w

    return out


def describe_lane_layout(
    lanes: list[dict],
    bounding_box: dict,
    titleBar_height: int = 50,
    vertical: bool = False,
) -> str:
    """
    Generate a human-readable summary of a lane configuration.

    Useful for pre-build sanity checking. Prints lane order, widths,
    interior boundaries, and whether widths sum correctly.
    """
    result = validate_lane_widths(lanes, bounding_box, vertical)
    boundaries = compute_lane_boundaries(lanes, titleBar_height, vertical)

    axis_label = "X" if vertical else "Y"
    sum_axis = "boundingBox.w" if vertical else "boundingBox.h"

    lines = [
        f"Swimlane layout summary",
        f"  orientation: {'vertical (lanes side-by-side)' if vertical else 'horizontal (lanes stacked top-to-bottom)'}",
        f"  boundingBox: w={bounding_box['w']}, h={bounding_box['h']}",
        f"  titleBar height: {titleBar_height}",
        f"  lane count: {len(lanes)}",
        f"  width sum check: {result.actual_sum} (lanes) vs {result.expected_sum} ({sum_axis}) — {'OK' if result.ok else 'MISMATCH'}",
        f"",
        f"  Lane interiors (along {axis_label} axis):",
    ]
    for b in boundaries:
        lines.append(
            f"    {b.title!r}: width={b.width}, interior {axis_label}=[{b.interior_min}, {b.interior_max}]"
        )

    if not result.ok:
        lines.append("")
        for issue in result.issues:
            lines.append(f"  ISSUE: {issue}")

    return "\n".join(lines)


if __name__ == "__main__":
    # Quick self-test on the 7-lane functional routing preset
    lanes = [
        {"title": "Entry", "width": 200},
        {"title": "Match", "width": 330},
        {"title": "Enrich", "width": 140},
        {"title": "Decide", "width": 620},
        {"title": "Route / Assign", "width": 270},
        {"title": "Cadence / Notify", "width": 370},
        {"title": "Write", "width": 390},
    ]
    bbox = {"w": 5000, "h": 2370}
    print(describe_lane_layout(lanes, bbox, vertical=False))
