# CoolBassZoomEffect + CoolFreqWarpEffect

## Context

With the audio feature extraction utility and beat detection established in PRD 001, this PRD adds two frequency-driven effect nodes. `CoolBassZoomEffect` zooms the image in/out proportionally to low-frequency (bass) energy. `CoolFreqWarpEffect` distorts UV coordinates using mid and treble frequency bands, producing a ripple/warp effect that reacts to harmonic content. Both nodes consume `audio_utils.extract_audio_features` and emit `EFFECT_PARAMS` for use in `CoolVideoGenerator`.

## Goals

- Extend `extract_audio_features` to populate `bass`, `mid`, and `treble` float fields (replacing the stubs from PRD 001).
- Deliver `CoolBassZoomEffect`: smooth zoom tied to sub-bass/bass energy.
- Deliver `CoolFreqWarpEffect`: UV warp distortion tied to mid and treble energy.
- Both nodes include WebGL2 live preview widgets with synthetic frequency signals.

## User Stories

### US-001: Frequency band extraction in audio_utils
**As a** developer building frequency-driven effect nodes, **I want** `extract_audio_features` to return `bass`, `mid`, and `treble` float values per frame **so that** effect nodes can independently react to different spectral regions without re-implementing FFT logic.

**Acceptance Criteria:**
- [ ] Each dict returned by `extract_audio_features` includes `bass` (float, 20–250 Hz energy, normalised to `[0.0, 1.0]`), `mid` (250–4000 Hz, normalised), and `treble` (4000–20000 Hz, normalised).
- [ ] Frequency band energies are computed via `numpy.fft.rfft` on each audio frame window; each band is the RMS of the magnitudes within that frequency range divided by the per-signal max for that band (so values are relative, not absolute).
- [ ] When `audio_tensor` is `None`, all three fields are `0.0` (consistent with existing graceful-degradation behaviour from PRD 001).
- [ ] The updated `extract_audio_features` remains backward-compatible: `rms` and `beat` fields continue to exist with the same semantics.

---

### US-002: CoolBassZoomEffect node
**As a** ComfyUI user, **I want** a `CoolBassZoomEffect` node that zooms the image proportionally to bass energy per frame **so that** low-frequency hits produce a visible zoom pulse in the rendered video.

**Acceptance Criteria:**
- [ ] Node class `CoolBassZoomEffect` is registered with key `"CoolBassZoomEffect"` and display name `"Cool Bass Zoom Effect"`.
- [ ] Node inputs: `zoom_strength` (FLOAT, default 0.3, min 0.0, max 1.0, step 0.01), `smoothing` (FLOAT, default 0.5, min 0.0, max 1.0, step 0.01).
- [ ] Node output: `EFFECT_PARAMS` built via `build_effect_params("bass_zoom", {...})`.
- [ ] `shaders/glsl/bass_zoom.frag` accepts `u_image`, `u_time`, `u_resolution` plus `u_bass`, `u_zoom_strength`, `u_smoothing`; implements UV zoom centred on `vec2(0.5)` scaled by `1.0 + bass * zoom_strength`.
- [ ] `CoolVideoGenerator` passes `u_bass` (float) per frame from the cached feature list.
- [ ] `web/bass_zoom_effect.js` mounts a live preview widget; when no audio is connected, the preview uses a synthetic bass pulse at ~60 BPM so the zoom effect is visually demonstrated.
- [ ] Node is registered and loaded in `__init__.py` without errors.

---

### US-003: CoolFreqWarpEffect node
**As a** ComfyUI user, **I want** a `CoolFreqWarpEffect` node that warps the image geometry based on mid and treble frequency energy **so that** harmonic and high-frequency content produce visible ripple distortion in the rendered video.

**Acceptance Criteria:**
- [ ] Node class `CoolFreqWarpEffect` is registered with key `"CoolFreqWarpEffect"` and display name `"Cool Freq Warp Effect"`.
- [ ] Node inputs: `warp_intensity` (FLOAT, default 0.4, min 0.0, max 1.0, step 0.01), `warp_frequency` (FLOAT, default 8.0, min 1.0, max 32.0, step 0.5 — controls the spatial frequency of the warp wave), `mid_weight` (FLOAT, default 0.6, min 0.0, max 1.0, step 0.01), `treble_weight` (FLOAT, default 0.4, min 0.0, max 1.0, step 0.01).
- [ ] Node output: `EFFECT_PARAMS` built via `build_effect_params("freq_warp", {...})`.
- [ ] `shaders/glsl/freq_warp.frag` accepts `u_image`, `u_time`, `u_resolution` plus `u_mid`, `u_treble`, `u_warp_intensity`, `u_warp_frequency`, `u_mid_weight`, `u_treble_weight`; distorts UV coordinates using `sin(uv.y * warp_frequency + u_time) * combined_energy * warp_intensity` on the x-axis and a complementary distortion on y.
- [ ] `CoolVideoGenerator` passes `u_mid` and `u_treble` per frame from the cached feature list.
- [ ] `web/freq_warp_effect.js` mounts a live preview widget; when no audio is connected, the preview drives `u_mid` and `u_treble` from `sin(u_time * 2.0)` and `cos(u_time * 3.5)` respectively so the warp is continuously visible.
- [ ] Node is registered and loaded in `__init__.py` without errors.

---

## Functional Requirements

- FR-1: FFT window size per frame is `ceil(sample_rate / fps)` samples, consistent with the beat detection window from PRD 001.
- FR-2: Per-band normalisation uses the maximum band energy across all frames of the clip (computed in a single pass before the render loop) to ensure values stay in `[0.0, 1.0]`.
- FR-3: `CoolVideoGenerator` must pass `u_bass`, `u_mid`, and `u_treble` to all effect shaders that declare those uniforms; shaders that do not declare them are unaffected (ModernGL ignores unknown uniform assignments).
- FR-4: `smoothing` in `CoolBassZoomEffect` is applied as an exponential moving average on the `bass` signal before passing to the shader: `smoothed = prev * smoothing + current * (1 - smoothing)`.
- FR-5: Both shaders must handle `u_bass = 0.0`, `u_mid = 0.0`, `u_treble = 0.0` gracefully (no visual artefact — the image must pass through unchanged).

## Non-Goals

- No changes to `CoolBeatPulseEffect` from PRD 001.
- No stereo spatial effects (left/right channel separation).
- No real-time audio input — effects apply only during `CoolVideoGenerator` render with a pre-loaded audio tensor.
- No waveform visualisation overlay (covered in PRD 003).

## Open Questions

- None.
