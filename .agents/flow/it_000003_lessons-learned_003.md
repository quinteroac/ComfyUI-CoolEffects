# Lessons Learned — Iteration 000003

## US-001 — CoolGlitchEffect node

**Summary:** Implemented a new `CoolGlitchEffect` node with native FLOAT wave controls, `EFFECT_PARAMS` output contract, package registration, and a dedicated frontend widget extension that mounts a live animated `glitch.frag` preview using a placeholder texture.

**Key Decisions:** Reused the existing preview primitives from `web/effect_selector.js` (`create_live_glsl_preview` and `create_placeholder_texture`) instead of duplicating renderer logic, and added a dedicated `web/glitch_effect.js` extension that only targets `CoolGlitchEffect` node registration.

**Pitfalls Encountered:** Local environment did not have `pip`/`pytest` preinstalled globally, so test execution required a temporary virtual environment; this was kept out of repository changes.

**Useful Context for Future Agents:** The full suite currently contains pre-existing JS widget/loader expectation mismatches unrelated to this story; focused tests for `test_glitch_effect_node.py` and `test_glitch_effect_widget.py` validate US-001 acceptance criteria cleanly.
