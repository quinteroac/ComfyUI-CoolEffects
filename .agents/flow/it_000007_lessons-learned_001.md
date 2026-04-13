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

## US-003 — Pan Up shader renders a bottom-to-top scrolling animation

**Summary:** Added `pan_up.frag` with wrapped upward UV scrolling from configurable origins, registered `pan_up` in `DEFAULT_PARAMS`, and expanded shader contract/default tests plus shader README coverage.

**Key Decisions:** Reused the same panning structure from `pan_left`/`pan_right` and only changed scroll direction to `+Y` via `vec2(0.0, u_speed * u_time)` with `fract(origin_uv + scroll_offset)` for wrap behavior.

**Pitfalls Encountered:** Existing unrelated widget/JS loader tests still fail in baseline; validation remained focused on shader/default tests tied to this story's acceptance criteria.

**Useful Context for Future Agents:** For the pan-family shaders, keep `u_speed`, `u_origin_x`, `u_origin_y` uniform/default contracts identical and change only the directional scroll vector to avoid behavioral drift.

## US-004 — Pan Down shader renders a top-to-bottom scrolling animation

**Summary:** Added `pan_down.frag` with wrapped downward UV scrolling, registered `pan_down` defaults in `DEFAULT_PARAMS`, and extended shader/default/readme tests to include the new effect.

**Key Decisions:** Followed the existing pan-family structure and implemented down-scroll as a negative Y time offset (`vec2(0.0, -u_speed * u_time)`) while preserving origin offset and `fract()` wrapping.

**Pitfalls Encountered:** None beyond ensuring all pan-family contract assertions remained synchronized when expanding expected shader lists and README coverage counts.

**Useful Context for Future Agents:** The `EXPECTED_SHADERS` tuple in `tests/test_initial_shaders.py` drives file-existence and compile checks; whenever adding a shader, update that tuple and the README contract assertions in the same change.
