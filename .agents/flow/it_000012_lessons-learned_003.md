# Lessons Learned — Iteration 000012

## US-001 — Per-frame waveform samples in audio_utils

**Summary:** Extended `extract_audio_features` to include a per-frame `waveform` field with 256 normalized samples (resampled per frame window), while preserving existing `rms`, `beat`, `bass`, `mid`, and `treble` behavior.

**Key Decisions:** Added a dedicated waveform path in `nodes/audio_utils.py` using `numpy.interp` for linear interpolation and a fixed `WAVEFORM_SAMPLE_COUNT = 256` constant; for empty/invalid segments, emitted deterministic zero-filled lists to keep output stable.

**Pitfalls Encountered:** The project context claims no automated tests, but this iteration already includes a `tests/` suite; relying on `python -m unittest` alone ran zero tests, so discovery mode (`python -m unittest discover -s tests`) is required.

**Useful Context for Future Agents:** `_default_feature_frame()` now includes `waveform`, so any consumer asserting exact keys/dicts must include that field. The tests verify both `numpy.interp` usage and waveform range/length, and preserve prior assertions for RMS/beat/frequency-band semantics.

## US-002 — CoolWaveformEffect node

**Summary:** Added the `CoolWaveformEffect` node, `waveform.frag` shader, frontend widget extension, and generator uniform plumbing so per-frame 256-sample waveform data renders as an oscilloscope line in both preview and video output.

**Key Decisions:** Implemented `line_color` parsing in the node into `u_line_color` vec3 values, added vector/uniform-array support to the shared WebGL preview controller (`set_uniform_array` + `uniform1fv`), and kept waveform-frame fallback logic in `video_generator.py` so rendering remains stable when frame features are missing or malformed.

**Pitfalls Encountered:** Existing generator uniform assignment assumed scalar-only values; waveform required vec3 (`u_line_color`) and float-array (`u_waveform[256]`) support, so scalar-only writes had to be generalized without regressing existing effect uniforms.

**Useful Context for Future Agents:** For shader uniform arrays in frontend previews, use `"u_<name>[0]"` with `set_uniform_array`; for backend Moderngl programs, assigning Python lists directly to `program['u_waveform'].value` works when length matches shader array size and values are numeric.
