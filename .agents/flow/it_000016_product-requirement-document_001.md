# Requirement: Color Grading Effects Set

## Context
ComfyUI-CoolEffects currently provides motion and distortion effects (glitch, VHS, zoom pulse, pan, fisheye, pincushion, etc.) but lacks color grading tools. Artists building image/video workflows need a set of color correction and grading nodes — Brightness/Contrast, HSL, Color Temperature, Curves, Color Balance, Sepia/B&W/Duotone, and LUT application — each following the same EFFECT_PARAMS pattern and compatible with the Video Generator pipeline.

## Goals
- Deliver seven color grading effect nodes using the established GLSL + ModernGL + WebGL2 preview pattern.
- Each node integrates seamlessly with `CoolVideoGenerator` for frame-by-frame video rendering.
- Neutral/default parameters must produce no perceptible change to the source image (safe defaults).

## User Stories

### US-001: Brightness / Contrast Effect Node
**As a** ComfyUI artist, **I want** a node that adjusts image brightness and contrast **so that** I can lighten, darken, or increase/decrease tonal range in my workflow.

**Acceptance Criteria:**
- [ ] Node `CoolBrightnessContrastEffect` appears in ComfyUI node browser.
- [ ] Inputs: `brightness` FLOAT [-1.0, 1.0, default 0.0], `contrast` FLOAT [-1.0, 1.0, default 0.0].
- [ ] Output: `EFFECT_PARAMS`.
- [ ] Live WebGL2 preview widget reflects parameter changes in real time.
- [ ] Default params (0, 0) produce no visible change to the source image.
- [ ] Effect renders correctly through `CoolVideoGenerator` frame-by-frame.
- [ ] Typecheck / lint passes.
- [ ] Visually verified in browser.

### US-002: HSL (Hue / Saturation / Lightness) Effect Node
**As a** ComfyUI artist, **I want** a node that shifts hue, saturation, and lightness **so that** I can remap colors or desaturate/saturate images.

**Acceptance Criteria:**
- [ ] Node `CoolHSLEffect` appears in ComfyUI node browser.
- [ ] Inputs: `hue_shift` FLOAT [-180.0, 180.0, default 0.0], `saturation` FLOAT [-1.0, 1.0, default 0.0], `lightness` FLOAT [-1.0, 1.0, default 0.0].
- [ ] Output: `EFFECT_PARAMS`.
- [ ] Live WebGL2 preview widget reflects parameter changes in real time.
- [ ] Default params (0, 0, 0) produce no visible change to the source image.
- [ ] Effect renders correctly through `CoolVideoGenerator` frame-by-frame.
- [ ] Typecheck / lint passes.
- [ ] Visually verified in browser.

### US-003: Color Temperature Effect Node
**As a** ComfyUI artist, **I want** a node that shifts the color temperature of an image warmer or cooler **so that** I can correct white balance or set a mood.

**Acceptance Criteria:**
- [ ] Node `CoolColorTemperatureEffect` appears in ComfyUI node browser.
- [ ] Inputs: `temperature` FLOAT [-1.0, 1.0, default 0.0] (negative = cool/blue, positive = warm/orange), `tint` FLOAT [-1.0, 1.0, default 0.0] (green–magenta axis).
- [ ] Output: `EFFECT_PARAMS`.
- [ ] Live WebGL2 preview widget reflects parameter changes in real time.
- [ ] Default params (0, 0) produce no visible change to the source image.
- [ ] Effect renders correctly through `CoolVideoGenerator` frame-by-frame.
- [ ] Typecheck / lint passes.
- [ ] Visually verified in browser.

### US-004: Curves (RGB Lift / Gamma / Gain) Effect Node
**As a** ComfyUI artist, **I want** lift/gamma/gain controls per channel **so that** I can perform precise tonal adjustments to shadows, midtones, and highlights independently.

**Acceptance Criteria:**
- [ ] Node `CoolCurvesEffect` appears in ComfyUI node browser.
- [ ] Inputs: `lift` FLOAT [0.0, 1.0, default 0.0], `gamma` FLOAT [0.1, 4.0, default 1.0], `gain` FLOAT [0.0, 4.0, default 1.0] (applied uniformly across RGB).
- [ ] Output: `EFFECT_PARAMS`.
- [ ] Live WebGL2 preview widget reflects parameter changes in real time.
- [ ] Default params (lift=0, gamma=1, gain=1) produce no visible change to the source image.
- [ ] Effect renders correctly through `CoolVideoGenerator` frame-by-frame.
- [ ] Typecheck / lint passes.
- [ ] Visually verified in browser.

### US-005: Color Balance Effect Node
**As a** ComfyUI artist, **I want** separate tint controls for shadows, midtones, and highlights **so that** I can apply split-toning and cinematic color looks.

