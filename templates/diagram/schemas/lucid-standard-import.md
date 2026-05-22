# Lucid Standard Import — Schema Reference

This is an annotated condensed reference for the Lucid Standard Import JSON format used by `lucid_create_diagram_from_specification`. For the canonical authoritative reference, read the MCP resource `lucid://diagram-specification` from the Lucid MCP at runtime.

## Top-level shape

```json
{
  "version": 1,
  "pages": [
    {
      "id": "page1",
      "title": "Page 1",
      "shapes": [],
      "lines": []
    }
  ]
}
```

## Page properties

- `id` (required): unique page identifier
- `title` (optional): page tab title

## Shape: common properties

- `id` (required): unique identifier string
- `type` (required): shape type from the registry below
- `boundingBox` (required): `{x, y, w, h}` — top-left + dimensions
- `text` (optional): string for the shape's displayed text
- `style` (optional): `{fill, stroke, textColor}`
  - `fill`: `{type: "color", color: "#hexcolor"}`
  - `stroke`: `{color, width, style}` where style is `"solid"`, `"dashed"`, etc.

**Text must not contain emoji.** Emoji render as black boxes.

## Shape types we use for process maps

From the Flowchart Library:

- `terminator` — start/end oval. Use for IN, OUT, START, END nodes.
- `process` — process rectangle. Use for steps, system actions, database writes, warning callouts, sub-process links. (We use the same shape type but different fill colors to convey semantic role.)
- `decision` — diamond. Use for branching decisions. **Minimum 280×140.**

From the Standard Library:

- `text` — text-only label. No fill/stroke. Used for legend titles and labels.
- `rectangle` — basic rectangle. Used for legend swatches.

## Container: swimLanes

```json
{
  "id": "lanes",
  "type": "swimLanes",
  "boundingBox": {"x": 0, "y": 0, "w": 3200, "h": 1130},
  "vertical": false,
  "assistedLayout": false,
  "titleBar": {"height": 50, "verticalText": false},
  "lanes": [
    {"title": "Lane 1", "width": 565, "headerFill": "#C7D2FE", "laneFill": "#EEF2FF"},
    {"title": "Lane 2", "width": 565, "headerFill": "#F5D0FE", "laneFill": "#FDF4FF"}
  ]
}
```

**Critical math:**

- `vertical: false` → lanes are rows stacked top-to-bottom. `width` is each lane's height. **Sum of widths must equal `boundingBox.h`** (titleBar height INCLUDED in the sum).
- `vertical: true` → lanes are columns stacked left-to-right. `width` is each lane's width. **Sum of widths must equal `boundingBox.w`**.

**Lane interior boundaries:**

- First lane interior: `[titleBar.height, lane[0].width]` — the titleBar occupies the leading edge of the first lane.
- Subsequent lane interiors: `[cumulative_lane_widths_so_far, cumulative_lane_widths_so_far + lane[i].width]`

**Every required lane property:** `title`, `width`, `headerFill`, `laneFill`. All four are required.

**assistedLayout:**

- `true` (default if omitted): Lucid auto-arranges nodes. Useful for sparse diagrams.
- `false`: your explicit coordinates are honored. Use for any diagram with 30+ nodes or where lane assignment matters.

## Line properties

```json
{
  "id": "l1",
  "lineType": "elbow",
  "endpoint1": {"type": "shapeEndpoint", "style": "none", "shapeId": "shape1"},
  "endpoint2": {"type": "shapeEndpoint", "style": "arrow", "shapeId": "shape2"},
  "stroke": {"color": "#374151", "width": 2, "style": "solid"},
  "text": [{"text": "label", "position": 0.5, "side": "middle"}]
}
```

- `lineType`: `"straight"`, `"elbow"`, `"curved"`. Default for process maps is `"elbow"`.
- `endpoint1.style` is the decoration AT THE START. For a one-way arrow, use `"none"` here and `"arrow"` on `endpoint2`.
- `text[].position`: a number 0–1 along the line. `.side`: `"top"`, `"middle"`, or `"bottom"`.

## Endpoint types

- `shapeEndpoint` — connects to a shape: `{type, style, shapeId, position?}`
- `positionEndpoint` — connects to an absolute canvas point: `{type, style, position: {x, y}}`
- `lineEndpoint` — connects to another line: `{type, style, lineId, position: number}`

**Position rule:** if you specify `position` on a `shapeEndpoint`, you MUST specify it on the OTHER endpoint too. Partial position specifications fail. Prefer omitting position entirely (smart routing) and only specify when needed to avoid connector-over-text overlap.

## Z-order

Shapes are rendered in array order. Later shapes appear ON TOP. Put background containers earlier in the array than the nodes they contain.

## Size limit

Total payload size: 2 MB maximum. Use concise JSON. Split into multiple maps before approaching this limit.
