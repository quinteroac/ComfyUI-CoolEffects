# Lessons Learned — Iteration 000003

## US-001 — Accept EFFECT_PARAMS input

**Summary:** Updated `CoolVideoGenerator` to require `effect_params` of type `EFFECT_PARAMS`, removed the `EFFECT_NAME` string input, and changed `execute` to `execute(self, image, effect_params, fps, duration)`. Added/updated tests to assert the new input contract and signature.

**Key Decisions:** Added a small `_extract_effect_name` validator in `nodes/video_generator.py` so shader lookup still uses a validated `effect_params["effect_name"]` value while keeping the rest of the rendering pipeline unchanged.

**Pitfalls Encountered:** Runtime test environments may not have `torch`/`numpy` available, which can skip or block import-based node tests.

**Useful Context for Future Agents:** For contract-only acceptance criteria on dependency-heavy nodes, AST-based tests (like `tests/test_video_generator_effect_params_contract.py`) provide stable coverage without requiring GPU/runtime Python deps.

## US-002 — Default param merging

**Summary:** Updated `CoolVideoGenerator.execute` to merge incoming `effect_params["params"]` with per-effect defaults via `merge_params(effect_params["effect_name"], effect_params["params"])`, then apply the merged uniforms before rendering.

**Key Decisions:** Loaded `merge_params` from `nodes/effect_params.py` using the same importlib-by-path pattern as shader loader imports so tests and runtime path loading remain consistent.

**Pitfalls Encountered:** Existing fake shader program tests only defined base uniforms (`u_image`, `u_time`, `u_resolution`); dynamic uniform lookups had to be supported in the test fake to validate merged uniform assignment.

**Useful Context for Future Agents:** Unknown effect handling now occurs before shader file loading and raises `ValueError` from the merge step, so shader-missing tests should use a known effect name to isolate `load_shader` error behavior.
