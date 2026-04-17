# Lessons Learned — Iteration 000016

## US-001 — Brightness / Contrast Effect Node

**Summary:** Implemented a new `CoolBrightnessContrastEffect` node with `brightness` and `contrast` FLOAT controls, `EFFECT_PARAMS` output, shared GLSL shader support (`brightness_contrast.frag`), live WebGL2 widget integration, package registration, and automated Python/JS tests covering node contract, shader contract, registration, widget uniform sync, and video-generator pipeline wiring.

**Key Decisions:** Reused the existing per-effect architecture (`nodes/<effect>_effect.py`, `web/<effect>_effect.js`, shared `effect_node_widget.js`) and used an effect key of `brightness_contrast` with uniforms `u_brightness` and `u_contrast`; default behavior uses contrast scale `1.0 + contrast` plus additive brightness so `(0, 0)` is identity.

**Pitfalls Encountered:** Full Python pytest execution is currently blocked in this environment because `torch` is unavailable in the ephemeral test runtime, so repository-wide pytest collection fails before test execution.

**Useful Context for Future Agents:** For new shader effects, the minimum complete wiring is: add node module + register in `__init__.py`, add shader file under `shaders/glsl/`, add defaults in `nodes/effect_params.py` and `web/effect_node_widget.js`, add web extension file for live preview, and add paired Python/JS tests that mirror existing effect test patterns.

## US-002 — HSL (Hue / Saturation / Lightness) Effect Node

**Summary:** Added `CoolHSLEffect` with `hue_shift`, `saturation`, and `lightness` FLOAT controls, `EFFECT_PARAMS` output, GLSL shader implementation (`hsl.frag`), live WebGL2 widget integration (`web/hsl_effect.js`), package registration, and paired Python/JS tests for contract, registration, widget uniform sync, default identity values, and video-generator pipeline wiring.

**Key Decisions:** Reused the existing per-effect architecture with effect key `hsl`; mapped controls to uniforms `u_hue_shift`, `u_saturation`, and `u_lightness`; implemented explicit RGB↔HSL conversion helpers in shader code so default `(0, 0, 0)` path remains identity while allowing bounded additive saturation/lightness edits and wrapped hue rotation.

**Pitfalls Encountered:** The environment still lacks `pytest`, so full Python test execution is not currently runnable here; validation had to rely on JS tests and Python syntax checks.

**Useful Context for Future Agents:** For color-space effects, keep identity defaults in both `nodes/effect_params.py` and `web/effect_node_widget.js` so preview and backend stay aligned, and assert those default identity values directly in node tests to cover “no visible change” acceptance criteria even when visual/manual validation is external.

## US-003 — Color Temperature Effect Node

**Summary:** Added `CoolColorTemperatureEffect` with `temperature` and `tint` FLOAT controls, `EFFECT_PARAMS` output, GLSL shader implementation (`color_temperature.frag`), live WebGL2 preview integration (`web/color_temperature_effect.js`), package registration, and Python/JS tests covering contract, registration, identity defaults, hardened widget uniform handling, and video-generator pipeline wiring.

**Key Decisions:** Followed the existing per-effect architecture using effect key `color_temperature`; mapped controls to uniforms `u_temperature` and `u_tint`; implemented shader bias vectors so positive temperature warms (red/yellow) and negative cools (blue), while tint applies a green↔magenta shift and `(0, 0)` remains an exact identity path.

**Pitfalls Encountered:** `pytest` is still unavailable in this runtime, so Python test execution could not run end-to-end; verification relied on JS test execution and Python compilation checks.

**Useful Context for Future Agents:** For any new effect, keep defaults synchronized across `nodes/effect_params.py`, `web/effect_node_widget.js`, and per-effect param specs, otherwise preview defaults and backend rendering can diverge subtly even when node inputs are unchanged.

## US-004 — Curves (RGB Lift / Gamma / Gain) Effect Node

