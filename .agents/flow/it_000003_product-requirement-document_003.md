# Per-Effect Selector Nodes

## Context

With `EFFECT_PARAMS` defined and `CoolVideoGenerator` updated to accept it, the final piece is a set of dedicated ComfyUI nodes — one per effect — each exposing its specific parameters as native ComfyUI FLOAT/INT widgets and outputting an `EFFECT_PARAMS` bundle. Each node also includes a live GLSL preview DOM widget. Parameter widgets are native so they serialize automatically with the graph and can receive connections from other nodes. The DOM widget is used only for the preview canvas; `onWidgetChanged` wires parameter changes to `renderer.set_uniform` for real-time preview updates.

## Goals

- Implement `CoolGlitchEffect`, `CoolVHSEffect`, and `CoolZoomPulseEffect` nodes.
- Each node exposes its effect-specific parameters as native ComfyUI FLOAT widgets.
- Each node outputs `EFFECT_PARAMS` with the effect name and current parameter values.
- Each node shows a live animated GLSL preview that updates in real time when a parameter widget changes.

## User Stories

### US-001: CoolGlitchEffect node
**As a** ComfyUI user, **I want** a dedicated Glitch effect node with wave controls **so that** I can tune the glitch look and wire the result to the video generator.

**Acceptance Criteria:**
- [ ] Node `CoolGlitchEffect` appears in the `CoolEffects` category.
- [ ] Native FLOAT inputs: `wave_freq` (default 120.0, min 1.0, max 500.0, step 1.0), `wave_amp` (default 0.0025, min 0.0, max 0.05, step 0.0005), `speed` (default 10.0, min 0.0, max 100.0, step 0.5).
- [ ] `RETURN_TYPES = ("EFFECT_PARAMS",)`, `RETURN_NAMES = ("EFFECT_PARAMS",)`.
- [ ] `execute(self, wave_freq, wave_amp, speed)` returns `(build_effect_params("glitch", {"u_wave_freq": wave_freq, "u_wave_amp": wave_amp, "u_speed": speed}),)`.
- [ ] The node widget shows a live animated preview of `glitch.frag` using the placeholder texture.

### US-002: CoolVHSEffect node
**As a** ComfyUI user, **I want** a dedicated VHS effect node with scanline and chroma controls **so that** I can dial in the retro look precisely.

**Acceptance Criteria:**
- [ ] Node `CoolVHSEffect` appears in the `CoolEffects` category.
- [ ] Native FLOAT inputs: `scanline_intensity` (default 0.04, min 0.0, max 0.5, step 0.005), `jitter_amount` (default 0.0018, min 0.0, max 0.02, step 0.0002), `chroma_shift` (default 0.002, min 0.0, max 0.02, step 0.0002).
- [ ] `RETURN_TYPES = ("EFFECT_PARAMS",)`, `RETURN_NAMES = ("EFFECT_PARAMS",)`.
- [ ] `execute(self, scanline_intensity, jitter_amount, chroma_shift)` returns the correct `EFFECT_PARAMS` bundle with keys `u_scanline_intensity`, `u_jitter_amount`, `u_chroma_shift`.
- [ ] The node widget shows a live animated preview of `vhs.frag` using the placeholder texture.

### US-003: CoolZoomPulseEffect node
**As a** ComfyUI user, **I want** a dedicated ZoomPulse effect node with pulse controls **so that** I can control zoom intensity and rhythm.

**Acceptance Criteria:**
- [ ] Node `CoolZoomPulseEffect` appears in the `CoolEffects` category.
- [ ] Native FLOAT inputs: `pulse_amp` (default 0.06, min 0.0, max 0.5, step 0.005), `pulse_speed` (default 3.0, min 0.1, max 20.0, step 0.1).
- [ ] `RETURN_TYPES = ("EFFECT_PARAMS",)`, `RETURN_NAMES = ("EFFECT_PARAMS",)`.
- [ ] `execute(self, pulse_amp, pulse_speed)` returns the correct `EFFECT_PARAMS` bundle with keys `u_pulse_amp`, `u_pulse_speed`.
- [ ] The node widget shows a live animated preview of `zoom_pulse.frag` using the placeholder texture.

### US-004: Real-time preview reflects parameter changes
**As a** ComfyUI user, **I want** the preview canvas to update when I change a parameter widget **so that** I can preview the effect before queuing a render.

**Acceptance Criteria:**
- [ ] Each per-effect node's JS extension registers an `onWidgetChanged` handler that calls `renderer.set_uniform(uniform_name, value)` and does not reload the shader program.
- [ ] The preview updates within one animation frame of the widget value changing.
- [ ] The mapping from widget name to uniform name matches the keys used in `execute` (e.g. widget `wave_freq` → uniform `u_wave_freq`).
- [ ] When WebGL2 is unavailable, the overlay error message is shown and no exception is thrown.

---

## Functional Requirements

- FR-1: Three new Python files: `nodes/glitch_effect.py`, `nodes/vhs_effect.py`, `nodes/zoom_pulse_effect.py`.
- FR-2: Each node imports `EFFECT_PARAMS` and `build_effect_params` from `nodes/effect_params.py`.
- FR-3: All parameter inputs are defined as native ComfyUI `FLOAT` widgets in `INPUT_TYPES["required"]`.
- FR-4: `__init__.py` registers `CoolGlitchEffect`, `CoolVHSEffect`, `CoolZoomPulseEffect` in `NODE_CLASS_MAPPINGS` and `NODE_DISPLAY_NAME_MAPPINGS`.
- FR-5: A new JS file `web/effect_node_widget.js` exports `mount_effect_node_widget(node, effect_name, param_specs)` — a reusable function that mounts only the preview canvas DOM widget and registers an `onWidgetChanged` hook that calls `renderer.set_uniform` for each parameter widget change.
- FR-6: Each effect has a corresponding JS extension file (`web/glitch_effect.js`, etc.) that calls `mount_effect_node_widget` in `onNodeCreated` with the correct `effect_name` and `param_specs` (array of `{widget_name, uniform_name}`).
- FR-7: `mount_effect_node_widget` initializes the WebGL2 preview with default uniform values from `DEFAULT_PARAMS` (fetched via the existing `/cool_effects/shaders` endpoint or hardcoded in JS matching the Python defaults).
- FR-8: The `CoolEffectSelector` node and its widget are not modified.

## Non-Goals

- This PRD does not remove or deprecate `CoolEffectSelector`.
- This PRD does not add new shaders beyond the existing 3.
- This PRD does not modify `CoolVideoGenerator`.

## Open Questions

- None.
