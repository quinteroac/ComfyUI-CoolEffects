# Requirement: Text Overlay Effect Node

## Context
ComfyUI-CoolEffects currently supports visual effects (glitch, VHS, pan, zoom, dolly, etc.) but has no way to overlay text on images or videos. Content creators need a dedicated node to add animated text overlays — titles, captions, watermarks — that integrate seamlessly with `CoolVideoGenerator` and display a live WebGL2 preview inside the node widget.

## Goals
- Provide a `CoolTextOverlayEffect` node that outputs `EFFECT_PARAMS` consumable by `CoolVideoGenerator`.
- Allow users to configure text content, appearance (font size, color), and screen position.
- Support at least two animation styles (e.g. fade-in and slide-in) so text enters the frame dynamically.
- Maintain visual consistency with existing effect nodes: live WebGL2 preview in the node widget.

## User Stories

### US-001: Configure text appearance
**As a** content creator, **I want** to type my text and set its font size and color **so that** I can match the overlay to my video's visual style.

**Acceptance Criteria:**
- [ ] Node exposes a `text` STRING input (free text, default `"Hello World"`).
- [ ] Node exposes a `font` COMBO input populated at load time by scanning `assets/fonts/` for `.ttf` files; defaults to the first font found alphabetically.
- [ ] Node exposes a `font_size` INT input (default `48`, min `8`, max `256`).
- [ ] Node exposes `color_r`, `color_g`, `color_b` FLOAT inputs (0.0–1.0, default white `1.0, 1.0, 1.0`).
- [ ] Node exposes an `opacity` FLOAT input (0.0–1.0, default `1.0`).
- [ ] If `assets/fonts/` is empty or missing, node raises a clear `ValueError` at load time.
- [ ] Typecheck / lint passes.

### US-002: Position text on the image
**As a** content creator, **I want** to choose where the text appears on the frame **so that** I can place titles at the top, captions at the bottom, or watermarks in a corner.

**Acceptance Criteria:**
- [ ] Node exposes a `position` COMBO input with options: `top-left`, `top-center`, `top-right`, `center`, `bottom-left`, `bottom-center`, `bottom-right` (default `bottom-center`).
- [ ] Node exposes `offset_x` and `offset_y` FLOAT inputs (−1.0–1.0, default `0.0`) for fine-grained nudging from the anchor point.
- [ ] The chosen position is reflected correctly in the live WebGL2 preview.
- [ ] Typecheck / lint passes.

### US-003: Animate the text
**As a** content creator, **I want** to choose an animation style and control its duration **so that** the text enters the frame in an engaging way rather than appearing abruptly.

**Acceptance Criteria:**
- [ ] Node exposes an `animation` COMBO input with options: `none`, `fade_in`, `fade_in_out`, `slide_up`, `typewriter` (default `fade_in`).
- [ ] Node exposes an `animation_duration` FLOAT input (seconds, default `0.5`, min `0.0`, max `5.0`) controlling the duration of the animation phase.
- [ ] With `none`: text is visible at full opacity for the entire clip.
- [ ] With `fade_in`: text transitions from transparent to the configured opacity over `animation_duration` seconds; stays visible for the remainder of the clip.
- [ ] With `fade_in_out`: text fades in over the first `animation_duration` seconds and fades out over the last `animation_duration` seconds of the clip.
- [ ] With `slide_up`: text enters from below its anchor position, sliding up into place over `animation_duration` seconds.
- [ ] With `typewriter`: characters are revealed one by one from left to right over `animation_duration` seconds; because GLSL cannot iterate over string characters, the typewriter effect is implemented on the Python/Pillow side by rendering a substring of increasing length per frame (this requires per-frame texture regeneration for this animation only).
- [ ] Animations are driven by `u_time` (and clip total duration via `u_duration` uniform) so they work correctly across all frame rates.
- [ ] Typecheck / lint passes.

### US-004: Output EFFECT_PARAMS compatible with CoolVideoGenerator
**As a** content creator, **I want** the node to produce an `EFFECT_PARAMS` output **so that** I can chain it with other effects inside `CoolVideoGenerator` and render an animated video with text.

