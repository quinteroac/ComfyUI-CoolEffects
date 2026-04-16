# Requirement: Camera Lens Distortion Effect Nodes

## Context
ComfyUI-CoolEffects currently offers motion and stylistic effects (Glitch, VHS, ZoomPulse, Pan variants). This iteration adds a **Camera Lens Distortion** pack — five new EFFECT_PARAMS nodes that simulate optical phenomena from real camera lenses: geometric distortion (Fisheye, Pincushion), colour dispersion (Chromatic Aberration), exposure falloff (Vignette), and selective focus (Tilt-Shift). Each node follows the established pattern: Python node + GLSL fragment shader + WebGL2 live preview widget, and outputs `EFFECT_PARAMS` compatible with `CoolVideoGenerator`.

## Goals
- Expand the effect library with 5 lens-based GLSL distortion nodes
- Each node plugs into the existing `CoolVideoGenerator` multi-effect chain without any changes to downstream nodes
- Artists can preview distortion in real time inside the node widget before rendering

## User Stories

### US-001: Fisheye Effect Node
**As a** ComfyUI artist, **I want** a Fisheye node that applies barrel distortion to an image **so that** I can simulate an ultra-wide / fisheye lens look.

**Inputs:**
- `strength` (FLOAT, default 0.5, min 0.0, max 1.0, step 0.01) — distortion intensity
- `zoom` (FLOAT, default 1.0, min 0.5, max 2.0, step 0.01) — compensating zoom to avoid black borders

**Acceptance Criteria:**
- [ ] Node `CoolFisheyeEffect` appears in ComfyUI under the correct category
- [ ] Node outputs `EFFECT_PARAMS` with `effect_name = "fisheye"`
- [ ] GLSL fragment shader `shaders/glsl/fisheye.frag` implements barrel distortion via polar-coordinate UV remapping
- [ ] Live WebGL2 preview inside the node widget updates when `strength` or `zoom` sliders change
- [ ] Effect is visually verified through `CoolVideoGenerator` — rendered video frames show barrel distortion
- [ ] Typecheck / lint passes

---

### US-002: Pincushion Effect Node
**As a** ComfyUI artist, **I want** a Pincushion node that applies pincushion (inverse barrel) distortion **so that** I can simulate the compression warp of a telephoto lens.

**Inputs:**
- `strength` (FLOAT, default 0.5, min 0.0, max 1.0, step 0.01) — distortion intensity
- `zoom` (FLOAT, default 1.0, min 0.5, max 2.0, step 0.01) — compensating zoom

**Acceptance Criteria:**
- [ ] Node `CoolPincushionEffect` appears in ComfyUI
- [ ] Node outputs `EFFECT_PARAMS` with `effect_name = "pincushion"`
- [ ] GLSL fragment shader `shaders/glsl/pincushion.frag` implements inverse-barrel distortion (edges pulled inward)
- [ ] Live WebGL2 preview updates in real time
- [ ] Effect is visually verified through `CoolVideoGenerator`
- [ ] Typecheck / lint passes

---

### US-003: Chromatic Aberration Effect Node
**As a** ComfyUI artist, **I want** a Chromatic Aberration node that separates the RGB channels radially **so that** I can simulate lens colour dispersion (fringing at edges).

**Inputs:**
- `strength` (FLOAT, default 0.01, min 0.0, max 0.1, step 0.001) — magnitude of channel separation
- `radial` (BOOLEAN, default True) — when True, separation grows toward edges (radial); when False, uniform lateral shift

**Acceptance Criteria:**
- [ ] Node `CoolChromaticAberrationEffect` appears in ComfyUI
- [ ] Node outputs `EFFECT_PARAMS` with `effect_name = "chromatic_aberration"`
- [ ] GLSL fragment shader `shaders/glsl/chromatic_aberration.frag` samples R, G, B channels at slightly offset UVs
- [ ] Radial mode increases separation toward image corners; lateral mode applies uniform constant offset
- [ ] Live WebGL2 preview updates in real time
- [ ] Effect is visually verified through `CoolVideoGenerator`
- [ ] Typecheck / lint passes

---

