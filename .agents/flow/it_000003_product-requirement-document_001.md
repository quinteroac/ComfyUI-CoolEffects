# EFFECT_PARAMS Type + Shader Uniforms

## Context

Currently the 3 shaders (`glitch.frag`, `vhs.frag`, `zoom_pulse.frag`) use hardcoded numeric values for all their visual parameters. There is no shared data contract between effect nodes and the video generator. This PRD establishes the `EFFECT_PARAMS` custom ComfyUI type, defines per-effect default parameter dicts, updates the shaders to read per-effect uniforms, and adds `set_uniform` to the WebGL2 renderer so the frontend can update uniforms in real time without reloading the shader.

## Goals

- Define a Python-level `EFFECT_PARAMS` type with `build_effect_params` and per-effect `DEFAULT_PARAMS`.
- Update all 3 shaders to use named uniforms instead of hardcoded constants.
- Add `set_uniform(name, value)` to `create_webgl2_renderer` in the frontend.

## User Stories

### US-001: EFFECT_PARAMS data contract with defaults
**As a** node developer, **I want** a well-defined `EFFECT_PARAMS` type with per-effect defaults **so that** any code that renders an effect can fall back to sensible values when params are not fully specified.

**Acceptance Criteria:**
- [ ] `nodes/effect_params.py` exports `EFFECT_PARAMS = "EFFECT_PARAMS"` (the ComfyUI type string).
- [ ] `build_effect_params(effect_name: str, params: dict) -> dict` returns `{"effect_name": effect_name, "params": params}` and raises `ValueError` if `effect_name` is empty or `params` is not a dict.
- [ ] `DEFAULT_PARAMS: dict[str, dict]` is exported from the same module with entries for `"glitch"`, `"vhs"`, and `"zoom_pulse"`, each containing the original hardcoded values as defaults (e.g. `{"u_wave_freq": 120.0, "u_wave_amp": 0.0025, "u_speed": 10.0}`).
- [ ] `merge_params(effect_name: str, params: dict) -> dict` returns `{**DEFAULT_PARAMS[effect_name], **params}`, raising `KeyError` if `effect_name` is not in `DEFAULT_PARAMS`.

### US-002: Glitch shader per-effect uniforms
**As a** user, **I want** the glitch effect's wave frequency, amplitude, and speed to be controllable via uniforms **so that** they can be set from the node graph instead of being hardcoded.

**Acceptance Criteria:**
- [ ] `glitch.frag` declares `uniform float u_wave_freq`, `uniform float u_wave_amp`, and `uniform float u_speed`.
- [ ] The shader produces visually equivalent output to the previous version when uniforms are set to `u_wave_freq=120.0`, `u_wave_amp=0.0025`, `u_speed=10.0`.
- [ ] No hardcoded per-effect constants remain in `glitch.frag`.

### US-003: VHS shader per-effect uniforms
**As a** user, **I want** the VHS effect's scanline intensity, jitter amount, and chroma shift to be controllable via uniforms **so that** they can be tuned per render.

**Acceptance Criteria:**
- [ ] `vhs.frag` declares `uniform float u_scanline_intensity`, `uniform float u_jitter_amount`, and `uniform float u_chroma_shift`.
- [ ] The shader produces visually equivalent output when uniforms are set to `u_scanline_intensity=0.04`, `u_jitter_amount=0.0018`, `u_chroma_shift=0.002`.
- [ ] No hardcoded per-effect constants remain in `vhs.frag`.

### US-004: ZoomPulse shader per-effect uniforms
**As a** user, **I want** the zoom pulse effect's amplitude and speed to be controllable via uniforms **so that** they can be adjusted per render.

**Acceptance Criteria:**
- [ ] `zoom_pulse.frag` declares `uniform float u_pulse_amp` and `uniform float u_pulse_speed`.
- [ ] The shader produces visually equivalent output when uniforms are set to `u_pulse_amp=0.06`, `u_pulse_speed=3.0`.
- [ ] No hardcoded per-effect constants remain in `zoom_pulse.frag`.

### US-005: WebGL2 renderer set_uniform method
**As a** frontend developer, **I want** `create_webgl2_renderer` to expose a `set_uniform(name, value)` method **so that** parameter widgets can update shader uniforms in real time without reloading the shader program.

**Acceptance Criteria:**
- [ ] `create_webgl2_renderer` returns an object that includes `set_uniform(name, value)`.
- [ ] `set_uniform` calls `gl.uniform1f(gl.getUniformLocation(program, name), value)` if the uniform location exists; silently does nothing if the uniform name is not present in the current program.
- [ ] Calling `set_uniform` while `program` is `null` does not throw an exception.
- [ ] The existing `render`, `set_fragment_shader`, `set_image_texture`, and `dispose` methods remain unchanged.

---

## Functional Requirements

- FR-1: `nodes/effect_params.py` exports `EFFECT_PARAMS`, `build_effect_params`, `DEFAULT_PARAMS`, and `merge_params`.
- FR-2: `glitch.frag` replaces its 3 hardcoded constants with `u_wave_freq`, `u_wave_amp`, `u_speed`.
- FR-3: `vhs.frag` replaces its 3 hardcoded constants with `u_scanline_intensity`, `u_jitter_amount`, `u_chroma_shift`.
- FR-4: `zoom_pulse.frag` replaces its 2 hardcoded constants with `u_pulse_amp`, `u_pulse_speed`.
- FR-5: `create_webgl2_renderer` in `web/effect_selector.js` gains `set_uniform(name, value)` in its returned interface.
- FR-6: `shaders/README.md` is updated to document all per-effect uniform contracts and their default values.

## Non-Goals

- This PRD does not create any ComfyUI nodes.
- This PRD does not modify `CoolVideoGenerator` or the `CoolEffectSelector` node logic.
- This PRD does not add new shaders.

## Open Questions

- None.
