# Audio Extraction Utility + CoolBeatPulseEffect

## Context

ComfyUI-CoolEffects already supports multi-effect video generation with AUDIO input passed to `CoolVideoGenerator`. However, no node currently analyses that audio signal to drive visual effects. This PRD establishes a shared audio feature extraction utility and delivers the first audio-reactive effect node: `CoolBeatPulseEffect`, which pulses image brightness and scale in sync with detected beats.

## Goals

- Provide a reusable per-frame audio feature extractor (`nodes/audio_utils.py`) that all audio-reactive nodes can import.
- Deliver `CoolBeatPulseEffect` as the first self-contained audio-reactive effect node, following the established `nodes/<effect>_effect.py` + `web/<effect>_effect.js` + `shaders/glsl/<effect>.frag` pattern.
- Give the node a WebGL2 live preview widget that simulates the pulse effect using a synthetic beat signal when no real audio is available.

## User Stories

### US-001: Per-frame audio feature extraction
**As a** video pipeline developer, **I want** a utility that converts a raw audio tensor into a list of per-frame feature dicts (RMS amplitude, beat flag, and frequency band stubs) **so that** every audio-reactive effect node can consume consistent, pre-computed features without duplicating DSP logic.

**Acceptance Criteria:**
- [ ] `nodes/audio_utils.py` exports a function `extract_audio_features(audio_tensor, fps, duration) -> list[dict]` that returns exactly `round(duration * fps)` dicts.
- [ ] Each dict contains `{"rms": float, "beat": bool, "bass": float, "mid": float, "treble": float}` where `rms` is in `[0.0, 1.0]`, `beat` is `True` on frames coinciding with an onset/beat event, and `bass`, `mid`, `treble` are `0.0` stubs (populated in PRD 002 without changing this dict contract).
- [ ] Beat detection uses only `numpy` (no `librosa` dependency) — implemented via energy-based onset detection (local energy spike above rolling mean threshold).
- [ ] When `audio_tensor` is `None`, the function returns a list of dicts with `rms=0.0, beat=False, bass=0.0, mid=0.0, treble=0.0` for every frame without raising an exception.
- [ ] The function is importable with a plain `from nodes.audio_utils import extract_audio_features` and does not import `moderngl`, `torch`, or ComfyUI internals at module level.

---

### US-002: CoolBeatPulseEffect node
**As a** ComfyUI user, **I want** a `CoolBeatPulseEffect` parameter node that outputs `EFFECT_PARAMS` **so that** I can chain it into `CoolVideoGenerator` and see image brightness and scale pulse on every detected beat.

**Acceptance Criteria:**
- [ ] Node class `CoolBeatPulseEffect` is registered in `NODE_CLASS_MAPPINGS` with key `"CoolBeatPulseEffect"` and display name `"Cool Beat Pulse Effect"`.
- [ ] Node inputs: `pulse_intensity` (FLOAT, default 0.5, min 0.0, max 1.0, step 0.01), `zoom_amount` (FLOAT, default 0.05, min 0.0, max 0.3, step 0.005), `decay` (FLOAT, default 0.3, min 0.0, max 1.0, step 0.01).
- [ ] Node output: `EFFECT_PARAMS` built via `build_effect_params("beat_pulse", {...})`.
- [ ] `shaders/glsl/beat_pulse.frag` accepts uniforms `u_image`, `u_time`, `u_resolution` (required contract) plus `u_pulse_intensity`, `u_zoom_amount`, `u_decay`, `u_beat`, `u_rms`; applies a brightness flash and slight zoom-in on beat frames with exponential decay between beats.
- [ ] `CoolVideoGenerator` passes `u_beat` (float 0.0/1.0) and `u_rms` (float) to the shader for each frame using features from `extract_audio_features`.
- [ ] `web/beat_pulse_effect.js` mounts a WebGL2 live preview widget via `mount_effect_node_widget`; when no real audio is connected the preview uses a synthetic 120 BPM pulse signal so the widget is visually active.
- [ ] The node is loaded via `importlib` in `__init__.py` alongside all other effect nodes without errors.

---

## Functional Requirements

- FR-1: `extract_audio_features` must handle mono and stereo audio tensors; stereo is averaged to mono before analysis.
- FR-2: Energy-based beat detection computes a short-time energy over windows of `ceil(sample_rate / fps)` samples and flags a beat when the window energy exceeds `1.5 × rolling mean` of the previous 43 windows (≈ 1 second at common fps).
- FR-3: `CoolVideoGenerator` must call `extract_audio_features` once per render job (not per frame) and cache the result list for the duration of the render loop.
- FR-4: Shader zoom is implemented as UV coordinate scaling centred on `vec2(0.5, 0.5)`.
- FR-5: All GL resource cleanup in `CoolBeatPulseEffect` backend (if any standalone render path is added later) must follow the `try/finally` teardown order defined in project conventions.

## Non-Goals

- No `librosa` or `scipy` dependency — pure `numpy` only for DSP.
- No new ComfyUI custom type beyond `EFFECT_PARAMS`; audio features are internal to the render loop, not a node output type.
- No changes to `CoolEffectSelector` or `CoolVideoPlayer` in this PRD.
- No audio waveform visualisation (covered in PRD 003).

## Open Questions

- None.
