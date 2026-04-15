# Lessons Learned — Iteration 000012

## US-001 — Per-frame audio feature extraction

**Summary:** Implemented `nodes/audio_utils.py` with `extract_audio_features(audio_tensor, fps, duration)` that returns per-frame audio feature dicts with RMS, beat flag, and bass/mid/treble stubs. Added unit tests covering frame count, dict contract, NumPy-only onset behavior, safe `None` handling, and dependency-safe module imports.

**Key Decisions:** Kept the module pure-NumPy at import/runtime for DSP logic and accepted multiple tensor-like audio payload forms by coercing to mono through duck-typed `detach/cpu/numpy` support. Beat detection uses a causal rolling baseline and local-peak spike criteria to satisfy the no-librosa requirement.

**Pitfalls Encountered:** There is no pre-existing automated Python test harness in this repo, so tests were added via `unittest` without introducing dependencies and designed to run directly with Python discovery.

**Useful Context for Future Agents:** `extract_audio_features` intentionally fixes the dict contract and sets `bass/mid/treble` to `0.0` placeholders; future PRD iterations can replace those values without changing output keys/types. The AC-compliant import safety is enforced by AST-based tests on `nodes/audio_utils.py`.

## US-002 — CoolBeatPulseEffect node

**Summary:** Added `CoolBeatPulseEffect` end to end: backend node class and registration, beat-reactive shader (`beat_pulse.frag`), frontend live preview extension with synthetic 120 BPM pulse when no real audio is attached, and `CoolVideoGenerator` audio-uniform wiring (`u_beat`, `u_rms`) sourced from `extract_audio_features`.

**Key Decisions:** Reused existing importlib/bootstrap and effect-widget patterns for consistency; introduced beat/rms defaults in shared effect params and widget defaults; passed per-frame audio features through `CoolVideoGenerator.execute` into `_render_frames` so audio-reactive uniforms are set centrally for every effect shader that declares them.

**Pitfalls Encountered:** Synthetic pulse preview needed its own lifecycle management to avoid runaway animation handles; modulo normalization had to be corrected so phase stays in `[0,1)` for stable 120 BPM timing.

**Useful Context for Future Agents:** Any future audio-reactive shader can consume `u_beat`/`u_rms` immediately because generator-side uniform plumbing is now generic; for node preview behavior, `web/beat_pulse_effect.js` shows the pattern for continuous synthetic signals layered on top of `mount_effect_node_widget`.