**Acceptance Criteria:**
- [ ] Node `RETURN_TYPES = ("EFFECT_PARAMS",)`.
- [ ] `execute()` calls `build_effect_params("text_overlay", {...})` with all configured parameters.
- [ ] Node is registered in `NODE_CLASS_MAPPINGS` as `"CoolTextOverlayEffect"` and in `NODE_DISPLAY_NAME_MAPPINGS`.
- [ ] A `CoolVideoGenerator` workflow with `CoolTextOverlayEffect` connected renders a video with visible animated text.
- [ ] Typecheck / lint passes.

### US-005: Live WebGL2 preview in the node widget
**As a** content creator, **I want** to see the text overlay rendered in real time inside the node **so that** I can adjust parameters without running the full workflow.

**Acceptance Criteria:**
- [ ] A JS extension `web/text_overlay_effect.js` is created, following the pattern of `web/zoom_in_effect.js` / `web/effect_node_widget.js`.
- [ ] The WebGL2 canvas widget renders a sample image with the configured text overlay and animation applied.
- [ ] Changing any node input (text, font size, color, position, animation) updates the preview in real time.
- [ ] Visually verified in browser: text appears at the correct position with the selected animation playing on the canvas.
- [ ] Typecheck / lint passes.

## Functional Requirements
- FR-1: A new Python node file `nodes/text_overlay_effect.py` implementing `CoolTextOverlayEffect`. At class load time it scans `assets/fonts/` (relative to the package root) for `*.ttf` files and exposes them as a COMBO input; the selected font name is passed as a parameter so `video_generator.py` can resolve the full path via `assets/fonts/<font_name>` when rendering.
- FR-2: A new GLSL fragment shader `shaders/glsl/text_overlay.frag` accepting `u_image`, `u_time`, `u_resolution`, and all text-related uniforms; composites the text layer over the base image with the selected animation.
- FR-3: Because GLSL cannot render arbitrary TrueType text natively, the text is pre-rendered to a texture via Pillow and uploaded to the shader as a second sampler uniform `u_text_texture`. For all animations except `typewriter`, the texture is rendered **once** before the frame loop and reused. For `typewriter`, the texture is re-rendered **per frame** with an increasing substring length. `CoolVideoGenerator` must be extended to handle both strategies for the `text_overlay` effect.
- FR-4b: The shader receives a `u_duration` FLOAT uniform (total clip duration in seconds) so animations like `fade_in_out` can compute the fade-out start time.
- FR-4: The JS extension must load `text_overlay.frag` via `loadShader("text_overlay")` and use `mount_effect_node_widget` (from `web/effect_node_widget.js`) to mount the live preview canvas.
- FR-5: Node registered in `__init__.py` using `importlib.util.spec_from_file_location`, following the same pattern as all existing effect nodes.
- FR-6: `NODE_CLASS_MAPPINGS["CoolTextOverlayEffect"]` and `NODE_DISPLAY_NAME_MAPPINGS["CoolTextOverlayEffect"] = "Cool Text Overlay Effect"`.

## Non-Goals (Out of Scope)
- Multiple text layers in a single node (one text string per node instance).
- Custom font file upload via the UI (fonts must be placed manually in `assets/fonts/`).
- Text outline / shadow / background box styling.
- Exit animations (text fading/sliding out) — entrance only for MVP.
- Slide directions other than `slide_up` (left, right, down) — can be added in future iterations.
- Multi-line auto-wrap (newlines via `\n` in the text string are acceptable but no automatic word wrap).
- Audio-reactive text animations.

## Open Questions
_All questions resolved._

**Font:** One or more `.ttf` files with OFL-compatible licenses (e.g. Roboto, Inter) are placed in `assets/fonts/`. The node scans this directory at load time and exposes all found fonts as a COMBO input — adding more `.ttf` files to the folder automatically expands the options without code changes.

**Text rendering strategy:** Pillow renders the text texture **once** before the frame loop inside `video_generator.py` and the resulting texture is reused for the entire clip. This is efficient and sufficient for MVP since text content does not change between frames.
