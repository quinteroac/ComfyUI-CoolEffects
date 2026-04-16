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

## US-003 — Nodo Dolly In

**Summary:** Implemented `CoolDollyInEffect` end-to-end with new backend node inputs (`dolly_strength`, `dolly_speed`, `focus_x`, `focus_y`), a dedicated `dolly_in` fragment shader, frontend live WebGL2 preview wiring, and registration/documentation updates.

**Key Decisions:** Reused the shared `effect_node_widget` flow (same as other effect nodes) and added matching defaults in both `nodes/effect_params.py` and `web/effect_node_widget.js` so preview and video rendering stay aligned through `merge_params()`.

**Pitfalls Encountered:** Python smoke checks can create noisy tracked/untracked `__pycache__` artifacts in this repo; they need cleanup before handing off changes.

**Useful Context for Future Agents:** `CoolVideoGenerator` required no code changes for new effects—once `effect_name` is `"dolly_in"` and the shader/defaults are present, it renders automatically via dynamic shader loading and merged uniform params.

## US-004 — Nodo Dolly Out

**Summary:** Implemented `CoolDollyOutEffect` end-to-end with editable `dolly_strength`, `dolly_speed`, `focus_x`, and `focus_y`, plus dedicated shader/frontend preview wiring and node registration updates.

**Key Decisions:** Kept Dolly Out uniform names aligned with Dolly In (`u_dolly_strength`, `u_dolly_speed`, `u_focus_x`, `u_focus_y`) and only inverted shader scale progression so both effects share a consistent parameter UX while producing opposite camera movement.

**Pitfalls Encountered:** None significant; the critical requirement was ensuring `dolly_out` defaults were added in both backend (`nodes/effect_params.py`) and frontend (`web/effect_node_widget.js`) to avoid preview/render mismatches.

**Useful Context for Future Agents:** For paired inverse effects, preserve the same parameter schema and implement inversion inside GLSL math; this keeps node widgets and Video Generator integration simple because `CoolVideoGenerator` already resolves effect names dynamically via shared shader loading.

## US-005 — Compatibilidad end-to-end con Video Generator

**Summary:** Updated `CoolVideoGenerator` to expose all backend `effect_params_1`…`effect_params_8` optional inputs (not only `effect_params_1`), then added regression tests covering slot acceptance, Zoom+Dolly sequential execution, and `CoolVideoPlayer` compatibility of generated VIDEO payloads.

**Key Decisions:** Declared all eight `effect_params_N` inputs directly in `INPUT_TYPES` to match the frontend dynamic slot behavior and ensure non-UI/runtime paths (workflow JSON/API execution) can validate and use any slot consistently.

**Pitfalls Encountered:** Existing code already iterated `effect_params_1..effect_count` from `kwargs`, so the real gap was input declaration rather than render logic; focusing on INPUT_TYPES avoided unnecessary changes in the rendering pipeline.

**Useful Context for Future Agents:** For `CoolVideoGenerator`, frontend dynamic slots in `web/video_generator.js` are not sufficient alone; backend `INPUT_TYPES` must declare every slot needed for type validation and reliable workflow loading/execution.
