# Lessons Learned — Iteration 000012

## US-001 — Frequency band extraction in audio_utils

**Summary:** Updated `extract_audio_features` to compute per-frame `bass`, `mid`, and `treble` values using `numpy.fft.rfft`, then normalize each band relative to that band's maximum energy across the signal while preserving `rms` and `beat`.

**Key Decisions:** Reused existing frame-window segmentation so all features are aligned per frame; computed one FFT per frame and derived all three bands from the same spectrum; resolved sample rate from audio metadata first, then inferred from sample count and duration when metadata is absent.

**Pitfalls Encountered:** Frequency tests can be unstable if frame windows do not contain integer cycles, so fixture signals were chosen at bin-aligned frequencies for deterministic band separation and normalization assertions.

**Useful Context for Future Agents:** `audio_utils` now supports optional `sample_rate`/`sampling_rate`/`samplerate` in audio dict payloads; when missing, it infers sample rate from `len(audio)/duration`, so keeping duration consistent with source audio length improves spectral mapping accuracy.

## US-002 — CoolBassZoomEffect node

**Summary:** Added a new `CoolBassZoomEffect` node that outputs `EFFECT_PARAMS` for the `bass_zoom` shader, introduced `bass_zoom.frag`, wired registration in `__init__.py`, added a frontend widget with synthetic 60 BPM bass preview pulse, and updated `CoolVideoGenerator` to pass per-frame `u_bass` from extracted audio features.

**Key Decisions:** Followed existing per-effect architecture (dedicated Python node + shader + web extension), reused `effect_node_widget` for uniform binding, and extended `_resolve_audio_feature_frame` to include clipped bass values so audio-reactive uniforms stay bounded and consistent with existing `u_beat`/`u_rms` handling.

**Pitfalls Encountered:** `u_smoothing` needed meaningful shader usage despite stateless fragment execution; resolved by applying smoothing as a nonlinear blend (`mix` + `smoothstep`) over incoming bass energy before computing zoom scale.

**Useful Context for Future Agents:** This repo validates many frontend/shader contracts through source-assertion unittests; for new effects, mirror that strategy to verify uniform contracts and preview-signal behavior without requiring browser runtime tests.
