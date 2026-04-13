# Lessons Learned — Iteration 000007

## US-001 — Pan Left shader renders a left-scrolling animation

**Summary:** Added `pan_left.frag` with origin-based wrapped UV panning, registered its defaults in `DEFAULT_PARAMS`, and expanded shader/defaults tests plus shader contract docs.

**Key Decisions:** Implemented left-scroll as `-u_speed * u_time` on X with `fract()` wrapping after applying origin offsets; reused existing shader contract and default-param patterns instead of introducing a new node path.

**Pitfalls Encountered:** Local system Python lacked `pytest`; project tests needed to run through the existing `.venv` interpreter.

**Useful Context for Future Agents:** `tests/test_initial_shaders.py` is the central contract test for required uniforms, compile checks, and shader README coverage—new shaders should be added there along with `DEFAULT_PARAMS` in `nodes/effect_params.py`.

## US-002 — Pan Right shader renders a right-scrolling animation

**Summary:** Added `pan_right.frag` with wrapped +X scrolling from configurable origins, registered `pan_right` defaults in `DEFAULT_PARAMS`, and expanded shader contract tests/docs coverage for the new effect.

**Key Decisions:** Mirrored the established `pan_left` structure and changed only scroll direction (`u_speed * u_time` on X) to keep behavior predictable and consistent with existing shader conventions.

**Pitfalls Encountered:** Existing full-suite baseline failures are unrelated to this story (`tests/test_effect_selector_widget.py`), so validation focused on shader/default-param tests tied to the acceptance criteria.

**Useful Context for Future Agents:** For additional shaders in this PRD series, update `tests/test_initial_shaders.py` (`EXPECTED_SHADERS`, directional formula assertions, README assertions) and `tests/test_effect_params.py` together to keep contract and default coverage aligned.
