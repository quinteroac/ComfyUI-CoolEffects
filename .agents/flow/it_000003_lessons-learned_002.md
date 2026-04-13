# Lessons Learned — Iteration 000003

## US-001 — Accept EFFECT_PARAMS input

**Summary:** Updated `CoolVideoGenerator` to require `effect_params` of type `EFFECT_PARAMS`, removed the `EFFECT_NAME` string input, and changed `execute` to `execute(self, image, effect_params, fps, duration)`. Added/updated tests to assert the new input contract and signature.

**Key Decisions:** Added a small `_extract_effect_name` validator in `nodes/video_generator.py` so shader lookup still uses a validated `effect_params["effect_name"]` value while keeping the rest of the rendering pipeline unchanged.

**Pitfalls Encountered:** Runtime test environments may not have `torch`/`numpy` available, which can skip or block import-based node tests.

**Useful Context for Future Agents:** For contract-only acceptance criteria on dependency-heavy nodes, AST-based tests (like `tests/test_video_generator_effect_params_contract.py`) provide stable coverage without requiring GPU/runtime Python deps.
