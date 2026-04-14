# Lessons Learned — Iteration 000010

## US-001 — Configure Water Drop Parameters

**Summary:** Added a new `CoolWaterDropsEffect` parameter node with six numeric controls (`drop_density`, `drop_size`, `fall_speed`, `refraction_strength`, `gravity`, `wind`) and registered it in the package mappings. The node now emits a valid `EFFECT_PARAMS` payload for `effect_name: "water_drops"`.

**Key Decisions:** Followed the existing effect-node pattern (`importlib` loading of `effect_params.py`, `FUNCTION = "execute"`, and `CATEGORY = "CoolEffects"`). Added `water_drops` defaults to `nodes/effect_params.py` so downstream `merge_params()` usage remains consistent with other effects.

**Pitfalls Encountered:** The injected user-story acceptance criteria were truncated; full parameter ranges/defaults had to be recovered from `.agents/flow/it_000010_product-requirement-document_001.md` before implementing.

**Useful Context for Future Agents:** This story only covers the parameter node contract (US-001), not shader implementation or live preview (US-002/US-003). `__init__.py` already uses `WEB_DIRECTORY` discovery, so no explicit JS extension list update is required for this repository structure.
