# Lessons Learned — Iteration 000015

## US-001 — Fisheye Effect Node

**Summary:** Added a new `CoolFisheyeEffect` node with `strength` and `zoom` controls, implemented `shaders/glsl/fisheye.frag` using polar-coordinate UV remapping for barrel distortion, wired a dedicated WebGL2 live-preview extension (`web/fisheye_effect.js`), registered the node in package mappings, and added backend/frontend tests for node contract, shader remapping behavior, preview uniform updates, and generator integration.

**Key Decisions:** Reused the existing `EFFECT_PARAMS` contract (`effect_name = "fisheye"` with `u_strength`/`u_zoom`) and shared `effect_node_widget` preview factory to keep behavior consistent with other effect nodes; implemented fisheye distortion via `(r, theta)` remap (`length` + `atan` then `cos/sin`) so the shader clearly matches the acceptance criterion; added default fisheye uniforms in both backend (`nodes/effect_params.py`) and frontend (`web/effect_node_widget.js`) to keep preview/render defaults aligned.

**Pitfalls Encountered:** Local CLI environment lacked `pytest` and runtime Python deps (including `torch`), so full Python test execution was not possible in-session; used available checks (Node tests + Python compile checks) and kept Python tests aligned with existing repo test patterns.

**Useful Context for Future Agents:** New effect nodes require coordinated updates across five surfaces: node file, shader file, effect defaults (`nodes/effect_params.py`), frontend preview defaults (`web/effect_node_widget.js`), and package registration (`__init__.py`); for slider-driven live preview behavior, exposing a small wrapper helper (`apply_fisheye_uniform_from_widget`) makes Node-based JS tests straightforward and avoids brittle prototype-hook tests.

## US-002 — Pincushion Effect Node

**Summary:** Added `CoolPincushionEffect` with `strength`/`zoom` controls, implemented `shaders/glsl/pincushion.frag` with inverse-barrel remapping, wired a dedicated frontend extension (`web/pincushion_effect.js`) for live WebGL2 preview updates, registered the node in package mappings, and added backend/frontend tests plus video-generator pipeline coverage.

**Key Decisions:** Mirrored the fisheye integration pattern end-to-end so the new effect remains consistent with existing architecture; reused `u_strength` and `u_zoom` uniform names and the shared `effect_node_widget` factory to minimize custom frontend logic; encoded inverse-barrel distortion with `inverse_barrel = max(1.0 - strength * radius * radius, 0.0)` so edge pull-in behavior is explicit and testable.

**Pitfalls Encountered:** This environment has no `python` alias, no `pip` for `python3`, and no installed `torch`, so Python runtime tests could not be executed here; only JS test execution and Python bytecode compilation were available.

**Useful Context for Future Agents:** For any new shader effect, keep backend `DEFAULT_PARAMS` (`nodes/effect_params.py`) and frontend `EFFECT_DEFAULT_UNIFORMS` (`web/effect_node_widget.js`) in sync, otherwise preview defaults and generator defaults drift; the quickest reliable template for new strength/zoom distortions is `fisheye_effect.py/js` + matching test files with only effect key/name differences.
