# Pan Shaders & Effect Params

## Context

The project already ships three shader-backed effects (glitch, vhs, zoom_pulse), each with a dedicated GLSL `.frag` file and a corresponding entry in `effect_params.py` `DEFAULT_PARAMS`. The rendering pipeline in `CoolVideoGenerator` passes all effect params as floats to the shader via uniform names. This PRD adds the GLSL rendering layer for five pan effects (left, right, up, down, diagonal) — the foundational piece that the dedicated ComfyUI nodes (PRD 002) will depend on.

## Goals

- Provide five `pan_*.frag` shaders that implement smooth UV-based pan animations.
- Register default uniform values for all five pan effects in `effect_params.py`.
- Keep all new uniforms as plain `float` types so the existing uniform-passing loop in `CoolVideoGenerator` requires no changes.

## User Stories

### US-001: Pan Left shader renders a left-scrolling animation
**As a** ComfyUI user, **I want** a `pan_left` shader **so that** the image scrolls continuously from right to left over the animation duration.

**Acceptance Criteria:**
- [ ] `shaders/glsl/pan_left.frag` exists and compiles without GLSL errors.
- [ ] The shader accepts `uniform sampler2D u_image`, `uniform float u_time`, `uniform vec2 u_resolution`, `uniform float u_speed`, `uniform float u_origin_x`, `uniform float u_origin_y`.
- [ ] At `u_time = 0` the visible region starts at `(u_origin_x, u_origin_y)`; UV offset increases in the `-X` direction over time proportional to `u_speed * u_time`, wrapping with `fract()`.
- [ ] `DEFAULT_PARAMS["pan_left"]` exists in `effect_params.py` with keys `u_speed`, `u_origin_x`, `u_origin_y`.

---

### US-002: Pan Right shader renders a right-scrolling animation
**As a** ComfyUI user, **I want** a `pan_right` shader **so that** the image scrolls continuously from left to right.

**Acceptance Criteria:**
- [ ] `shaders/glsl/pan_right.frag` exists and compiles without GLSL errors.
- [ ] Accepts the same uniform contract as US-001.
- [ ] UV offset increases in the `+X` direction over time, wrapping with `fract()`.
- [ ] `DEFAULT_PARAMS["pan_right"]` exists in `effect_params.py` with keys `u_speed`, `u_origin_x`, `u_origin_y`.

---

### US-003: Pan Up shader renders a bottom-to-top scrolling animation
**As a** ComfyUI user, **I want** a `pan_up` shader **so that** the image scrolls from bottom to top.

**Acceptance Criteria:**
- [ ] `shaders/glsl/pan_up.frag` exists and compiles without GLSL errors.
- [ ] Accepts the same uniform contract as US-001.
- [ ] UV offset increases in the `+Y` direction over time, wrapping with `fract()`.
- [ ] `DEFAULT_PARAMS["pan_up"]` exists in `effect_params.py` with keys `u_speed`, `u_origin_x`, `u_origin_y`.

---

### US-004: Pan Down shader renders a top-to-bottom scrolling animation
**As a** ComfyUI user, **I want** a `pan_down` shader **so that** the image scrolls from top to bottom.

**Acceptance Criteria:**
- [ ] `shaders/glsl/pan_down.frag` exists and compiles without GLSL errors.
- [ ] Accepts the same uniform contract as US-001.
- [ ] UV offset increases in the `-Y` direction over time, wrapping with `fract()`.
- [ ] `DEFAULT_PARAMS["pan_down"]` exists in `effect_params.py` with keys `u_speed`, `u_origin_x`, `u_origin_y`.

---

### US-005: Pan Diagonal shader renders a diagonal scrolling animation
**As a** ComfyUI user, **I want** a `pan_diagonal` shader **so that** the image scrolls diagonally with a configurable angle.

**Acceptance Criteria:**
- [ ] `shaders/glsl/pan_diagonal.frag` exists and compiles without GLSL errors.
- [ ] Accepts the same uniform contract as US-001 plus `uniform float u_dir_x` and `uniform float u_dir_y` to control the diagonal angle (defaults `0.7071` each for 45°).
- [ ] UV offset is `u_speed * u_time * vec2(u_dir_x, u_dir_y)`, wrapping with `fract()`.
- [ ] `DEFAULT_PARAMS["pan_diagonal"]` exists in `effect_params.py` with keys `u_speed`, `u_origin_x`, `u_origin_y`, `u_dir_x`, `u_dir_y`.

---

## Functional Requirements

- FR-1: Each of the five `.frag` files must satisfy the shared uniform contract: `uniform sampler2D u_image`, `uniform float u_time`, `uniform vec2 u_resolution`.
- FR-2: `u_speed` controls the rate of UV offset per second (e.g. default `0.2` means 20% of image width/height per second).
- FR-3: `u_origin_x` and `u_origin_y` define the UV starting offset (range 0.0–1.0, default `0.0` for both).
- FR-4: All UV arithmetic must use `fract()` for seamless wrapping — no clamping.
- FR-5: `merge_params(effect_name, {})` must return a complete set of uniforms for all five pan effects without raising `KeyError`.
- FR-6: No changes to `video_generator.py` — all new uniforms are plain floats compatible with the existing `float(uniform_value)` cast.

## Non-Goals

- ComfyUI node classes (`CoolPan*Effect`) — covered by PRD 002.
- Registration in `NODE_CLASS_MAPPINGS` or `__init__.py` — covered by PRD 002.
- Tests — covered by PRD 002.
- Clamp-at-edge behaviour (no-wrap mode) — out of scope for this iteration.
- Frontend live-preview widget updates — out of scope for this iteration.

## Open Questions

- **Resolved:** `pan_diagonal` uses tunable `u_dir_x` / `u_dir_y` uniforms with `0.7071` defaults (45°). The `CoolPanDiagonalEffect` node (PRD 002 US-005) exposes them as FLOAT inputs, allowing any angle without requiring a separate shader per angle. A hard-coded angle was discarded — it adds no value and removes flexibility.