### US-004: Vignette Effect Node
**As a** ComfyUI artist, **I want** a Vignette node that darkens image edges **so that** I can add cinematic depth or draw attention to the centre.

**Inputs:**
- `strength` (FLOAT, default 0.5, min 0.0, max 1.0, step 0.01) — darkness at edges
- `radius` (FLOAT, default 0.75, min 0.1, max 1.5, step 0.01) — how far from centre the vignette begins
- `softness` (FLOAT, default 0.5, min 0.0, max 1.0, step 0.01) — falloff smoothness

**Acceptance Criteria:**
- [ ] Node `CoolVignetteEffect` appears in ComfyUI
- [ ] Node outputs `EFFECT_PARAMS` with `effect_name = "vignette"`
- [ ] GLSL fragment shader `shaders/glsl/vignette.frag` computes radial distance from centre and applies smooth darkening
- [ ] Live WebGL2 preview updates in real time
- [ ] Effect is visually verified through `CoolVideoGenerator`
- [ ] Typecheck / lint passes

---

### US-005: Tilt-Shift Effect Node
**As a** ComfyUI artist, **I want** a Tilt-Shift node that blurs the top and bottom bands of the image while keeping the centre sharp **so that** I can create a miniature/model-world illusion.

**Inputs:**
- `focus_center` (FLOAT, default 0.5, min 0.0, max 1.0, step 0.01) — vertical position of the sharp band (0 = top, 1 = bottom)
- `focus_width` (FLOAT, default 0.2, min 0.0, max 1.0, step 0.01) — fraction of image height kept in focus
- `blur_strength` (FLOAT, default 0.5, min 0.0, max 1.0, step 0.01) — intensity of blur in out-of-focus bands
- `angle` (FLOAT, optional, default 0.0, min 0.0, max 360.0, step 1.0) — rotation of the focus band in degrees; reserved for future use, defaults to horizontal band (0°)

**Acceptance Criteria:**
- [ ] Node `CoolTiltShiftEffect` appears in ComfyUI
- [ ] Node outputs `EFFECT_PARAMS` with `effect_name = "tilt_shift"`
- [ ] GLSL fragment shader `shaders/glsl/tilt_shift.frag` applies a blur kernel (Gaussian approximation) that scales with distance from the focus band
- [ ] Live WebGL2 preview updates in real time when any slider changes
- [ ] Effect is visually verified through `CoolVideoGenerator` — rendered video shows sharp centre band with blurred top/bottom
- [ ] Typecheck / lint passes

---

## Functional Requirements
- FR-1: Each new node must follow the file layout convention: `nodes/<effect>_effect.py` (Python) + `shaders/glsl/<effect>.frag` (GLSL) + `web/<effect>_effect.js` (JS frontend)
- FR-2: Each GLSL shader must accept the standard uniform contract: `uniform sampler2D u_image`, `uniform float u_time`, `uniform vec2 u_resolution`, plus effect-specific uniforms
- FR-3: Each Python node must call `build_effect_params()` from `nodes/effect_params.py` to construct its output
- FR-4: Each JS frontend extension must use `mount_effect_node_widget` from `web/effect_node_widget.js` to attach the WebGL2 preview canvas
- FR-5: All five nodes must be registered in `NODE_CLASS_MAPPINGS` and `NODE_DISPLAY_NAME_MAPPINGS` in `__init__.py`
- FR-6: GL resource cleanup in the Python backend must follow the established `try/finally` teardown order (vao → vbo → fbo → renderbuffer → texture → program → ctx)
- FR-7: No new Python package dependencies may be introduced

## Non-Goals (Out of Scope)
- Animated distortion (e.g. wobbling fisheye over time driven by `u_time`) — static parameter values only for this iteration
- Combining multiple lens distortions into a single "lens preset" node
- Per-axis (X/Y independent) distortion controls
- GPU-accelerated blur for Tilt-Shift beyond a Gaussian approximation in the fragment shader

## Open Questions
- None — all open questions resolved during requirements interview.

## Decisions Recorded
- All five nodes registered under the existing `"CoolEffects"` category (flat, no sub-category).
- Tilt-Shift node includes an optional `angle` input (default 0.0°) reserved for future rotation support; this iteration only uses the horizontal band (angle = 0).
