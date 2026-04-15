# Lessons Learned — Iteration 000011

## US-001 — Live canvas preview of text overlay

**Summary:** Implemented a new `CoolTextOverlay` frontend extension (`web/text_overlay_effect.js`) that mounts a canvas preview widget, draws the first decoded frame from the connected VIDEO source, renders single-style or rich inline text fragments on top, rerenders immediately on widget changes, and preserves source aspect ratio while fitting node width.

**Key Decisions:** Cached executed VIDEO outputs by origin node ID so `CoolTextOverlay` can resolve preview sources from connected VIDEO links; used a paused hidden `<video>` element to capture frame 0 and a 2D canvas overlay renderer mirroring node widget controls (`text`, `font_size`, `color`, `pos_x`, `pos_y`, `align`, `opacity`, and fragment JSON).

**Pitfalls Encountered:** Initial Bun coverage for rich fragments had a faulty mock context setup (separate context/call objects), which caused a false negative; fixed by sharing the same mock context and call recorder.

**Useful Context for Future Agents:** The preview extension exports helper functions (`update_preview_layout`, `normalize_overlay_fragments`, `render_overlay_text`, `render_preview_frame`, `patch_preview_widget_callbacks`) that are easy to unit test in Bun without a real browser DOM; for connection-time previews, upstream VIDEO nodes must execute once to seed the executed-output cache.

## US-002 — pretext integration for accurate rich inline layout

**Summary:** Integrated pretext rich-inline measurement into `CoolTextOverlay` preview rendering so fragment widths come from `prepareRichInline()` + `layoutNextRichInlineLineRange()`, with async module loading and rerender caching to keep preview alignment consistent with backend line composition.

**Key Decisions:** Added dynamic pretext import with ordered source fallback (CDN first, bundled vendor module second); kept synchronous canvas fallback while pretext is loading; cached computed widths per normalized fragment-set key on widget state to avoid repeated layout work.

**Pitfalls Encountered:** Fully async width resolution initially made test timing nondeterministic; resolved by adding a synchronous fast path when the pretext module is already cached and preloading module state in the unit test before asserting rendered coordinates.

**Useful Context for Future Agents:** Use `set_pretext_dynamic_import_for_tests()` to inject deterministic loaders in Bun tests; `load_pretext_rich_inline_module()` accepts a custom importer for URL-order assertions; preview x positions will only use measured pretext widths after first measurement for a given fragment set.
