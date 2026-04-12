# Lessons Learned — Iteration 000002

## US-001 — Effect selection without image input

**Summary:** Updated `CoolEffectSelector` to remove IMAGE input/output and emit only `EFFECT_NAME` as a `STRING`, then aligned node tests and added a selector-to-generator compatibility test.

**Key Decisions:** Kept `effect_name` as the only required selector input so existing dropdown/widget behavior remains intact while changing node wiring to string-only output; validated compatibility by feeding selector output directly into `CoolVideoGenerator.effect_name`.

**Pitfalls Encountered:** Existing test/runtime environment lacked installable Python test dependencies (`pytest`, `numpy`) in this session, so full suite execution was not possible here.

**Useful Context for Future Agents:** `CoolVideoGenerator` now expects a string contract from selector wiring only; `_FakeModerngl.create_standalone_context` in tests should accept keyword args (like `backend`) to mirror current node runtime calls.
