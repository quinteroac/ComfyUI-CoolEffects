# Water Drops on Glass Effect Node

## Context

ComfyUI-CoolEffects already ships Glitch, VHS, ZoomPulse, and Pan effect nodes, each
following a standard pattern: a Python `EFFECT_PARAMS` node, a GLSL fragment shader
in `shaders/glsl/`, and a JavaScript WebGL2 preview widget. This PRD adds a new
effect that simulates water droplets falling and sliding across a glass surface,
distorting the image through refraction.

## Goals

- Add a `CoolWaterDropsEffect` node that outputs `EFFECT_PARAMS` compatible with
  `CoolVideoGenerator`'s multi-effect chaining pipeline.
- Implement a GLSL fragment shader (`water_drops.frag`) that produces convincing
  animated water drops with UV-space refraction.
- Expose intuitive parameters (drop density, drop size, fall speed, refraction
  strength) as ComfyUI node inputs.
- Provide a live WebGL2 preview widget in the node so the user sees the effect
  in real time without running the full workflow.

## User Stories

### US-001: Configure Water Drop Parameters
**As a** ComfyUI workflow author, **I want** to control the density, size, speed,
and refraction strength of the water drops **so that** I can dial in the exact
wet-glass look I need for my video.

**Acceptance Criteria:**
- [ ] Node exposes six numeric inputs: `drop_density` (INT, 1–200, default 60),
      `drop_size` (FLOAT, 0.01–0.5, default 0.08), `fall_speed` (FLOAT, 0.1–5.0,
      default 1.0), `refraction_strength` (FLOAT, 0.0–1.0, default 0.3),
      `gravity` (FLOAT, 0.1–5.0, default 1.0), `wind` (FLOAT, -2.0–2.0, default 0.0).
- [ ] Each input widget is visible in the ComfyUI node and accepts the full
      specified range without clamping errors.
- [ ] Node output is typed `EFFECT_PARAMS` and carries `{"effect_name": "water_drops", "params": {...}}`.

### US-002: Live WebGL2 Preview in Node
**As a** ComfyUI workflow author, **I want** to see an animated preview of the water
drops effect directly inside the node widget **so that** I can tweak parameters
without running the full generation pipeline.

**Acceptance Criteria:**
- [ ] A canvas widget is mounted inside the `CoolWaterDropsEffect` node, showing
      the effect applied to a placeholder image (or the connected upstream image
      if available).
- [ ] The preview animates in real time using `requestAnimationFrame`, driven by
      `u_time`.
- [ ] Changing any of the four parameter widgets updates the preview within one
      animation frame — no page reload required.
- [ ] The canvas uses the same `water_drops.frag` shader source fetched from
      `/cool_effects/shaders/water_drops` (not an inlined string).

### US-003: Integration with VideoGenerator
**As a** ComfyUI workflow author, **I want** to chain `CoolWaterDropsEffect` with
other effect nodes into `CoolVideoGenerator` **so that** water drops appear on top
of or combined with other effects in the final video.

**Acceptance Criteria:**
- [ ] Connecting `CoolWaterDropsEffect` output to any `effect_params_N` slot of
      `CoolVideoGenerator` produces a video with the water drops rendered on every
      frame.
- [ ] When chained after another effect (e.g. VHS), the drops are applied to the
      already-processed frame — output is visually correct (drops on top of VHS
      noise, not the other way around unless order is reversed).
- [ ] `CoolVideoGenerator` does not raise an exception when `effect_name` is
      `"water_drops"`.

---

## Functional Requirements

- FR-1: Create `nodes/water_drops_effect.py` with class `CoolWaterDropsEffect`
  following the same structure as `nodes/glitch_effect.py` — `INPUT_TYPES`,
  `RETURN_TYPES = ("EFFECT_PARAMS",)`, `FUNCTION = "build_params"`, and a
  `build_params()` method that calls `build_effect_params("water_drops", {...})`.
- FR-2: Create `shaders/glsl/water_drops.frag` with uniforms `uniform sampler2D
  u_image`, `uniform float u_time`, `uniform vec2 u_resolution`, plus
  `uniform int u_drop_density`, `uniform float u_drop_size`,
  `uniform float u_fall_speed`, `uniform float u_refraction_strength`,
  `uniform float u_gravity`, `uniform float u_wind`.
- FR-3: The shader must produce animated drops using a hash / noise function for
  procedural placement — no texture atlas required.
- FR-4: Create `web/water_drops_effect.js` as a ComfyUI extension that mounts a
  WebGL2 canvas widget using the shared `mount_effect_node_widget` factory from
  `web/effect_node_widget.js`, passing all six uniforms. The preview placeholder
  uses `create_placeholder_texture(document_ref, 512)` via the factory — no custom
  placeholder logic required.
- FR-5: Register `CoolWaterDropsEffect` in `__init__.py` under
  `NODE_CLASS_MAPPINGS` and `NODE_DISPLAY_NAME_MAPPINGS`.
- FR-6: Add `web/water_drops_effect.js` to the extension list in `__init__.py`
  (or equivalent WEB_DIRECTORY discovery mechanism).
- FR-7: All GL resources allocated during preview rendering must be released in a
  `try/finally` block per project conventions (applies to Python backend
  rendering path in VideoGenerator).

## Non-Goals

- Frosted glass blur or condensation — covered in PRD 002.
- Simulating drops pooling or running off the bottom edge with physics.
- Any audio-reactive behaviour.
- A standalone "render image" mode — the node only outputs `EFFECT_PARAMS`.

## Open Questions

- None. All questions resolved: `gravity` and `wind` added as parameters;
  preview placeholder uses the standard `create_placeholder_texture(512)` factory.
