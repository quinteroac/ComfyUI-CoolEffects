# Lessons Learned — Iteration 000014

## US-001 — Configure text appearance

**Summary:** Added `CoolTextOverlayEffect` with text, font, font size, RGB color, and opacity inputs, including load-time font discovery from `assets/fonts/`. Added pytest coverage for all US-001 acceptance criteria.

**Key Decisions:** Implemented font scanning at module load to enforce immediate validation and deterministic COMBO defaults via case-insensitive alphabetical sorting. Added a bundled default `.ttf` asset (`assets/fonts/dejavu_sans.ttf`) to keep normal module loading functional.

**Pitfalls Encountered:** Repository initially had no `assets/fonts/` directory, which would have caused unconditional import failures once the node module loads. Resolved by adding a default font asset and testing missing/empty directory behavior using isolated temporary module imports.

**Useful Context for Future Agents:** The new tests use a temporary copied module tree so load-time errors can be asserted without mutating repository assets. Future text-overlay stories can extend `nodes/text_overlay_effect.py` without changing this import-time font validation pattern.

## US-002 — Position text on the image

**Summary:** Added text-position controls to `CoolTextOverlayEffect` (`position`, `offset_x`, `offset_y`) and wired them into `execute()` output params. Implemented `web/text_overlay_effect.js` plus `shaders/glsl/text_overlay.frag` so anchor selection updates the live WebGL2 preview.

**Key Decisions:** Represented placement as discrete anchor coordinates (`u_anchor_x`, `u_anchor_y`) derived from the COMBO value, then applied fine-grained nudging through separate `u_offset_x` and `u_offset_y` uniforms. Exposed pure helper exports in the JS extension (`map_position_to_anchor`, `apply_text_overlay_position`) to make preview behavior directly testable.

**Pitfalls Encountered:** The repository had no existing text-overlay frontend extension or shader, so preview AC coverage required adding both in this story rather than only tweaking Python inputs.

**Useful Context for Future Agents:** `effect_node_widget.js` only auto-applies numeric widget uniforms, so COMBO widgets like `position` must be handled explicitly in `onWidgetChanged`. The text-overlay preview currently renders a text-block proxy rectangle; future stories can swap this for a true text texture path while keeping the anchor/offset uniform contract.
