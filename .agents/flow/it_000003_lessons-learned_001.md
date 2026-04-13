# Lessons Learned — Iteration 000003

## US-001 — EFFECT_PARAMS data contract with defaults

**Summary:** Added `nodes/effect_params.py` with the `EFFECT_PARAMS` type string, `DEFAULT_PARAMS` for `glitch`, `vhs`, and `zoom_pulse`, plus `build_effect_params` and `merge_params`. Added `tests/test_effect_params.py` covering contract shape, validation, defaults, merge behavior, and unknown-effect errors.

**Key Decisions:** Reused the exact default numeric values from the iteration PRD for each effect and kept `merge_params` as a direct `{**DEFAULT_PARAMS[effect_name], **params}` merge so unknown effects naturally raise `KeyError`.

**Pitfalls Encountered:** The local environment did not have a system `pytest` command available, so tests were run via the repository-local virtual environment (`.venv/bin/pytest`).

**Useful Context for Future Agents:** The PRD JSON (`.agents/flow/it_000003_PRD_001.json`) already contains the canonical default values for all effect uniforms and is the source of truth when extending `DEFAULT_PARAMS`-driven behavior in later stories.

## US-002 — Glitch shader per-effect uniforms

**Summary:** Updated `shaders/glsl/glitch.frag` to replace the hardcoded wave constants with `u_wave_freq`, `u_wave_amp`, and `u_speed`, and added focused tests in `tests/test_initial_shaders.py` to verify declaration, formula usage, and removal of old hardcoded wave constants.

**Key Decisions:** Kept the existing glitch wave expression structure intact and only parameterized frequency, amplitude, and speed so default values (`120.0`, `0.0025`, `10.0`) produce the same behavior when provided at runtime.

**Pitfalls Encountered:** Full-suite baseline currently includes unrelated pre-existing JS/widget test failures, so verification for this story was performed with targeted shader tests.

**Useful Context for Future Agents:** `tests/test_initial_shaders.py` is the current place for shader-contract checks; add effect-specific uniform assertions there to keep coverage centralized with loader-based source reads.

## US-003 — VHS shader per-effect uniforms

**Summary:** Updated `shaders/glsl/vhs.frag` to replace scanline intensity, jitter amount, and chroma shift hardcoded values with `u_scanline_intensity`, `u_jitter_amount`, and `u_chroma_shift` uniforms. Added focused VHS assertions in `tests/test_initial_shaders.py`.

**Key Decisions:** Preserved the existing VHS math and only parameterized the three effect-tuning values so rendering remains equivalent when defaults are supplied (`0.04`, `0.0018`, `0.002`).

**Pitfalls Encountered:** The local runtime did not initially provide a `pytest` executable in `PATH`, so test execution needed to use an installed module form.

**Useful Context for Future Agents:** Keep effect-uniform regression checks in `tests/test_initial_shaders.py`; this file already centralizes shader contract checks and is loaded through `shaders/loader.py`, matching runtime behavior.
