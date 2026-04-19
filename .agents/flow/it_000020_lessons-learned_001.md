# Lessons Learned — Iteration 000020

## US-001 — Pixelate / Mosaic Effect Node

**Summary:** Implemented `CoolPixelateEffect` end-to-end with backend node registration, shared defaults, a new `pixelate.frag` shader, frontend live-preview extension wiring, and Python/JS tests validating node inputs, payload contract, shader uniform contract, registration, and video-generator chaining.

**Key Decisions:** Reused the existing per-effect node/widget architecture exactly (importlib-based node module loading, `build_effect_params` payload shape, and `mount_effect_node_widget` frontend helper). Used `u_pixel_size` + `u_aspect_ratio` uniforms to compute per-fragment block sampling so `pixel_size=1` behaves as identity while larger values create mosaic blocks and non-1.0 aspect creates rectangular pixels.

**Pitfalls Encountered:** Full baseline Python suite has one pre-existing failure unrelated to this story (`tests/test_video_mixer_node.py::test_video_mixer_assembles_video_from_components_with_mixed_frames_and_audio` transition-duration validation). Targeted and contract-relevant checks pass for the pixelate implementation.

**Useful Context for Future Agents:** To add future effects quickly, mirror `nodes/<effect>_effect.py`, `web/<effect>_effect.js`, `shaders/glsl/<effect>.frag`, add defaults in `nodes/effect_params.py`, extend `EFFECT_DEFAULT_UNIFORMS` in `web/effect_node_widget.js`, then wire class/display + module loading in `__init__.py` and add paired `tests/test_<effect>_effect_node.py` + `tests/test_<effect>_effect_web.mjs`.
