# Lessons Learned — Iteration 000002

## US-001 — Effect selection without image input

**Summary:** Updated `CoolEffectSelector` to remove IMAGE input/output and emit only `EFFECT_NAME` as a `STRING`, then aligned node tests and added a selector-to-generator compatibility test.

**Key Decisions:** Kept `effect_name` as the only required selector input so existing dropdown/widget behavior remains intact while changing node wiring to string-only output; validated compatibility by feeding selector output directly into `CoolVideoGenerator.effect_name`.

**Pitfalls Encountered:** Existing test/runtime environment lacked installable Python test dependencies (`pytest`, `numpy`) in this session, so full suite execution was not possible here.

**Useful Context for Future Agents:** `CoolVideoGenerator` now expects a string contract from selector wiring only; `_FakeModerngl.create_standalone_context` in tests should accept keyword args (like `backend`) to mirror current node runtime calls.

## US-002 — Built-in preview placeholder

**Summary:** Updated the effect selector widget to generate and use a JS-only placeholder canvas texture on mount, removed the empty-preview overlay prompt text, and kept the preview canvas transparent while shaders are applied.

**Key Decisions:** Added `create_placeholder_texture(document_ref, size)` in `web/effect_selector.js` so placeholder generation stays frontend-only; wired `mount_effect_selector_widget_for_node` to pass that texture into `create_live_glsl_preview`; kept shader switching logic texture-stable by reusing `u_image` while only replacing fragment shader source.

**Pitfalls Encountered:** The environment lacks `pip`/`pytest` installation capability (no root + system Python restrictions), so full `pytest` execution is still blocked in-session.

**Useful Context for Future Agents:** New widget tests in `tests/test_effect_selector_widget.py` cover placeholder-on-mount, transparent background, removed overlay prompt, and effect-switch texture persistence; these tests use inline Node module execution via Python subprocess and can run once `pytest` is available.
