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