**Acceptance Criteria:**
- [ ] Node `CoolColorBalanceEffect` appears in ComfyUI node browser.
- [ ] Inputs: `shadows_r`, `shadows_g`, `shadows_b`, `midtones_r`, `midtones_g`, `midtones_b`, `highlights_r`, `highlights_g`, `highlights_b` — all FLOAT [-1.0, 1.0, default 0.0].
- [ ] Output: `EFFECT_PARAMS`.
- [ ] Live WebGL2 preview widget reflects parameter changes in real time.
- [ ] All defaults at 0.0 produce no visible change to the source image.
- [ ] Effect renders correctly through `CoolVideoGenerator` frame-by-frame.
- [ ] Typecheck / lint passes.
- [ ] Visually verified in browser.

### US-006: Sepia / Black & White / Duotone Effect Node
**As a** ComfyUI artist, **I want** a node that converts an image to sepia tone, black & white, or a duotone look **so that** I can apply classic and stylized monochrome aesthetics.

**Acceptance Criteria:**
- [ ] Node `CoolToneMappingEffect` appears in ComfyUI node browser.
- [ ] Inputs: `mode` COMBO ["none", "bw", "sepia", "duotone"], `intensity` FLOAT [0.0, 1.0, default 1.0], `shadow_r/g/b` FLOAT [0.0, 1.0, default 0.0/0.0/0.0], `highlight_r/g/b` FLOAT [0.0, 1.0, default 1.0/1.0/1.0].
- [ ] Output: `EFFECT_PARAMS`.
- [ ] Live WebGL2 preview widget reflects parameter changes in real time.
- [ ] Mode "none" produces no visible change to the source image.
- [ ] Effect renders correctly through `CoolVideoGenerator` frame-by-frame.
- [ ] Typecheck / lint passes.
- [ ] Visually verified in browser.

### US-007: LUT Application Effect Node
**As a** ComfyUI artist, **I want** a node that applies a .cube LUT file to an image **so that** I can use professional color grades in my ComfyUI workflow.

**Acceptance Criteria:**
- [ ] Node `CoolLUTEffect` appears in ComfyUI node browser.
- [ ] Inputs: `lut_path` STRING (absolute or relative path to a `.cube` file), `intensity` FLOAT [0.0, 1.0, default 1.0].
- [ ] Output: `EFFECT_PARAMS`.
- [ ] Backend parses the `.cube` file and uploads LUT data as a 3D texture uniform (or flattened 2D strip) to the GLSL shader.
- [ ] Live WebGL2 preview widget applies the LUT in real time (LUT data fetched via HTTP endpoint or embedded in EFFECT_PARAMS).
- [ ] `intensity = 0.0` produces no visible change (original image); `intensity = 1.0` applies the full LUT.
- [ ] Effect renders correctly through `CoolVideoGenerator` frame-by-frame.
- [ ] Typecheck / lint passes.
- [ ] Visually verified in browser.

## Functional Requirements
- FR-1: Each effect node outputs `EFFECT_PARAMS` via `build_effect_params()` from `nodes/effect_params.py`.
- FR-2: Each effect has a dedicated GLSL fragment shader in `shaders/glsl/` (e.g. `brightness_contrast.frag`, `hsl.frag`, `color_temperature.frag`, `curves.frag`, `color_balance.frag`, `tone_mapping.frag`, `lut.frag`).
- FR-3: All shaders accept the required uniform contract: `uniform sampler2D u_image`, `uniform float u_time`, `uniform vec2 u_resolution`.
- FR-4: Each node has a dedicated Python file in `nodes/` and a JS extension in `web/` using `mount_effect_node_widget` from `web/effect_node_widget.js`.
- FR-5: All seven nodes are registered in `NODE_CLASS_MAPPINGS` and `NODE_DISPLAY_NAME_MAPPINGS` in `__init__.py`.
- FR-6: GL resource cleanup follows the project standard: `try/finally` releasing vao, vbo, fbo, renderbuffer, texture, program, ctx in that order.
- FR-7: For `CoolLUTEffect`, the `.cube` file parser must handle both 17³ and 33³ LUT sizes; unsupported sizes raise `ValueError`.

## Non-Goals (Out of Scope)
- Per-channel (R/G/B separate) curve editors with spline control points.
- HDR or floating-point pipeline changes beyond the existing [0, 1] range.
- LUT format support beyond `.cube` (no `.3dl`, `.mga`, etc.).
- Batch LUT preset management UI or preset library.
- Any new node type other than EFFECT_PARAMS parameter nodes.

## Open Questions
None — all questions resolved during PRD definition.

### Resolved Decisions
- **LUT frontend preview**: Use a new HTTP endpoint `GET /cool_effects/lut?path=...` returning the parsed LUT as a JSON float array. Follows the existing `/cool_effects/shaders` pattern; JS fetches and caches per path change; keeps `EFFECT_PARAMS` lean.
- **Duotone colors**: Use separate FLOAT triplets (`shadow_r`, `shadow_g`, `shadow_b`, `highlight_r`, `highlight_g`, `highlight_b`) — consistent with `CoolColorBalanceEffect` style and simpler for GLSL uniform passing.
