# Lessons Learned — Iteration 000003

## US-001 — CoolGlitchEffect node

**Summary:** Implemented a new `CoolGlitchEffect` node with native FLOAT wave controls, `EFFECT_PARAMS` output contract, package registration, and a dedicated frontend widget extension that mounts a live animated `glitch.frag` preview using a placeholder texture.

**Key Decisions:** Reused the existing preview primitives from `web/effect_selector.js` (`create_live_glsl_preview` and `create_placeholder_texture`) instead of duplicating renderer logic, and added a dedicated `web/glitch_effect.js` extension that only targets `CoolGlitchEffect` node registration.

**Pitfalls Encountered:** Local environment did not have `pip`/`pytest` preinstalled globally, so test execution required a temporary virtual environment; this was kept out of repository changes.

**Useful Context for Future Agents:** The full suite currently contains pre-existing JS widget/loader expectation mismatches unrelated to this story; focused tests for `test_glitch_effect_node.py` and `test_glitch_effect_widget.py` validate US-001 acceptance criteria cleanly.

## US-002 — CoolVHSEffect node

**Summary:** Added `CoolVHSEffect` with native VHS parameter controls, `EFFECT_PARAMS` output wiring, package registration, and a dedicated frontend extension that mounts a live animated `vhs.frag` preview using the placeholder texture.

**Key Decisions:** Mirrored the existing `CoolGlitchEffect` backend/frontend patterns for consistency: dynamic loading of `build_effect_params`, matching Comfy node metadata (`CATEGORY`, `RETURN_TYPES`, `RETURN_NAMES`), and a focused `web/vhs_effect.js` extension that only activates for `CoolVHSEffect`.

**Pitfalls Encountered:** The repository-wide pytest suite still contains pre-existing failures in effect selector/web shader loader tests; story validation relied on focused US-001/US-002 node+widget tests to confirm no regressions in the touched surfaces.

**Useful Context for Future Agents:** `web/vhs_effect.js` follows the same test harness contract as `web/glitch_effect.js` (fake DOM canvas + injected shader loader + `preview_descriptor` assertions), so new per-effect widgets can be added quickly by cloning this structure and renaming effect/node/state keys.

## US-003 — CoolZoomPulseEffect node

**Summary:** Implemented `CoolZoomPulseEffect` with pulse amplitude/speed FLOAT controls, `EFFECT_PARAMS` output contract, package registration, and a dedicated frontend widget that mounts a live animated preview for `zoom_pulse.frag` using the placeholder canvas texture.

**Key Decisions:** Followed the existing per-effect architecture used by glitch/vhs nodes: dynamic `effect_params` module loading in Python, explicit node/display registration in `__init__.py`, and a standalone web extension file that reuses `create_live_glsl_preview` + `create_placeholder_texture` from `web/effect_selector.js`.

**Pitfalls Encountered:** Full-suite pytest still reports pre-existing failures in effect selector and web shader loader tests unrelated to US-003 changes; verification was performed with focused node/widget suites covering glitch, vhs, and the new zoom pulse surfaces.

**Useful Context for Future Agents:** For new effect widgets, the most stable test contract is asserting `preview_state.preview_controller.preview_descriptor.effect_name` and shader loader calls in a fake DOM harness; this avoids coupling tests to broader effect selector internals that currently have unrelated drift.
