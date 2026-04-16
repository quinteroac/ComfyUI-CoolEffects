# Lessons Learned — Iteration 000015

## US-001 — Fisheye Effect Node

**Summary:** Added a new `CoolFisheyeEffect` node with `strength` and `zoom` controls, implemented `shaders/glsl/fisheye.frag` using polar-coordinate UV remapping for barrel distortion, wired a dedicated WebGL2 live-preview extension (`web/fisheye_effect.js`), registered the node in package mappings, and added backend/frontend tests for node contract, shader remapping behavior, preview uniform updates, and generator integration.

**Key Decisions:** Reused the existing `EFFECT_PARAMS` contract (`effect_name = "fisheye"` with `u_strength`/`u_zoom`) and shared `effect_node_widget` preview factory to keep behavior consistent with other effect nodes; implemented fisheye distortion via `(r, theta)` remap (`length` + `atan` then `cos/sin`) so the shader clearly matches the acceptance criterion; added default fisheye uniforms in both backend (`nodes/effect_params.py`) and frontend (`web/effect_node_widget.js`) to keep preview/render defaults aligned.

**Pitfalls Encountered:** Local CLI environment lacked `pytest` and runtime Python deps (including `torch`), so full Python test execution was not possible in-session; used available checks (Node tests + Python compile checks) and kept Python tests aligned with existing repo test patterns.

**Useful Context for Future Agents:** New effect nodes require coordinated updates across five surfaces: node file, shader file, effect defaults (`nodes/effect_params.py`), frontend preview defaults (`web/effect_node_widget.js`), and package registration (`__init__.py`); for slider-driven live preview behavior, exposing a small wrapper helper (`apply_fisheye_uniform_from_widget`) makes Node-based JS tests straightforward and avoids brittle prototype-hook tests.
