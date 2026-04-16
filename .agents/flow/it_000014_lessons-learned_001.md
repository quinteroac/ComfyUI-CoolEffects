# Lessons Learned — Iteration 000014

## US-001 — Configure text appearance

**Summary:** Added `CoolTextOverlayEffect` with text, font, font size, RGB color, and opacity inputs, including load-time font discovery from `assets/fonts/`. Added pytest coverage for all US-001 acceptance criteria.

**Key Decisions:** Implemented font scanning at module load to enforce immediate validation and deterministic COMBO defaults via case-insensitive alphabetical sorting. Added a bundled default `.ttf` asset (`assets/fonts/dejavu_sans.ttf`) to keep normal module loading functional.

**Pitfalls Encountered:** Repository initially had no `assets/fonts/` directory, which would have caused unconditional import failures once the node module loads. Resolved by adding a default font asset and testing missing/empty directory behavior using isolated temporary module imports.

**Useful Context for Future Agents:** The new tests use a temporary copied module tree so load-time errors can be asserted without mutating repository assets. Future text-overlay stories can extend `nodes/text_overlay_effect.py` without changing this import-time font validation pattern.
