# Lessons Learned — Iteration 000010

## US-001 — Configure Frosted Glass Parameters

**Summary:** Added `CoolFrostedGlassEffect` as a new effect-parameter node with five numeric controls (`frost_intensity`, `blur_radius`, `uniformity`, `tint_temperature`, `condensation_rate`) and `EFFECT_PARAMS` output payload for `effect_name: "frosted_glass"`.

**Key Decisions:** Followed the existing effect-node structure (`FUNCTION = "execute"`, `CATEGORY = "CoolEffects"`, `build_effect_params(...)` wiring), registered the node in `__init__.py`, and added default uniforms in `nodes/effect_params.py` to keep merge behavior consistent for future video-generator use.

**Pitfalls Encountered:** Injected acceptance criteria were truncated, so full ranges/defaults and expected payload shape were confirmed from `.agents/flow/it_000010_product-requirement-document_002.md` before implementing tests.

**Useful Context for Future Agents:** This story only covers the parameter-node contract (US-001). Shader implementation and live WebGL2 widget behavior are separate stories in the same PRD (`US-002+`), and `WEB_DIRECTORY = "web"` means frontend files are auto-discovered in this repo.
