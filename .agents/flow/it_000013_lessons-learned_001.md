# Lessons Learned — Iteration 000013

## US-001 — Nodo Zoom In

**Summary:** Implemented a new `CoolZoomInEffect` node that outputs `EFFECT_PARAMS`, added a dedicated `zoom_in` fragment shader, registered backend/frontend integration, and connected live WebGL2 preview updates via widget-driven uniforms.

**Key Decisions:** Reused the shared `effect_node_widget` factory to keep preview behavior consistent; introduced `zoom_strength` + `zoom_speed` controls with matching defaults in both Python (`DEFAULT_PARAMS`) and frontend (`EFFECT_DEFAULT_UNIFORMS`) to ensure parity between preview and render pipeline.

**Pitfalls Encountered:** Running `compileall` updated tracked `__pycache__` artifacts in the repo; these need cleanup after local validation to avoid unrelated diffs.

**Useful Context for Future Agents:** For new effect nodes, minimum end-to-end wiring is: node file + shader file + frontend extension + `__init__.py` registration + `effect_params.py` defaults + `web/effect_node_widget.js` defaults. `CoolVideoGenerator` picks new effects automatically once `effect_name` defaults exist and shader is available.
