"""
Pre-flight validator for Lucid Standard Import payloads.

Catches the common schema violations and convention violations that produce
either API errors or unreadable diagrams:

- Lane width sum mismatch (the #1 cause of API rejection)
- Decision shapes smaller than 280x140 (causes text rotation)
- Connector endpoints with partial position specification
- Duplicate shape/line IDs
- Connector references to non-existent shape IDs
- Text containing emoji (renders as black boxes)
- Total payload size approaching 2MB
- Lane header colors that are saturated/dark (fail readability)
"""

import json
import re
from dataclasses import dataclass, field

from lane_math import validate_lane_widths


# Sanctioned light lane header fills (from palettes/colors.json). Anything not
# in this set triggers a soft warning, not a hard fail.
LIGHT_LANE_FILLS = {
    "#FED7AA", "#FECACA", "#C7D2FE", "#BFDBFE", "#F5D0FE",
    "#A7F3D0", "#FBCFE8", "#FDE68A",
}


@dataclass
class ValidationReport:
    """Outcome of validating a payload."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_markdown(self) -> str:
        if self.ok and not self.warnings:
            return "Pre-flight validation: **OK** (no issues found)."
        lines = [f"Pre-flight validation: **{'OK' if self.ok else 'FAILED'}**"]
        if self.errors:
            lines.append("")
            lines.append("**Errors (block the build):**")
            for e in self.errors:
                lines.append(f"- {e}")
        if self.warnings:
            lines.append("")
            lines.append("**Warnings (review but non-blocking):**")
            for w in self.warnings:
                lines.append(f"- {w}")
        return "\n".join(lines)


_EMOJI_PATTERN = re.compile(
    "[\U0001F000-\U0001FFFF\U00002600-\U000027BF\U0001F300-\U0001F5FF]"
)


def _has_emoji(text: str) -> bool:
    return bool(_EMOJI_PATTERN.search(text))


def validate_payload(payload: dict, max_bytes: int = 2_000_000) -> ValidationReport:
    """
    Validate a complete lucid_create_diagram_from_specification payload.

    Args:
        payload: the dict that will become standard_import_json
        max_bytes: payload size limit (Lucid API: 2 MB)

    Returns:
        ValidationReport with errors and warnings.
    """
    r = ValidationReport()

    # --- top-level shape ---
    if "version" not in payload:
        r.warnings.append("Missing 'version' at top level. Recommended value: 1.")
    if "pages" not in payload or not payload.get("pages"):
        r.errors.append("Payload must have a 'pages' array with at least one page.")
        return r

    # --- size ---
    serialized = json.dumps(payload, separators=(",", ":"))
    size = len(serialized.encode("utf-8"))
    if size > max_bytes:
        r.errors.append(
            f"Payload size {size} bytes exceeds Lucid's {max_bytes} byte limit. "
            f"Split the diagram into multiple maps with sub-process links."
        )
    elif size > max_bytes * 0.8:
        r.warnings.append(
            f"Payload size {size} bytes is approaching the {max_bytes} byte limit "
            f"({100 * size / max_bytes:.0f}%). Consider splitting."
        )

    # --- per-page checks ---
    for page_idx, page in enumerate(payload["pages"]):
        page_label = f"page[{page_idx}]"
        if "id" not in page:
            r.errors.append(f"{page_label} is missing required 'id'.")

        shapes = page.get("shapes", []) or []
        lines = page.get("lines", []) or []

        # --- duplicate IDs across shapes and lines ---
        seen_ids = set()
        for s in shapes:
            sid = s.get("id")
            if not sid:
                r.errors.append(f"{page_label}: a shape is missing required 'id'.")
                continue
            if sid in seen_ids:
                r.errors.append(f"{page_label}: duplicate id {sid!r}.")
            seen_ids.add(sid)
        line_ids = set()
        for ln in lines:
            lid = ln.get("id")
            if not lid:
                r.errors.append(f"{page_label}: a line is missing required 'id'.")
                continue
            if lid in seen_ids or lid in line_ids:
                r.errors.append(f"{page_label}: duplicate id {lid!r}.")
            line_ids.add(lid)

        shape_ids = {s["id"] for s in shapes if "id" in s}

        # --- swimLanes-specific checks ---
        for s in shapes:
            if s.get("type") != "swimLanes":
                continue
            sid = s.get("id", "(no id)")
            bbox = s.get("boundingBox", {})
            lanes = s.get("lanes", [])
            vertical = s.get("vertical", False)

            if not lanes:
                r.errors.append(f"{page_label}: swimLanes {sid} has no lanes.")
                continue

            for li, lane in enumerate(lanes):
                for required in ("title", "width", "headerFill", "laneFill"):
                    if required not in lane:
                        r.errors.append(
                            f"{page_label}: swimLanes {sid} lane[{li}] missing required {required!r}."
                        )
                if lane.get("headerFill") and lane["headerFill"].upper() not in LIGHT_LANE_FILLS:
                    r.warnings.append(
                        f"{page_label}: swimLanes {sid} lane[{li}] headerFill "
                        f"{lane['headerFill']!r} is not in the sanctioned light-fill set. "
                        f"Check readability with dark text."
                    )

            sum_result = validate_lane_widths(lanes, bbox, vertical=vertical)
            if not sum_result.ok:
                for issue in sum_result.issues:
                    r.errors.append(f"{page_label}: swimLanes {sid}: {issue}")

            if "titleBar" not in s:
                r.warnings.append(
                    f"{page_label}: swimLanes {sid} has no titleBar. Default would be applied."
                )

        # --- decision shape size ---
        for s in shapes:
            if s.get("type") != "decision":
                continue
            bb = s.get("boundingBox", {})
            w = bb.get("w", 0)
            h = bb.get("h", 0)
            if w < 280 or h < 140:
                r.warnings.append(
                    f"{page_label}: decision shape {s.get('id', '(no id)')!r} is "
                    f"{w}x{h}; minimum recommended 280x140 to keep text horizontal."
                )

        # --- emoji in text ---
        for s in shapes:
            t = s.get("text", "")
            if isinstance(t, str) and _has_emoji(t):
                r.errors.append(
                    f"{page_label}: shape {s.get('id', '(no id)')!r} text contains emoji "
                    f"which render as black boxes. Remove emoji."
                )

        # --- line endpoint checks ---
        for ln in lines:
            lid = ln.get("id", "(no id)")
            for ep_name in ("endpoint1", "endpoint2"):
                ep = ln.get(ep_name)
                if not ep:
                    r.errors.append(f"{page_label}: line {lid} missing {ep_name}.")
                    continue
                if "type" not in ep or "style" not in ep:
                    r.errors.append(
                        f"{page_label}: line {lid} {ep_name} missing 'type' or 'style'."
                    )
                if ep.get("type") == "shapeEndpoint":
                    if "shapeId" not in ep:
                        r.errors.append(
                            f"{page_label}: line {lid} {ep_name} is shapeEndpoint but missing 'shapeId'."
                        )
                    elif ep["shapeId"] not in shape_ids:
                        r.errors.append(
                            f"{page_label}: line {lid} {ep_name} references unknown shapeId "
                            f"{ep['shapeId']!r}."
                        )

            # "position must be specified on BOTH endpoints or NEITHER"
            has_pos_1 = "position" in (ln.get("endpoint1") or {})
            has_pos_2 = "position" in (ln.get("endpoint2") or {})
            if has_pos_1 != has_pos_2:
                r.errors.append(
                    f"{page_label}: line {lid} specifies position on one endpoint but not "
                    f"the other. Lucid requires position on BOTH endpoints or NEITHER."
                )

    return r


if __name__ == "__main__":
    # Self-test: build a deliberately broken payload and run it
    payload = {
        "version": 1,
        "pages": [
            {
                "id": "p1",
                "title": "Test",
                "shapes": [
                    {
                        "id": "lanes",
                        "type": "swimLanes",
                        "boundingBox": {"x": 0, "y": 0, "w": 1000, "h": 800},
                        "vertical": False,
                        "titleBar": {"height": 50, "verticalText": False},
                        "lanes": [
                            {"title": "A", "width": 400, "headerFill": "#C7D2FE", "laneFill": "#EEF2FF"},
                            {"title": "B", "width": 350, "headerFill": "#4338CA", "laneFill": "#EEF2FF"},
                        ],
                    },
                    {
                        "id": "dec",
                        "type": "decision",
                        "boundingBox": {"x": 100, "y": 100, "w": 200, "h": 100},
                        "text": "Too small?",
                    },
                ],
                "lines": [
                    {
                        "id": "l1",
                        "lineType": "elbow",
                        "endpoint1": {"type": "shapeEndpoint", "style": "none", "shapeId": "dec",
                                      "position": {"x": 1, "y": 0.5}},
                        "endpoint2": {"type": "shapeEndpoint", "style": "arrow", "shapeId": "ghost"},
                    },
                ],
            }
        ],
    }

    report = validate_payload(payload)
    print(report.to_markdown())
