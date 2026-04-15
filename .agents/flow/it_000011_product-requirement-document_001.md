# CoolTextOverlay — Backend & Node Structure

## Context

ComfyUI-CoolEffects produces videos by chaining GLSL effects on images. Currently there is no way to
embed styled text into the video output. This PRD covers the Python node and Pillow-based rendering
pipeline that bakes rich inline text (multiple fragments, each with its own font/size/color/weight)
into every frame of a VIDEO tensor, producing a new VIDEO with the text permanently composited.

## Goals

- Introduce a `CoolTextOverlay` Python node that accepts a VIDEO and a rich text configuration and
  returns a VIDEO with the text burned into every frame.
- Support multiple styled text fragments per overlay (rich inline: each fragment has independent
  font family, size, color, and weight).
- Allow precise placement via normalised X/Y coordinates and horizontal alignment (left / center /
  right).
- Keep Pillow as the sole new backend dependency (already present in virtually every ComfyUI
  environment; add to `requirements.txt` if absent).
- Register the node in `__init__.py` following the existing `importlib` pattern.

## User Stories

### US-001: Single-style text overlay on video
**As a** ComfyUI user, **I want** to connect a VIDEO to `CoolTextOverlay` and specify a text string
with a font, size, and color **so that** every frame of the output VIDEO has that text rendered at
the position I specified.

**Acceptance Criteria:**
- [ ] The node accepts a VIDEO input and returns a VIDEO output of identical resolution, fps, and
      frame count.
- [ ] A widget `text` (STRING) sets the full overlay text when no fragments are provided.
- [ ] Widgets `font_family` (STRING, default `"arial"`), `font_size` (INT, 24–256, default 48),
      `color` (STRING hex, default `"#ffffff"`), `font_weight` (COMBO `["normal","bold"]`, default
      `"normal"`) control the default style.
- [ ] Widgets `pos_x` (FLOAT 0.0–1.0, default 0.5) and `pos_y` (FLOAT 0.0–1.0, default 0.1)
      define the anchor position as a fraction of frame width/height.
- [ ] Widget `align` (COMBO `["left","center","right"]`, default `"center"`) controls text
      alignment relative to `pos_x`.
- [ ] Widget `opacity` (FLOAT 0.0–1.0, default 1.0) blends the text into the frame.
- [ ] Running the node with a 3-frame VIDEO produces an output VIDEO where all 3 frames contain the
      rendered text at the expected position.

### US-002: Rich inline multi-fragment text overlay
**As a** ComfyUI user, **I want** to supply a JSON array of text fragments (each with its own
`text`, `font_family`, `font_size`, `color`, `font_weight`) **so that** I can render composite
labels (e.g., white normal word followed by a yellow bold word) burned into the video.

**Acceptance Criteria:**
- [ ] The node accepts an optional `fragments` input of type STRING containing a JSON array; when
      provided it takes precedence over the `text` widget.
- [ ] Each fragment object must support keys: `text` (required), `font_family` (optional, falls
      back to the node-level default), `font_size` (optional, falls back), `color` (optional, falls
      back), `font_weight` (optional, falls back).
- [ ] Fragments are laid out left-to-right on a single baseline; `pos_x`/`pos_y`/`align` apply to
      the whole composed line.
- [ ] Passing an invalid JSON string raises a `ValueError` with a human-readable message.
- [ ] A VIDEO rendered with two fragments of different colors shows each fragment in its respective
      color in the output frames.

### US-003: Pillow font resolution
**As a** developer, **I want** the node to resolve font files robustly **so that** it does not crash
on systems where a requested font family is not installed.

**Acceptance Criteria:**
- [ ] The node attempts to load the font via `ImageFont.truetype`; on `OSError` it falls back to
      `ImageFont.load_default()` and logs a warning.
- [ ] The fallback produces visible text in the output (no silent blank frames).
- [ ] Font resolution is attempted once per unique `(font_family, font_size, font_weight)` tuple
      per `execute()` call (no repeated I/O per frame).

---

## Functional Requirements

- FR-1: Node class `CoolTextOverlay` lives in `nodes/text_overlay_effect.py`.
- FR-2: `INPUT_TYPES` returns `{"required": {"video": ("VIDEO",)}, "optional": {"fragments": ("STRING", {"default": "[]"})}}` plus all style/position widgets.
- FR-3: `RETURN_TYPES = ("VIDEO",)`, `RETURN_NAMES = ("video",)`, `FUNCTION = "execute"`.
- FR-4: `execute()` iterates over every frame tensor in the VIDEO payload, converts each to a
        Pillow `Image`, draws text (single-style or segmented fragments) using `ImageDraw`, converts
        back to tensor, and reassembles the VIDEO payload preserving fps and audio metadata.
- FR-5: For rich inline fragments, each fragment is drawn sequentially; the X cursor advances by
        the measured pixel width of the previous fragment (`ImageDraw.textlength` or
        `ImageFont.getbbox`).
- FR-6: Opacity blending uses `Image.paste` with an RGBA mask derived from `opacity`.
- FR-7: GL resource cleanup pattern does NOT apply here (no ModernGL); Pillow images are created
        and discarded per frame inside the loop.
- FR-8: Node is registered in `__init__.py` under the key `"CoolTextOverlay"` with display name
        `"Cool Text Overlay"` following the existing `importlib.util.spec_from_file_location`
        pattern.
- FR-9: `requirements.txt` gains a `Pillow` entry if not already present.

## Non-Goals

- Frontend canvas preview widget (covered in PRD 002).
- Animation of text position or opacity over time (future iteration).
- Vertical text layout or multi-line wrapping (future iteration).
- Text shadow, stroke, or outline effects (future iteration).
- Any GLSL shader involvement for text rendering.

## Open Questions

- The VIDEO payload structure (`comfy_api.latest` format) should be verified at implementation
  time — confirm how to extract frame tensors and reassemble with preserved audio/fps metadata.
