# CoolWaveformEffect

## Context

With bass, beat, and frequency warp effects delivered in PRDs 001 and 002, this PRD completes the audio-reactive set by adding a waveform visualiser effect. `CoolWaveformEffect` overlays the raw audio waveform of the current frame window directly onto the image as a GLSL-rendered line, giving the video an oscilloscope-style visual tied to the actual audio signal shape — not just its energy.

## Goals

- Deliver `CoolWaveformEffect`: a self-contained effect node that renders the audio waveform as a coloured line overlay on top of the image.
- Support user control over waveform position, height, colour, line thickness, and opacity.
- Include a WebGL2 live preview widget with a synthetic sine waveform when no audio is available.
- Extend `audio_utils.extract_audio_features` to return a compact waveform sample array per frame.

## User Stories

### US-001: Per-frame waveform samples in audio_utils
**As a** developer building the waveform effect node, **I want** `extract_audio_features` to include a fixed-length normalised waveform sample array per frame **so that** the shader can read the waveform shape without additional processing.

**Acceptance Criteria:**
- [ ] Each dict returned by `extract_audio_features` includes a `waveform` key whose value is a `list` of exactly 256 floats in `[-1.0, 1.0]`, representing the normalised audio samples for that frame's window resampled to 256 points.
- [ ] Resampling to 256 points is done via linear interpolation using `numpy.interp`; no additional dependencies required.
- [ ] When `audio_tensor` is `None`, `waveform` is a list of 256 zeros.
- [ ] Existing fields (`rms`, `beat`, `bass`, `mid`, `treble`) are unaffected by this change.

---

### US-002: CoolWaveformEffect node
**As a** ComfyUI user, **I want** a `CoolWaveformEffect` node that overlays the audio waveform as a visible line on each video frame **so that** the rendered video shows a real-time oscilloscope display synchronised to the audio.

**Acceptance Criteria:**
- [ ] Node class `CoolWaveformEffect` is registered with key `"CoolWaveformEffect"` and display name `"Cool Waveform Effect"`.
- [ ] Node inputs: `line_color` (STRING, default `"1.0,0.8,0.2"` — RGB floats comma-separated), `line_thickness` (FLOAT, default 0.005, min 0.001, max 0.05, step 0.001), `waveform_height` (FLOAT, default 0.2, min 0.05, max 0.8, step 0.01 — fraction of image height), `waveform_y` (FLOAT, default 0.8, min 0.0, max 1.0, step 0.01 — vertical centre position in UV space), `opacity` (FLOAT, default 0.85, min 0.0, max 1.0, step 0.01).
- [ ] Node output: `EFFECT_PARAMS` built via `build_effect_params("waveform", {...})`.
- [ ] `shaders/glsl/waveform.frag` accepts `u_image`, `u_time`, `u_resolution` (required contract) plus `u_waveform[256]` (float array uniform), `u_line_color` (vec3), `u_line_thickness`, `u_waveform_height`, `u_waveform_y`, `u_opacity`; renders the waveform by looking up the sample at `floor(uv.x * 256.0)` and drawing a line where `abs(uv.y - (waveform_y + sample * waveform_height * 0.5)) < line_thickness`.
- [ ] `CoolVideoGenerator` passes the 256-element `u_waveform` array uniform per frame from the cached feature list using `program['u_waveform'].value = features[i]['waveform']`.
- [ ] `web/waveform_effect.js` mounts a live preview widget via `mount_effect_node_widget`; when no audio is connected the preview synthesises `u_waveform` values from `sin(u_time * 4.0 + index / 40.0)` so the oscilloscope line is always animated.
- [ ] Node is registered and loaded in `__init__.py` without errors.

---

### US-003: Waveform colour input validation
**As a** ComfyUI user, **I want** malformed `line_color` strings to fall back to a default colour rather than crashing the render **so that** a typo in the colour input does not abort the video generation job.

**Acceptance Criteria:**
- [ ] If `line_color` cannot be parsed as three comma-separated floats, the node logs a warning via Python's `logging` module and substitutes the default `(1.0, 0.8, 0.2)`.
- [ ] Each component is clamped to `[0.0, 1.0]` after parsing regardless of the input value.
- [ ] The fallback does not raise an exception visible to the user in the ComfyUI error panel.

---

## Functional Requirements

- FR-1: The waveform sample window for frame `i` is the same `ceil(sample_rate / fps)` samples used for energy analysis, resampled to exactly 256 points.
- FR-2: ModernGL uniform array assignment uses `program['u_waveform'].value = tuple(features[i]['waveform'])` (a Python tuple of 256 floats).
- FR-3: The shader must not alter pixels outside the waveform line region — the underlying image must remain fully visible everywhere except where the waveform is drawn.
- FR-4: All GL resource cleanup follows the project-standard `try/finally` teardown order if any standalone context is used.
- FR-5: The JS preview widget reads `u_waveform` as a `uniform float u_waveform[256]` in the WebGL2 GLSL shader and populates it via `gl.uniform1fv(loc, Float32Array)`.

## Non-Goals

- No stereo dual-channel waveform (single mono channel only).
- No frequency spectrum / bar chart visualisation (that would be a separate effect).
- No user-selectable waveform position presets (top, bottom, centre) — raw `waveform_y` float is sufficient.
- No changes to `CoolBeatPulseEffect`, `CoolBassZoomEffect`, or `CoolFreqWarpEffect`.

## Open Questions

- None.
