# Lessons Learned — Iteration 000011

## US-001 — Single-style text overlay on video

**Summary:** Added a new `CoolTextOverlay` backend node that reads VIDEO frames, renders Pillow text overlays on every frame with style/position/alignment/opacity controls, and returns a rebuilt VIDEO while preserving frame rate and audio metadata.

**Key Decisions:** Reused the existing `comfy_api.latest` `VideoFromComponents` output pattern for VIDEO compatibility; implemented anchor-based alignment math (`left`/`center`/`right`) using measured text width; used RGBA layer composition plus `Image.paste` mask scaling for opacity blending.

**Pitfalls Encountered:** Font availability differs across environments, so tests were made deterministic by monkeypatching the node’s font loader to `ImageFont.load_default()`; this prevents environment-dependent failures while still verifying placement and blending behavior.

**Useful Context for Future Agents:** The new node is registered directly in `__init__.py` (no optional dependency gate). Tests in `tests/test_text_overlay_effect_node.py` already cover all US-001 acceptance criteria and can be extended for US-002/US-003 by building on the fragment parsing and font-loading helpers.

## US-002 — Rich inline multi-fragment text overlay

**Summary:** Extended `CoolTextOverlay` to support rendering a JSON fragment array where each fragment can carry its own text style (`font_family`, `font_size`, `color`, `font_weight`) while preserving single-line positioning controls (`pos_x`, `pos_y`, `align`) for the composed line.

**Key Decisions:** Added strict fragment normalization/validation helpers (`_parse_fragments`, `_normalize_fragments`); retained node-level text/style as defaults when fragment style keys are omitted; switched rendering from single-string draw to per-fragment sequential draw with a shared baseline and line-level alignment math.

**Pitfalls Encountered:** Pillow font objects vary by environment, so baseline calculations needed a fallback when `getmetrics()` is unavailable; color assertions in tests were written with channel thresholds (instead of exact values) to avoid anti-aliasing noise.

**Useful Context for Future Agents:** Fragment JSON errors now raise clear `ValueError` messages (`fragments must be valid JSON...`); tests in `tests/test_text_overlay_effect_node.py` now include fragment default fallback, invalid JSON handling, left-to-right composed-line layout, and per-fragment color rendering checks.
