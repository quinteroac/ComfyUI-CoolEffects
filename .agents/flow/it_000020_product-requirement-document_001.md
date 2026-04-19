# Requirement: Retro Pixel Effect Nodes (Pixelate, Dithering, Color Quantization, CRT Pixel Grid)

## Context
ComfyUI-CoolEffects currently offers GLSL-based effect nodes for distortion (Glitch, VHS, Zoom Pulse), camera motion (Pan/Dolly/Zoom), color grading (HSL, Curves, LUT, Tone Mapping, etc.), and lens/optic effects (Fisheye, Pincushion, Chromatic Aberration, Frosted Glass, Water Drops). There is no category of effects dedicated to **retro pixel aesthetics** (8-bit, 16-bit, CRT, print-dither looks). Content creators who want to produce retro/arcade/vintage visuals must combine unrelated effects and cannot achieve the characteristic chunky-pixel, low-palette, scanline looks natively.

This iteration adds four new parameter nodes that together cover the core retro pixel toolkit, following the same per-effect architectural pattern already established in the project (one `<effect>.frag` shader + one `nodes/<effect>_effect.py` + one `web/<effect>_effect.js`, all exposing `EFFECT_PARAMS` chainable by `CoolVideoGenerator`).

## Goals
- Add 4 new effect parameter nodes covering the core retro pixel aesthetic: Pixelate, Dithering, Color Quantization, CRT Pixel Grid.
- Each node produces an `EFFECT_PARAMS` output that is chainable into `CoolVideoGenerator` alongside existing effects.
- Each node exposes a live WebGL2 preview widget in the ComfyUI graph (consistent with existing per-effect nodes).
- No new runtime dependencies — implementation uses only `moderngl`, `torch`, `numpy`, and the existing `comfy_api.latest` stack already in the project.
- Shader uniform contract matches the existing convention: every fragment shader accepts `uniform sampler2D u_image`, `uniform float u_time`, `uniform vec2 u_resolution`, plus effect-specific uniforms.

## User Stories
Each story is implementable in one focused session and delivers a complete end-to-end node (Python + GLSL + JS extension + wiring in `__init__.py` + `EFFECT_PARAMS` defaults in `nodes/effect_params.py`).

### US-001: Pixelate / Mosaic Effect Node
**As a** ComfyUI user creating retro-styled video, **I want** a `CoolPixelateEffect` node that reduces image resolution to chunky blocks **so that** I can produce an 8-bit / low-resolution aesthetic chainable into `CoolVideoGenerator`.

**Parameters:**
- `pixel_size` (INT, 1–128, default 8) — size of each square pixel block in output pixels
- `aspect_ratio` (FLOAT, 0.25–4.0, default 1.0) — horizontal/vertical ratio of pixel blocks (values ≠ 1 produce rectangular pixels)

**Acceptance Criteria:**
- [ ] `CoolPixelateEffect` node is registered and appears in the ComfyUI node picker under the CoolEffects category
- [ ] Node exposes `pixel_size` and `aspect_ratio` inputs with the ranges/defaults above
- [ ] Node outputs an `EFFECT_PARAMS` payload with `effect_name = "pixelate"` and the two param values
- [ ] `shaders/glsl/pixelate.frag` exists and respects the shared uniform contract (`u_image`, `u_time`, `u_resolution`)
- [ ] `web/pixelate_effect.js` mounts a live WebGL2 preview widget that updates as the user changes parameters
- [ ] Chaining `CoolPixelateEffect` → `CoolVideoGenerator` renders a video where frames show the expected chunky-pixel mosaic effect
- [ ] Defaults for `pixelate` are present in `nodes/effect_params.py::DEFAULT_PARAMS`
- [ ] **[UI story]** Visually verified in browser with a sample image at `pixel_size=1` (identity), `pixel_size=32` (chunky), and `aspect_ratio=2.0` (wide pixels)
- [ ] Python lint passes; no new dependencies added to `requirements.txt`

---

### US-002: Dithering Effect Node
**As a** ComfyUI user targeting retro/monochrome aesthetics, **I want** a `CoolDitheringEffect` node that applies an ordered (Bayer) dither pattern **so that** I can reproduce the characteristic look of early computer graphics and print media.

