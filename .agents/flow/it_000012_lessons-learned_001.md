# Lessons Learned — Iteration 000012

## US-001 — Per-frame audio feature extraction

**Summary:** Implemented `nodes/audio_utils.py` with `extract_audio_features(audio_tensor, fps, duration)` that returns per-frame audio feature dicts with RMS, beat flag, and bass/mid/treble stubs. Added unit tests covering frame count, dict contract, NumPy-only onset behavior, safe `None` handling, and dependency-safe module imports.

**Key Decisions:** Kept the module pure-NumPy at import/runtime for DSP logic and accepted multiple tensor-like audio payload forms by coercing to mono through duck-typed `detach/cpu/numpy` support. Beat detection uses a causal rolling baseline and local-peak spike criteria to satisfy the no-librosa requirement.

**Pitfalls Encountered:** There is no pre-existing automated Python test harness in this repo, so tests were added via `unittest` without introducing dependencies and designed to run directly with Python discovery.

**Useful Context for Future Agents:** `extract_audio_features` intentionally fixes the dict contract and sets `bass/mid/treble` to `0.0` placeholders; future PRD iterations can replace those values without changing output keys/types. The AC-compliant import safety is enforced by AST-based tests on `nodes/audio_utils.py`.
