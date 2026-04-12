# Lessons Learned — Iteration 000001

## US-001 — Effect Dropdown

**Summary:** Implemented a new `CoolEffectSelector` node with a dynamic shader dropdown sourced from `shaders/glsl/`, added frontend dropdown controller logic in `web/effect_selector.js`, and added tests covering dropdown population, fast preview updates, and effect-name emission.

**Key Decisions:** Used ComfyUI-native dropdown typing in `INPUT_TYPES` by passing the runtime shader-name list as the `effect_name` input options; kept node registration robust in `__init__.py` via path-based module loading to avoid package-name/import-mode issues; kept frontend behavior testable with pure exported functions for dropdown initialization and change handling.

**Pitfalls Encountered:** The environment does not provide `pytest`/`pip`, so full test-runner execution is unavailable; validation relied on module import/compile smoke checks and direct Node execution of widget behavior paths.

**Useful Context for Future Agents:** This repository’s import-by-file pattern is important for modules under a hyphenated custom-node directory; for frontend behavior tests, a lightweight fake DOM object in Node subprocess tests is sufficient to validate dropdown and event behavior without a browser runtime.