**Parameters:**
- `dither_scale` (FLOAT, 0.5–8.0, default 1.0) — scale of the Bayer matrix in screen space (smaller = finer pattern)
- `threshold` (FLOAT, 0.0–1.0, default 0.5) — brightness threshold applied per channel after dither offset
- `palette_size` (INT, 2–16, default 2) — number of quantization levels per channel (2 = pure B/W dither, 4 = CGA-style, etc.)

**Acceptance Criteria:**
- [ ] `CoolDitheringEffect` node is registered and appears in the ComfyUI node picker under the CoolEffects category
- [ ] Node exposes `dither_scale`, `threshold`, `palette_size` inputs with the ranges/defaults above
- [ ] Node outputs an `EFFECT_PARAMS` payload with `effect_name = "dithering"` and the three param values
- [ ] `shaders/glsl/dithering.frag` exists, implements an 8×8 Bayer dither matrix, and respects the shared uniform contract
- [ ] `web/dithering_effect.js` mounts a live WebGL2 preview widget that updates as the user changes parameters
- [ ] Chaining `CoolDitheringEffect` → `CoolVideoGenerator` renders a video showing the ordered dither pattern at the configured scale/threshold/palette
- [ ] Defaults for `dithering` are present in `nodes/effect_params.py::DEFAULT_PARAMS`
- [ ] **[UI story]** Visually verified in browser with a sample image at `palette_size=2` (pure B/W dither) and `palette_size=4` (4-level dither)
- [ ] Python lint passes; no new dependencies added to `requirements.txt`

---

### US-003: Color Quantization Effect Node
**As a** ComfyUI user recreating specific retro hardware palettes, **I want** a `CoolColorQuantizationEffect` node that reduces each RGB channel to a configurable number of discrete levels **so that** I can reproduce NES / Game Boy / early-PC color depths.

**Parameters:**
- `levels_r` (INT, 2–32, default 4) — number of quantization levels on the red channel
- `levels_g` (INT, 2–32, default 4) — number of quantization levels on the green channel
- `levels_b` (INT, 2–32, default 4) — number of quantization levels on the blue channel

**Acceptance Criteria:**
- [ ] `CoolColorQuantizationEffect` node is registered and appears in the ComfyUI node picker under the CoolEffects category
- [ ] Node exposes `levels_r`, `levels_g`, `levels_b` inputs with the ranges/defaults above
- [ ] Node outputs an `EFFECT_PARAMS` payload with `effect_name = "color_quantization"` and the three param values
- [ ] `shaders/glsl/color_quantization.frag` exists, quantizes each channel independently via `floor(c * levels) / (levels - 1)`, and respects the shared uniform contract
- [ ] `web/color_quantization_effect.js` mounts a live WebGL2 preview widget that updates as the user changes parameters
- [ ] Chaining `CoolColorQuantizationEffect` → `CoolVideoGenerator` renders a video with visibly banded / quantized colors per channel
- [ ] Defaults for `color_quantization` are present in `nodes/effect_params.py::DEFAULT_PARAMS`
- [ ] **[UI story]** Visually verified in browser with a sample image at `levels_r=levels_g=levels_b=2` (8-color total) and `=8` (512-color)
- [ ] Python lint passes; no new dependencies added to `requirements.txt`

---

### US-004: CRT Pixel Grid Effect Node
**As a** ComfyUI user going for a vintage-monitor look, **I want** a `CoolCrtPixelGridEffect` node that simulates the RGB subpixel grid and scanlines of a CRT display **so that** the video reads as being viewed through an old-school screen.

**Parameters:**
- `pixel_size` (INT, 2–32, default 6) — size of each CRT cell (one R-G-B triad) in output pixels
- `grid_strength` (FLOAT, 0.0–1.0, default 0.6) — intensity of the vertical RGB subpixel mask (0 = off, 1 = fully saturated subpixel stripes)
- `scanline_strength` (FLOAT, 0.0–1.0, default 0.4) — intensity of the horizontal scanline darkening (0 = off, 1 = strong scanlines)

