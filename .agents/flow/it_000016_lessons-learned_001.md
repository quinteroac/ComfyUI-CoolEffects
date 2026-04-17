# Lessons Learned — Iteration 000016

## US-001 — Brightness / Contrast Effect Node

**Summary:** Implemented a new `CoolBrightnessContrastEffect` node with `brightness` and `contrast` FLOAT controls, `EFFECT_PARAMS` output, shared GLSL shader support (`brightness_contrast.frag`), live WebGL2 widget integration, package registration, and automated Python/JS tests covering node contract, shader contract, registration, widget uniform sync, and video-generator pipeline wiring.

**Key Decisions:** Reused the existing per-effect architecture (`nodes/<effect>_effect.py`, `web/<effect>_effect.js`, shared `effect_node_widget.js`) and used an effect key of `brightness_contrast` with uniforms `u_brightness` and `u_contrast`; default behavior uses contrast scale `1.0 + contrast` plus additive brightness so `(0, 0)` is identity.

**Pitfalls Encountered:** Full Python pytest execution is currently blocked in this environment because `torch` is unavailable in the ephemeral test runtime, so repository-wide pytest collection fails before test execution.

**Useful Context for Future Agents:** For new shader effects, the minimum complete wiring is: add node module + register in `__init__.py`, add shader file under `shaders/glsl/`, add defaults in `nodes/effect_params.py` and `web/effect_node_widget.js`, add web extension file for live preview, and add paired Python/JS tests that mirror existing effect test patterns.
