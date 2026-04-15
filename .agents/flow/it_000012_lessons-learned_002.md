# Lessons Learned — Iteration 000012

## US-001 — Frequency band extraction in audio_utils

**Summary:** Updated `extract_audio_features` to compute per-frame `bass`, `mid`, and `treble` values using `numpy.fft.rfft`, then normalize each band relative to that band's maximum energy across the signal while preserving `rms` and `beat`.

**Key Decisions:** Reused existing frame-window segmentation so all features are aligned per frame; computed one FFT per frame and derived all three bands from the same spectrum; resolved sample rate from audio metadata first, then inferred from sample count and duration when metadata is absent.

**Pitfalls Encountered:** Frequency tests can be unstable if frame windows do not contain integer cycles, so fixture signals were chosen at bin-aligned frequencies for deterministic band separation and normalization assertions.

**Useful Context for Future Agents:** `audio_utils` now supports optional `sample_rate`/`sampling_rate`/`samplerate` in audio dict payloads; when missing, it infers sample rate from `len(audio)/duration`, so keeping duration consistent with source audio length improves spectral mapping accuracy.
