# Lessons Learned — Iteration 000013

## US-001 — Nodo Zoom In

**Summary:** Implemented a new `CoolZoomInEffect` node that outputs `EFFECT_PARAMS`, added a dedicated `zoom_in` fragment shader, registered backend/frontend integration, and connected live WebGL2 preview updates via widget-driven uniforms.

**Key Decisions:** Reused the shared `effect_node_widget` factory to keep preview behavior consistent; introduced `zoom_strength` + `zoom_speed` controls with matching defaults in both Python (`DEFAULT_PARAMS`) and frontend (`EFFECT_DEFAULT_UNIFORMS`) to ensure parity between preview and render pipeline.

**Pitfalls Encountered:** Running `compileall` updated tracked `__pycache__` artifacts in the repo; these need cleanup after local validation to avoid unrelated diffs.

**Useful Context for Future Agents:** For new effect nodes, minimum end-to-end wiring is: node file + shader file + frontend extension + `__init__.py` registration + `effect_params.py` defaults + `web/effect_node_widget.js` defaults. `CoolVideoGenerator` picks new effects automatically once `effect_name` defaults exist and shader is available.

## US-002 — Nodo Zoom Out

**Summary:** Added a new `CoolZoomOutEffect` node that emits `EFFECT_PARAMS` with editable `zoom_strength`/`zoom_speed`, created `zoom_out.frag`, wired frontend live preview with a dedicated extension, and registered backend/UI mappings so the effect is available end-to-end (including `CoolVideoGenerator`).

**Key Decisions:** Reused the same parameter names/uniform contract as `zoom_in` (`u_zoom_strength`, `u_zoom_speed`) to keep node UX and rendering pipeline consistent; clamped zoom-out scale in shader (`>= 0.05`) to prevent invalid sampling and runtime instability at high parameter values.

**Pitfalls Encountered:** None significant; the main requirement was to update both backend and frontend default uniform maps so preview defaults and render defaults stay in sync.

**Useful Context for Future Agents:** For any new effect, if preview appears static or inconsistent with render output, first compare `nodes/effect_params.py` defaults against `web/effect_node_widget.js` defaults; mismatches there are the most common source of confusion.
