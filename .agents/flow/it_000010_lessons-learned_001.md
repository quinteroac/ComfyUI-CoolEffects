# Lessons Learned — Iteration 000010

## US-001 — Configure Water Drop Parameters

**Summary:** Added a new `CoolWaterDropsEffect` parameter node with six numeric controls (`drop_density`, `drop_size`, `fall_speed`, `refraction_strength`, `gravity`, `wind`) and registered it in the package mappings. The node now emits a valid `EFFECT_PARAMS` payload for `effect_name: "water_drops"`.

**Key Decisions:** Followed the existing effect-node pattern (`importlib` loading of `effect_params.py`, `FUNCTION = "execute"`, and `CATEGORY = "CoolEffects"`). Added `water_drops` defaults to `nodes/effect_params.py` so downstream `merge_params()` usage remains consistent with other effects.

**Pitfalls Encountered:** The injected user-story acceptance criteria were truncated; full parameter ranges/defaults had to be recovered from `.agents/flow/it_000010_product-requirement-document_001.md` before implementing.

**Useful Context for Future Agents:** This story only covers the parameter node contract (US-001), not shader implementation or live preview (US-002/US-003). `__init__.py` already uses `WEB_DIRECTORY` discovery, so no explicit JS extension list update is required for this repository structure.

## US-002 — Live WebGL2 Preview in Node

**Summary:** Added a dedicated `web/water_drops_effect.js` ComfyUI extension that mounts a live WebGL2 preview canvas for `CoolWaterDropsEffect`, applies widget changes to shader uniforms, and added `shaders/glsl/water_drops.frag` plus widget-focused tests.

**Key Decisions:** Reused the shared `mount_effect_node_widget` and `apply_effect_widget_uniform_from_widget` helpers to match existing effect-node patterns and guarantee `requestAnimationFrame` + `u_time` animation behavior comes from the common preview controller.

**Pitfalls Encountered:** The injected acceptance-criteria strings were truncated again, so the full AC text had to be confirmed from `.agents/flow/it_000010_product-requirement-document_001.md` before finalizing test assertions.

**Useful Context for Future Agents:** The story-level tests are in `tests/test_water_drops_effect_widget.py` and directly cover canvas mount, `u_time` animation via rAF, primary parameter uniform sync, and shader lookup by `water_drops`; full-repo pytest still has unrelated pre-existing failures outside this story scope.

## US-003 — Integration with VideoGenerator

**Summary:** Added `CoolVideoGenerator` integration tests for `water_drops` to confirm successful execution, rendering across frames, compatibility with dynamic `effect_params_N` slot positions, and correct post-processing order when chained after VHS.

**Key Decisions:** Reused the existing fake ModernGL harness in `tests/test_video_generator_node.py` and extended it to retain all created contexts so tests can inspect the specific render pass where `water_drops` is applied.

**Pitfalls Encountered:** Acceptance criteria in injected context were truncated, so the complete AC wording was verified from `.agents/flow/it_000010_product-requirement-document_001.md` before mapping assertions.

**Useful Context for Future Agents:** No production code changes were required because `water_drops` was already wired through `DEFAULT_PARAMS`, shader loading, and sequential pass logic; story completion is primarily validated by runtime integration tests in `tests/test_video_generator_node.py`.
