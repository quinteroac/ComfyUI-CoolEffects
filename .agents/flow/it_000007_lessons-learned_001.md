# Lessons Learned — Iteration 000007

## US-001 — Pan Left shader renders a left-scrolling animation

**Summary:** Added `pan_left.frag` with origin-based wrapped UV panning, registered its defaults in `DEFAULT_PARAMS`, and expanded shader/defaults tests plus shader contract docs.

**Key Decisions:** Implemented left-scroll as `-u_speed * u_time` on X with `fract()` wrapping after applying origin offsets; reused existing shader contract and default-param patterns instead of introducing a new node path.

**Pitfalls Encountered:** Local system Python lacked `pytest`; project tests needed to run through the existing `.venv` interpreter.

**Useful Context for Future Agents:** `tests/test_initial_shaders.py` is the central contract test for required uniforms, compile checks, and shader README coverage—new shaders should be added there along with `DEFAULT_PARAMS` in `nodes/effect_params.py`.
