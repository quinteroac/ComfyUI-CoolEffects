# Frosted Glass Effect Node

## Context

ComfyUI-CoolEffects ships a growing set of GLSL-based effect parameter nodes.
This PRD adds a companion effect to Water Drops (PRD 001): a frosted / fogged glass
simulation. Where Water Drops distorts through individual refracting droplets, Frosted
Glass renders a broad soft blur with a procedural condensation pattern — the kind of
look seen on a bathroom mirror or a cold window in a warm room.

## Goals

- Add a `CoolFrostedGlassEffect` node that outputs `EFFECT_PARAMS` compatible with
  `CoolVideoGenerator`'s multi-effect chaining pipeline.
- Implement a GLSL fragment shader (`frosted_glass.frag`) that combines a directional
  gaussian-style blur with a procedural noise-based frost pattern.
- Expose intuitive parameters (frost intensity, blur radius, condensation uniformity,
  temperature tint) as ComfyUI node inputs.
- Provide a live WebGL2 preview widget so the user sees the effect in real time.

## User Stories

### US-001: Configure Frosted Glass Parameters
**As a** ComfyUI workflow author, **I want** to control how heavily frosted and blurred
the glass appears **so that** I can set anything from a light haze to a fully opaque
white frost.

**Acceptance Criteria:**
- [ ] Node exposes five numeric inputs: `frost_intensity` (FLOAT, 0.0–1.0, default 0.5),
      `blur_radius` (FLOAT, 0.0–0.05, default 0.015), `uniformity` (FLOAT, 0.0–1.0,
      default 0.6 — controls spatial frequency of frost noise: low = broad patches,
      high = fine-grained), `tint_temperature` (FLOAT, -1.0–1.0, default 0.0 — negative
      = cold blue, positive = warm yellow), `condensation_rate` (FLOAT, 0.0–1.0,
      default 0.0 — drives frost build-up over video duration via `u_time`).
- [ ] Each widget accepts the full specified range without clamping errors.
- [ ] Node output is typed `EFFECT_PARAMS` and carries
      `{"effect_name": "frosted_glass", "params": {...}}`.

### US-002: Live WebGL2 Preview in Node
**As a** ComfyUI workflow author, **I want** to see the frosted glass distortion
animated in the node widget **so that** I can judge the look without running the full
pipeline.

**Acceptance Criteria:**
- [ ] A canvas widget is mounted inside the `CoolFrostedGlassEffect` node, showing
      the effect on a placeholder or connected image.
- [ ] The preview animates (`u_time` drives subtle noise evolution — frost is not
      completely static).
- [ ] Changing any parameter widget updates the preview within one animation frame.
- [ ] The canvas uses `frosted_glass.frag` fetched from
      `/cool_effects/shaders/frosted_glass` — no inlined GLSL string.

### US-003: Integration with VideoGenerator
**As a** ComfyUI workflow author, **I want** to connect `CoolFrostedGlassEffect` to
`CoolVideoGenerator` alongside other effects **so that** the frosted look is applied
consistently across every frame of the output video.

**Acceptance Criteria:**
- [ ] Connecting `CoolFrostedGlassEffect` to any `effect_params_N` slot of
      `CoolVideoGenerator` produces a video with the frosted glass rendered on every
      frame.
- [ ] When chained after `CoolWaterDropsEffect`, the frosted blur is applied over the
      already-distorted frame — the two effects compose correctly.
- [ ] `CoolVideoGenerator` does not raise an exception when `effect_name` is
      `"frosted_glass"`.

### US-004: Directional Blur Quality
**As a** ComfyUI workflow author, **I want** the blur to look like light scattered
through ground glass, not a simple box blur **so that** the result is visually
convincing even at large blur radii.

**Acceptance Criteria:**
- [ ] The blur samples at least 8 offset directions per pixel, with offsets perturbed
      by the procedural noise pattern to break the uniform ring artifact.
- [ ] At `blur_radius = 0.015` and `frost_intensity = 0.5`, fine detail in a test
      image is visibly softened but the image is still recognisable.
- [ ] At `blur_radius = 0.04` and `frost_intensity = 1.0`, the image is heavily
      obscured with a white frost overlay and only broad shapes remain.

---

## Functional Requirements

- FR-1: Create `nodes/frosted_glass_effect.py` with class `CoolFrostedGlassEffect`
  following the same structure as other effect nodes — `INPUT_TYPES`,
  `RETURN_TYPES = ("EFFECT_PARAMS",)`, `FUNCTION = "build_params"`, and a
  `build_params()` method that calls `build_effect_params("frosted_glass", {...})`.
- FR-2: Create `shaders/glsl/frosted_glass.frag` with uniforms `uniform sampler2D
  u_image`, `uniform float u_time`, `uniform vec2 u_resolution`, plus
  `uniform float u_frost_intensity`, `uniform float u_blur_radius`,
  `uniform float u_uniformity`, `uniform float u_tint_temperature`,
  `uniform float u_condensation_rate`. `u_uniformity` modulates the frequency of
  the procedural noise (low = large frost patches, high = fine crystalline texture).
  `u_condensation_rate` scales the frost coverage as a function of `u_time`, so at
  rate > 0 the glass progressively frosts over during the video.
- FR-3: The frost pattern must be generated procedurally via a noise or hash function
  — no external texture required.
- FR-4: `tint_temperature` must shift the final colour: negative values add a blue-cold
  cast (simulate cold glass), positive values add a warm-yellow cast (simulate steamy
  bathroom); at 0.0 the output is colour-neutral.
- FR-5: Create `web/frosted_glass_effect.js` as a ComfyUI extension that mounts a
  WebGL2 canvas widget using `mount_effect_node_widget`, passing all five uniforms.
  Preview placeholder uses `create_placeholder_texture(document_ref, 512)` via the
  factory — no custom placeholder logic required.
- FR-6: Register `CoolFrostedGlassEffect` in `__init__.py` under
  `NODE_CLASS_MAPPINGS` and `NODE_DISPLAY_NAME_MAPPINGS`.
- FR-7: Add `web/frosted_glass_effect.js` to the extension list in `__init__.py`.
- FR-8: All GL resources allocated in the Python rendering path must be released
  in a `try/finally` block per project conventions.

## Non-Goals

- Individual water drop simulation — covered in PRD 001.
- A "defrost" animation where frost melts away over time (could be a future iteration).
- Any interaction with cursor position (hover-to-defrost).
- Standalone image rendering — the node only outputs `EFFECT_PARAMS`.

## Open Questions

- None. All questions resolved: `uniformity` controls spatial frequency of frost noise;
  `condensation_rate` added to drive progressive frost build-up over video duration.
