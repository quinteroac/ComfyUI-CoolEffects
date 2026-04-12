# Lessons Learned — Iteration 000001

## US-001 — Effect Dropdown

**Summary:** Implemented a new `CoolEffectSelector` node with a dynamic shader dropdown sourced from `shaders/glsl/`, added frontend dropdown controller logic in `web/effect_selector.js`, and added tests covering dropdown population, fast preview updates, and effect-name emission.

**Key Decisions:** Used ComfyUI-native dropdown typing in `INPUT_TYPES` by passing the runtime shader-name list as the `effect_name` input options; kept node registration robust in `__init__.py` via path-based module loading to avoid package-name/import-mode issues; kept frontend behavior testable with pure exported functions for dropdown initialization and change handling.

**Pitfalls Encountered:** The environment does not provide `pytest`/`pip`, so full test-runner execution is unavailable; validation relied on module import/compile smoke checks and direct Node execution of widget behavior paths.

**Useful Context for Future Agents:** This repository’s import-by-file pattern is important for modules under a hyphenated custom-node directory; for frontend behavior tests, a lightweight fake DOM object in Node subprocess tests is sufficient to validate dropdown and event behavior without a browser runtime.

## US-002 — Live GLSL Preview

**Summary:** Added a live preview runtime in `web/effect_selector.js` that builds a canvas-based preview surface, tracks shader uniforms (`u_image`, `u_time`, `u_resolution`), runs a requestAnimationFrame animation loop, handles resize updates, and shows a grey placeholder when no image input is present.

**Key Decisions:** Kept the implementation framework-agnostic but explicitly modeled as an R3F-style preview descriptor (`renderer: "r3f"`, `mesh: "plane"`) so behavior remains testable in Node; integrated preview updates with existing dropdown change handling through `preview_state.preview_controller`.

**Pitfalls Encountered:** `u_resolution` initially stayed at the old dimensions during tests because `clientWidth/clientHeight` were not updated by `resize`; fixed by updating both canvas dimensions and client dimensions before recomputing uniforms.

**Useful Context for Future Agents:** The JS test strategy in this repo relies on fake DOM elements and Node subprocess execution, so exported pure functions/controllers are easier to validate than tightly coupled browser-only widget code; keep widget logic decomposed into testable units.

## US-003 — Node Inputs and Outputs

**Summary:** Kept `CoolEffectSelector` behavior aligned with workflow chaining requirements and added explicit node tests for image input typing, IMAGE + EFFECT_NAME outputs, passthrough execute behavior, registration, and category placement.

**Key Decisions:** Focused changes on test coverage because node implementation already matched the acceptance criteria; asserted metadata directly (`RETURN_TYPES`, `RETURN_NAMES`, `CATEGORY`) to prevent regressions in ComfyUI wiring.

**Pitfalls Encountered:** The environment lacks `pytest`, so full suite execution could not run locally in this session.

**Useful Context for Future Agents:** Existing selector tests already cover registration and execute semantics; when extending selector behavior, keep assertions around class-level ComfyUI contracts since these are the integration surface for downstream nodes.
