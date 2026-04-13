# Lessons Learned — Iteration 000003

## US-001 — EFFECT_PARAMS data contract with defaults

**Summary:** Added `nodes/effect_params.py` with the `EFFECT_PARAMS` type string, `DEFAULT_PARAMS` for `glitch`, `vhs`, and `zoom_pulse`, plus `build_effect_params` and `merge_params`. Added `tests/test_effect_params.py` covering contract shape, validation, defaults, merge behavior, and unknown-effect errors.

**Key Decisions:** Reused the exact default numeric values from the iteration PRD for each effect and kept `merge_params` as a direct `{**DEFAULT_PARAMS[effect_name], **params}` merge so unknown effects naturally raise `KeyError`.

**Pitfalls Encountered:** The local environment did not have a system `pytest` command available, so tests were run via the repository-local virtual environment (`.venv/bin/pytest`).

**Useful Context for Future Agents:** The PRD JSON (`.agents/flow/it_000003_PRD_001.json`) already contains the canonical default values for all effect uniforms and is the source of truth when extending `DEFAULT_PARAMS`-driven behavior in later stories.