**Acceptance Criteria:**
- [ ] `CoolCrtPixelGridEffect` node is registered and appears in the ComfyUI node picker under the CoolEffects category
- [ ] Node exposes `pixel_size`, `grid_strength`, `scanline_strength` inputs with the ranges/defaults above
- [ ] Node outputs an `EFFECT_PARAMS` payload with `effect_name = "crt_pixel_grid"` and the three param values
- [ ] `shaders/glsl/crt_pixel_grid.frag` exists, renders both the RGB subpixel mask (vertical stripes within each cell) and horizontal scanlines, and respects the shared uniform contract
- [ ] `web/crt_pixel_grid_effect.js` mounts a live WebGL2 preview widget that updates as the user changes parameters
- [ ] Chaining `CoolCrtPixelGridEffect` → `CoolVideoGenerator` renders a video that visibly shows RGB subpixel stripes and darkened scanlines
- [ ] Defaults for `crt_pixel_grid` are present in `nodes/effect_params.py::DEFAULT_PARAMS`
- [ ] **[UI story]** Visually verified in browser with a sample image at `grid_strength=0, scanline_strength=0` (near-identity aside from pixelation) and both at `1.0` (strong CRT look)
- [ ] Python lint passes; no new dependencies added to `requirements.txt`

---

## Functional Requirements

- **FR-1:** Every new effect registers a new entry in `NODE_CLASS_MAPPINGS` and `NODE_DISPLAY_NAME_MAPPINGS` inside `__init__.py`, loaded via the same `importlib.util.spec_from_file_location` pattern used by existing effect modules.
- **FR-2:** Every new effect adds a corresponding `DEFAULT_PARAMS` entry in `nodes/effect_params.py` keyed by its `effect_name` (`"pixelate"`, `"dithering"`, `"color_quantization"`, `"crt_pixel_grid"`).
- **FR-3:** Every new fragment shader declares `uniform sampler2D u_image`, `uniform float u_time`, `uniform vec2 u_resolution`, plus the effect-specific uniforms matching the node's parameters (GLSL names in `snake_case` with `u_` prefix, e.g. `u_pixel_size`, `u_dither_scale`, `u_levels_r`, `u_grid_strength`).
- **FR-4:** `CoolVideoGenerator` must dispatch each new `effect_name` correctly: on render, it binds the effect's fragment shader and sets all of that effect's uniforms from the merged params dict.
- **FR-5:** Every new JS extension reuses `mount_effect_node_widget` / `apply_effect_widget_uniform_from_widget` from `web/effect_node_widget.js` (do not reinvent preview plumbing).
- **FR-6:** Every new JS extension fetches its shader via the existing `loadShader(name)` helper in `web/shaders/loader.js` (shaders are served by `GET /cool_effects/shaders/{name}`).
- **FR-7:** GL resource lifecycle inside any new shader rendering path in `CoolVideoGenerator` follows the existing `try/finally` release order (`vao, vbo, fbo, renderbuffer, texture, program, ctx`).
- **FR-8:** All four new effects can be chained together in a single `CoolVideoGenerator` instance (e.g. Pixelate → ColorQuantization → Dithering → CrtPixelGrid) without errors and each effect's output feeds the next's `u_image` input, per the existing multi-effect chaining pipeline.
- **FR-9:** Python files follow `snake_case` naming: `nodes/pixelate_effect.py`, `nodes/dithering_effect.py`, `nodes/color_quantization_effect.py`, `nodes/crt_pixel_grid_effect.py`. Shader files: `shaders/glsl/pixelate.frag`, `dithering.frag`, `color_quantization.frag`, `crt_pixel_grid.frag`. JS files: `web/pixelate_effect.js`, `web/dithering_effect.js`, `web/color_quantization_effect.js`, `web/crt_pixel_grid_effect.js`.

## Non-Goals (Out of Scope)
- **Error-diffusion dithering** (Floyd-Steinberg, Atkinson, Stucki) — ordered/Bayer dither only in this iteration; error diffusion requires frame-buffer feedback that doesn't fit the current stateless per-pixel shader model.
- **ASCII / character-mapping effects** — visually related but require a glyph atlas texture and a different pipeline; deferred.
- **Pixel sorting / pixel dissolve / shatter** — temporal/animated pixel effects; deferred to a future iteration.
- **Non-square (hex/tri) mosaic** — different tessellation model; deferred.
- **Halftone dots** — related but visually distinct from Bayer dither; deferred.
- **Custom palette injection** (user-supplied PNG palettes, `.pal` files) — current iteration quantizes on a per-channel uniform grid only.
- **Modifying `CoolVideoMixer`, `CoolAudioMixer`, or any existing effect node's behavior** — new nodes only; existing nodes remain untouched except for the dispatch wiring in `CoolVideoGenerator` and `DEFAULT_PARAMS` in `effect_params.py`.
- **Automated tests** — the project uses manual testing only; no test suite will be added.
- **New runtime dependencies** — nothing added to `requirements.txt`.

## Open Questions
- None
