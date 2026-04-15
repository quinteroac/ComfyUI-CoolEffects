# CoolTextOverlay — Frontend & pretext Preview

## Context

PRD 001 introduces the `CoolTextOverlay` Python node that bakes rich inline text into video frames
via Pillow. This PRD covers the complementary ComfyUI JS extension: a canvas widget that renders a
pixel-perfect live preview of the text overlay using the **pretext** library
(https://github.com/chenglou/pretext) for accurate text measurement and layout, matching what the
backend will produce. It also covers the fragment configuration UI (add/remove/edit styled
fragments in the node widget area).

## Goals

- Provide a live canvas preview inside the `CoolTextOverlay` node that shows the text composited
  over the first frame of the connected VIDEO, updating in real time as the user edits parameters.
- Use pretext `prepareRichInline()` + `materializeRichInlineLineRange()` to measure and position
  each fragment so that the frontend layout matches the Pillow backend output as closely as
  possible.
- Deliver a usable fragment editor UI: add fragment, remove fragment, and per-fragment controls
  (text, font family, font size, color, weight).
- Load pretext as a plain ES module (no bundler) consistent with the project's no-build-step
  constraint.

## User Stories

### US-001: Live canvas preview of text overlay
**As a** ComfyUI user, **I want** the `CoolTextOverlay` node to show a canvas preview with the text
rendered over the video frame **so that** I can adjust position, size, and style without running
the full workflow.

**Acceptance Criteria:**
- [ ] When a VIDEO is connected to the node, the canvas widget displays the first frame as a
      background image.
- [ ] The text overlay (single-style or rich inline fragments) is rendered on top of the frame
      using Canvas 2D API, with position and alignment driven by `pos_x`, `pos_y`, and `align`
      widget values.
- [ ] Changing any widget value (text, font_size, color, pos_x, pos_y, align, opacity) causes the
      canvas to re-render within one animation frame (no noticeable lag).
- [ ] The canvas dimensions match the connected VIDEO frame's aspect ratio; it scales to fit the
      node widget area without distorting the image.

### US-002: pretext integration for accurate rich inline layout
**As a** ComfyUI developer, **I want** the frontend to use pretext's `prepareRichInline()` API to
measure fragment widths **so that** the canvas preview matches the Pillow backend output in
fragment positioning and line width.

**Acceptance Criteria:**
- [ ] pretext is loaded via a dynamic `import()` from a CDN URL or a local vendor file bundled
      under `web/vendor/pretext.js`; no bundler or build step is required.
- [ ] For each set of fragments, `prepareRichInline()` is called with the fragment specs and the
      canvas font shorthand (e.g., `"bold 48px Arial"`); the returned measurement is used to
      compute the total line width and per-fragment X offsets.
- [ ] When `align` is `"center"`, the composite line is centered at `pos_x * canvas.width`;
      `"left"` anchors the left edge; `"right"` anchors the right edge — matching the backend FR-5
      logic.
- [ ] A visual comparison between the canvas preview and the node's output frame shows fragment
      boundaries within ±2 px for a Latin-script test string at 48 px.

### US-003: Fragment editor UI in node widget
**As a** ComfyUI user, **I want** to add, remove, and edit styled text fragments directly in the
node **so that** I can build composite labels without manually writing JSON.

**Acceptance Criteria:**
- [ ] The node widget area shows a list of fragment rows; each row has inputs for `text` (text
      field), `font_family` (text field), `font_size` (number input), `color` (color picker or hex
      input), and `font_weight` (select: normal / bold).
- [ ] An "Add fragment" button appends a new row with default values inherited from the node-level
      widgets.
- [ ] A "Remove" button on each row deletes that fragment; at least one fragment must remain (the
      button is disabled when only one row is present).
- [ ] Editing any fragment field immediately serialises the fragment list to JSON and writes it
      into the hidden `fragments` STRING widget so ComfyUI sends the updated value on the next
      queue execution.
- [ ] The canvas preview updates to reflect fragment edits in real time (covered by US-001 AC).

### US-004: Graceful degradation when pretext unavailable
**As a** ComfyUI user on a network-restricted environment, **I want** the canvas preview to still
render text **so that** the node is usable even if pretext fails to load.

**Acceptance Criteria:**
- [ ] If the pretext `import()` rejects (network error, missing vendor file), the extension catches
      the error, logs a console warning, and falls back to `ctx.measureText()` for width
      calculation.
- [ ] The fallback path renders the same canvas layout logic (pos_x, pos_y, align, opacity) using
      native Canvas 2D measurement; no JS exception propagates to ComfyUI's error handler.

---

## Functional Requirements

- FR-1: Extension file is `web/text_overlay_effect.js`; registered in `__init__.py` via
        `WEB_DIRECTORY` (already set up for the package).
- FR-2: The extension registers on `"CoolTextOverlay"` node type using ComfyUI's
        `app.registerExtension` → `nodeCreated` callback, consistent with other per-effect
        extensions.
- FR-3: A canvas element is appended to the node as a DOM widget via `node.addDOMWidget`.
- FR-4: pretext is loaded once at module init via `import()` and the resolved module cached in a
        module-level variable; subsequent preview renders use the cache.
- FR-5: Fragment editor rows are rendered as a `<div>` DOM widget below the canvas; changes to
        inputs trigger `serialize_fragments()` → write to the `fragments` widget value.
- FR-6: The canvas re-render function reads `pos_x`, `pos_y`, `align`, `opacity` from
        `node.widgets` by name and applies them when drawing text.
- FR-7: If no VIDEO is connected, the canvas shows a dark placeholder with a centred "No video"
        label so the widget area is not blank.
- FR-8: The extension follows the same ES module style as `web/effect_node_widget.js` (no
        `import` statements at top-level that require a bundler — use dynamic `import()` for
        pretext only).

## Non-Goals

- Modifying `web/effect_node_widget.js` or the shared widget factory (this node has its own
  widget with different requirements).
- Animating the canvas preview over time (scrubbing through video frames).
- Supporting multi-line text wrapping in the preview (single-line layout only, matching FR in
  PRD 001).
- Server-side rendering via pretext (noted as "coming soon" in pretext docs; not relied upon).

## Open Questions

- None. pretext `@chenglou/pretext@0.0.5` ships native ES module builds on jsDelivr:
  - Layout: `https://cdn.jsdelivr.net/npm/@chenglou/pretext@0.0.5/dist/layout.js`
  - Rich inline: `https://cdn.jsdelivr.net/npm/@chenglou/pretext@0.0.5/dist/rich-inline.js`
  Load via `import()` dynamic import — no bundler required. For offline environments, vendor a
  copy under `web/vendor/pretext-rich-inline.js` and fall back to it if the CDN import fails.
