# Lessons Learned — Iteration 000020

## US-001 — Pixelate / Mosaic Effect Node

**Summary:** Implemented `CoolPixelateEffect` end-to-end with backend node registration, shared defaults, a new `pixelate.frag` shader, frontend live-preview extension wiring, and Python/JS tests validating node inputs, payload contract, shader uniform contract, registration, and video-generator chaining.

**Key Decisions:** Reused the existing per-effect node/widget architecture exactly (importlib-based node module loading, `build_effect_params` payload shape, and `mount_effect_node_widget` frontend helper). Used `u_pixel_size` + `u_aspect_ratio` uniforms to compute per-fragment block sampling so `pixel_size=1` behaves as identity while larger values create mosaic blocks and non-1.0 aspect creates rectangular pixels.

**Pitfalls Encountered:** Full baseline Python suite has one pre-existing failure unrelated to this story (`tests/test_video_mixer_node.py::test_video_mixer_assembles_video_from_components_with_mixed_frames_and_audio` transition-duration validation). Targeted and contract-relevant checks pass for the pixelate implementation.

**Useful Context for Future Agents:** To add future effects quickly, mirror `nodes/<effect>_effect.py`, `web/<effect>_effect.js`, `shaders/glsl/<effect>.frag`, add defaults in `nodes/effect_params.py`, extend `EFFECT_DEFAULT_UNIFORMS` in `web/effect_node_widget.js`, then wire class/display + module loading in `__init__.py` and add paired `tests/test_<effect>_effect_node.py` + `tests/test_<effect>_effect_web.mjs`.

## US-002 — Dithering Effect Node

**Summary:** Implemented `CoolDitheringEffect` with backend node inputs/output contract, package registration, shared default uniforms, `dithering.frag` shader (8×8 Bayer ordered dither), frontend live-preview extension wiring, and Python/JS coverage for node contract, shader contract, registration, and video-generator chaining.

**Key Decisions:** Followed the established per-effect architecture used by prior effects to minimize risk and keep consistency. Implemented Bayer logic directly in GLSL via a static 64-value matrix and used `dither_scale`, `threshold`, and `palette_size` as runtime uniforms so both preview and render paths share identical behavior.

**Pitfalls Encountered:** Python test execution is currently blocked in this environment because `pytest` is not installed (`python3 -m pytest` fails before test discovery). JS test execution remains available and was used for frontend verification.

**Useful Context for Future Agents:** For future ordered/quantization effects, keep the uniform naming consistent (`u_*`) and add matching defaults in both `nodes/effect_params.py` and `web/effect_node_widget.js`; this keeps preview initialization and backend merge behavior aligned without extra wiring.

## US-003 — Color Quantization Effect Node

**Summary:** Implemented `CoolColorQuantizationEffect` end-to-end with backend node contract, package registration, default uniform registry entries, `color_quantization.frag` shader, frontend WebGL2 live-preview extension wiring, and Python/JS tests covering inputs, payload, shader contract, registration, and video-generator chaining.

**Key Decisions:** Kept the implementation fully aligned with the existing per-effect architecture (`build_effect_params`, `mount_effect_node_widget`, importlib-based node loading in `__init__.py`) and used per-channel uniforms (`u_levels_r/g/b`) so each channel quantizes independently while keeping the shared shader uniform contract.

**Pitfalls Encountered:** Full Python suite still has the known unrelated baseline failure in `tests/test_video_mixer_node.py::test_video_mixer_assembles_video_from_components_with_mixed_frames_and_audio`; targeted story-specific Python and JS checks pass.

**Useful Context for Future Agents:** For RGB-channel effects, mirror both defaults registries (`nodes/effect_params.py` and `web/effect_node_widget.js`) and validate shader formula strings in node tests; this catches backend/frontend drift early and keeps preview/render semantics consistent.
