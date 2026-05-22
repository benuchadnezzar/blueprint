"""
High-level builders for assembling a Lucid Standard Import payload.

Goal: let the caller construct a process map by describing the lanes, nodes,
and connections in semantic terms, and have this module produce a fully
validated payload ready to send to lucid_create_diagram_from_specification.

This is the highest-leverage piece of the template: it eliminates the
boilerplate that's most error-prone (lane spec formatting, shape style
defaults, endpoint construction).
"""

import json
import os
from pathlib import Path
from typing import Literal

# Re-export validator and audit so callers only need one import
from validators import ValidationReport, validate_payload  # noqa: F401
from placement_audit import NodePlacement, audit  # noqa: F401

# Resolve template directory. Priority:
#   1. PROCESS_MAPS_TEMPLATE_DIR environment variable
#   2. <plugin_root>/templates/process-maps/ (computed from this file's location:
#      scripts/process-maps/builder.py -> ../../templates/process-maps/)
#   3. ./templates/process-maps/ relative to the current working directory

def _resolve_template_dir() -> Path:
    if env := os.environ.get("PROCESS_MAPS_TEMPLATE_DIR"):
        p = Path(env)
        if (p / "presets" / "lane-presets.json").exists():
            return p
    # scripts/process-maps/builder.py -> plugin_root = parent.parent.parent
    plugin_root = Path(__file__).parent.parent.parent
    p = plugin_root / "templates" / "process-maps"
    if (p / "presets" / "lane-presets.json").exists():
        return p
    p = Path.cwd() / "templates" / "process-maps"
    if (p / "presets" / "lane-presets.json").exists():
        return p
    raise FileNotFoundError(
        "Could not locate the process-maps template library. Expected to find "
        "presets/lane-presets.json under one of: "
        "$PROCESS_MAPS_TEMPLATE_DIR, "
        f"{plugin_root / 'templates' / 'process-maps'}, or "
        f"{Path.cwd() / 'templates' / 'process-maps'}."
    )

_TEMPLATE_DIR = _resolve_template_dir()
_COMPONENTS_FILE = _TEMPLATE_DIR / "components" / "node-components.json"
_PRESETS_FILE = _TEMPLATE_DIR / "presets" / "lane-presets.json"
_COLORS_FILE = _TEMPLATE_DIR / "palettes" / "colors.json"

def _load(path: Path) -> dict:
    return json.loads(path.read_text())

NodeKind = Literal[
    "terminator_start_end",
    "terminator_success_end",
    "process",
    "system_action",
    "decision",
    "database_write",
    "out_of_scope",
    "warning_callout",
    "sub_process_link",
]

ConnectorKind = Literal[
    "primary_flow",
    "cross_system_handoff",
    "bug_risk_link",
    "auto_convert_implicit",
]