**Summary:** Added `CoolCurvesEffect` with `lift`, `gamma`, and `gain` FLOAT controls, `EFFECT_PARAMS` output, GLSL shader implementation (`curves.frag`), live WebGL2 preview integration (`web/curves_effect.js`), package registration, synchronized backend/frontend defaults, and Python/JS tests for contract, registration, widget uniform sync, identity defaults, and video-generator pipeline wiring.

**Key Decisions:** Reused the established per-effect architecture with effect key `curves`; mapped controls to uniforms `u_lift`, `u_gamma`, and `u_gain`; implemented shader math as additive lift, gamma power transform, and multiplicative gain with clamped input ranges so defaults `(0, 1, 1)` are an identity path.

**Pitfalls Encountered:** As with prior stories, `pytest` is unavailable in this environment, so Python test execution cannot be run end-to-end here; validation must combine JS tests plus Python syntax checks.

**Useful Context for Future Agents:** For lift/gamma/gain style controls, keep default identities aligned in three places (`nodes/effect_params.py`, `web/effect_node_widget.js`, and per-effect JS param specs) so both WebGL preview initialization and video-render defaults remain behaviorally consistent.

## US-005 — Color Balance Effect Node

**Summary:** Added `CoolColorBalanceEffect` with nine FLOAT controls for shadows/midtones/highlights RGB tinting, `EFFECT_PARAMS` output wiring, a new shared GLSL shader (`color_balance.frag`), live WebGL2 preview extension (`web/color_balance_effect.js`), package registration, synchronized default uniforms, and Python/JS tests for node contract, registration, identity defaults, widget uniform sync, and video-generator pipeline integration.

**Key Decisions:** Followed the established per-effect architecture using effect key `color_balance`; mapped each UI control to explicit channel uniforms (`u_shadows_*`, `u_midtones_*`, `u_highlights_*`); implemented tonal weighting in shader from luma-derived shadows/midtones/highlights masks so split-toning applies predictably while all-zero controls remain an identity path.

**Pitfalls Encountered:** The environment still does not provide a `python` executable (only `python3`), and full pytest remains blocked by missing runtime deps in this environment, so validation needs `python3`-based checks plus JS test execution.

**Useful Context for Future Agents:** For multi-control color effects, keep param/default parity in all three locations (`nodes/effect_params.py`, `web/effect_node_widget.js`, and per-effect `*_PARAM_SPECS`) and assert identity behavior in both node output tests and shader-string contract tests to catch backend/frontend drift early.

## US-006 — Sepia / Black & White / Duotone Effect Node

**Summary:** Added `CoolToneMappingEffect` with `mode` (`none`/`bw`/`sepia`/`duotone`), `intensity`, and duotone shadow/highlight RGB controls; wired full backend/frontend support with new shader (`tone_mapping.frag`), package registration, synchronized default uniforms, live WebGL2 widget extension (`web/tone_mapping_effect.js`), and Python/JS tests for contract, registration, mode mapping, identity behavior, and video-generator pipeline integration.

**Key Decisions:** Implemented tone mapping as effect key `tone_mapping` with numeric `u_mode` values (0..3) so backend and WebGL preview share one uniform contract; built shader behavior as `target_color` selection by mode plus `mix(source, target, intensity)` to guarantee mode `none` is an identity path; added explicit mode-string normalization (`trim().toLowerCase()`) in frontend mapping for resilient widget updates.

**Pitfalls Encountered:** Python `pytest` is still unavailable in this environment (`No module named pytest`), so automated Python test execution could not run here; validation relied on JS tests plus Python compile/smoke checks.

**Useful Context for Future Agents:** For effects with COMBO/string controls, keep the node’s string input and convert to numeric uniforms in both Python (`execute`) and JS (`map_*_to_uniform_value`) so preview updates remain real-time and backend/video rendering stays deterministic; also keep identity defaults aligned in `nodes/effect_params.py`, `web/effect_node_widget.js`, and effect param specs to avoid preview/render drift.
