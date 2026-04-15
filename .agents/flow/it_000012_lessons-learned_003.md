# Lessons Learned — Iteration 000012

## US-001 — Per-frame waveform samples in audio_utils

**Summary:** Extended `extract_audio_features` to include a per-frame `waveform` field with 256 normalized samples (resampled per frame window), while preserving existing `rms`, `beat`, `bass`, `mid`, and `treble` behavior.

**Key Decisions:** Added a dedicated waveform path in `nodes/audio_utils.py` using `numpy.interp` for linear interpolation and a fixed `WAVEFORM_SAMPLE_COUNT = 256` constant; for empty/invalid segments, emitted deterministic zero-filled lists to keep output stable.

**Pitfalls Encountered:** The project context claims no automated tests, but this iteration already includes a `tests/` suite; relying on `python -m unittest` alone ran zero tests, so discovery mode (`python -m unittest discover -s tests`) is required.

**Useful Context for Future Agents:** `_default_feature_frame()` now includes `waveform`, so any consumer asserting exact keys/dicts must include that field. The tests verify both `numpy.interp` usage and waveform range/length, and preserve prior assertions for RMS/beat/frequency-band semantics.