class DiagramBuilder:
    """
    Build a Lucid Standard Import payload step by step.

    Usage:
        builder = DiagramBuilder()
        builder.set_swimlanes(preset_name="horizontal_5_lane_system_end_to_end")
        builder.add_node("nl_in", "terminator_start_end", lane="Lane 1",
                         x=100, y=100, text="IN: New Lead")
        builder.add_node("nl_match", "process", lane="Lane 1",
                         x=350, y=100, text="Match Contact")
        builder.connect("nl_in", "nl_match", kind="primary_flow")
        report = builder.validate()
        if report.ok:
            payload = builder.build()
    """

    def __init__(self) -> None:
        self._components = _load(_COMPONENTS_FILE)["components"]
        self._connector_templates = _load(_COMPONENTS_FILE)["connector_templates"]
        self._presets = _load(_PRESETS_FILE)["presets"]

        self._swimlanes: dict | None = None
        self._lane_assignments: dict[str, str] = {}  # node_id -> lane title
        self._shapes: list[dict] = []
        self._lines: list[dict] = []
        self._line_counter = 0

    def set_swimlanes(
        self,
        preset_name: str | None = None,
        lanes: list[dict] | None = None,
        bounding_box: dict | None = None,
        vertical: bool = False,
        title_bar_height: int = 50,
        assisted_layout: bool = False,
    ) -> None:
        """
        Configure the swimLanes container.

        Either pass `preset_name` to use a preset from presets/lane-presets.json,
        or pass `lanes` + `bounding_box` directly.
        """
        if preset_name:
            if preset_name not in self._presets:
                raise ValueError(
                    f"Unknown preset {preset_name!r}. Available: {list(self._presets)}"
                )
            preset = self._presets[preset_name]
            lanes = [
                {"title": l["title"], "width": l["width"]}
                for l in preset["lanes"]
            ]
            bounding_box = dict(preset["boundingBox"])
            vertical = preset.get("vertical", False)
            title_bar_height = preset.get("titleBar_height", 50)

        if not lanes or not bounding_box:
            raise ValueError(
                "set_swimlanes requires either a preset_name or both lanes and bounding_box."
            )

        # Attach default headerFill/laneFill if missing (use functional palette by index)
        colors = _load(_COLORS_FILE)["lane_headers_functional"]
        # Filter out documentation keys like $comment, $note
        color_keys = [k for k in colors.keys() if not k.startswith("$")]
        for i, lane in enumerate(lanes):
            if "headerFill" not in lane or "laneFill" not in lane:
                ckey = color_keys[i % len(color_keys)]
                lane.setdefault("headerFill", colors[ckey]["header"])
                lane.setdefault("laneFill", colors[ckey]["lane_fill"])

        self._swimlanes = {
            "id": "lanes",
            "type": "swimLanes",
            "boundingBox": {"x": 0, "y": 0, **bounding_box},
            "vertical": vertical,
            "assistedLayout": assisted_layout,
            "titleBar": {"height": title_bar_height, "verticalText": False},
            "lanes": lanes,
        }

    def add_node(
        self,
        node_id: str,
        kind: NodeKind,
        lane: str,
        x: int,
        y: int,
        text: str,
        width: int | None = None,
        height: int | None = None,
    ) -> None:
        """Add a node of the given semantic kind to a named lane."""
        if kind not in self._components:
            raise ValueError(
                f"Unknown node kind {kind!r}. Available: {list(self._components)}"
            )
        template = self._components[kind]["template"]
        shape = json.loads(json.dumps(template))  # deep copy
        shape["id"] = node_id
        shape["text"] = text
        shape["boundingBox"]["x"] = x
        shape["boundingBox"]["y"] = y
        if width is not None:
            shape["boundingBox"]["w"] = width
        if height is not None:
            shape["boundingBox"]["h"] = height
        self._shapes.append(shape)
        self._lane_assignments[node_id] = lane

    def connect(
        self,
        source_id: str,
        target_id: str,
        kind: ConnectorKind = "primary_flow",
        label: str | None = None,
    ) -> str:
        """Add a connector between two existing nodes. Returns the line id."""
        if kind not in self._connector_templates:
            raise ValueError(
                f"Unknown connector kind {kind!r}. Available: {list(self._connector_templates)}"
            )

        tmpl_key = "with_label_template" if label and "with_label_template" in self._connector_templates[kind] else "template"
        template = self._connector_templates[kind][tmpl_key]
        line = json.loads(json.dumps(template))  # deep copy

        self._line_counter += 1
        line_id = f"l{self._line_counter}"
        line["id"] = line_id
        line["endpoint1"]["shapeId"] = source_id
        line["endpoint2"]["shapeId"] = target_id

        if label and "text" in line:
            line["text"][0]["text"] = label
        elif label:
            line["text"] = [{"text": label, "position": 0.5, "side": "middle"}]

        self._lines.append(line)
        return line_id

    def add_warning(self, callout_id: str, near_node_id: str, lane: str,
                    x: int, y: int, text: str) -> None:
        """Convenience: add a warning_callout AND link it with a bug_risk_link."""
        if not text.startswith(("WARNING:", "BUG:")):
            text = "WARNING: " + text
        self.add_node(callout_id, "warning_callout", lane, x, y, text)
        self.connect(near_node_id, callout_id, kind="bug_risk_link")

    def run_audit(self) -> tuple[bool, str]:
        """Run the pre-build placement audit and return (ok, markdown_table)."""
        if not self._swimlanes:
            raise RuntimeError("set_swimlanes() must be called before run_audit().")
        placements = []
        for shape in self._shapes:
            sid = shape["id"]
            lane = self._lane_assignments.get(sid)
            if not lane:
                continue
            bb = shape["boundingBox"]
            placements.append(
                NodePlacement(
                    node_id=sid,
                    target_lane=lane,
                    x=bb["x"], y=bb["y"], width=bb["w"], height=bb["h"],
                )
            )
        return audit(
            placements,
            self._swimlanes["lanes"],
            titleBar_height=self._swimlanes["titleBar"]["height"],
            vertical=self._swimlanes["vertical"],
        )

    def validate(self) -> ValidationReport:
        """Run pre-flight payload validation."""
        return validate_payload(self.build())

    def build(self) -> dict:
        """Return the assembled Lucid Standard Import payload."""
        if not self._swimlanes:
            raise RuntimeError("set_swimlanes() must be called before build().")
        page_shapes = [self._swimlanes] + self._shapes
        return {
            "version": 1,
            "pages": [
                {
                    "id": "p1",
                    "title": "Process Map",
                    "shapes": page_shapes,
                    "lines": self._lines,
                }
            ],
        }


if __name__ == "__main__":
    # Self-test: build a minimal 2-lane map
    b = DiagramBuilder()
    b.set_swimlanes(preset_name="horizontal_2_lane_system_handoff")
    b.add_node("in_node", "terminator_start_end", lane="System A",
               x=100, y=200, text="IN: Webhook received")
    b.add_node("proc1", "process", lane="System A",
               x=400, y=200, text="Validate payload")
    b.add_node("write1", "database_write", lane="System B",
               x=700, y=750, text="Insert record")
    b.connect("in_node", "proc1")
    b.connect("proc1", "write1", label="POST /api/insert")

    ok, table = b.run_audit()
    print("PLACEMENT AUDIT:")
    print(table)
    print(f"\nAll fit: {ok}\n")

    report = b.validate()
    print("PRE-FLIGHT VALIDATION:")
    print(report.to_markdown())
