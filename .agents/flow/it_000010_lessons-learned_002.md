# Lessons Learned — Iteration 000010

## US-001 — Configure Frosted Glass Parameters

**Summary:** Added `CoolFrostedGlassEffect` as a new effect-parameter node with five numeric controls (`frost_intensity`, `blur_radius`, `uniformity`, `tint_temperature`, `condensation_rate`) and `EFFECT_PARAMS` output payload for `effect_name: "frosted_glass"`.

**Key Decisions:** Followed the existing effect-node structure (`FUNCTION = "execute"`, `CATEGORY = "CoolEffects"`, `build_effect_params(...)` wiring), registered the node in `__init__.py`, and added default uniforms in `nodes/effect_params.py` to keep merge behavior consistent for future video-generator use.

**Pitfalls Encountered:** Injected acceptance criteria were truncated, so full ranges/defaults and expected payload shape were confirmed from `.agents/flow/it_000010_product-requirement-document_002.md` before implementing tests.

**Useful Context for Future Agents:** This story only covers the parameter-node contract (US-001). Shader implementation and live WebGL2 widget behavior are separate stories in the same PRD (`US-002+`), and `WEB_DIRECTORY = "web"` means frontend files are auto-discovered in this repo.

## US-002 — Live WebGL2 Preview in Node

**Summary:** Added a dedicated `web/frosted_glass_effect.js` extension that mounts a live canvas preview for `CoolFrostedGlassEffect`, wired all five node widgets to uniforms, and introduced the `shaders/glsl/frosted_glass.frag` shader used by that preview.

**Key Decisions:** Reused the shared `mount_effect_node_widget` + `apply_effect_widget_uniform_from_widget` factory pattern (matching existing effect nodes), added frosted-glass defaults into `web/effect_node_widget.js` for consistent preview initialization, and kept shader loading through `loadShader(...)` so preview source always comes from `/cool_effects/shaders/{name}`.

**Pitfalls Encountered:** The acceptance-criteria text in injected context was truncated, so the full PRD artifact was used to confirm AC wording (especially animation and shader-fetch requirements). Also avoided committing generated `__pycache__` artifacts from local test runs.

**Useful Context for Future Agents:** Widget tests run via Node-based module execution in pytest (`node --input-type=module -e ...`) and can directly assert `shader_loader` call names, `u_time` animation progression, and uniform updates from `onWidgetChanged`, which is the fastest way to validate ComfyUI extension behavior without a browser harness.

## US-003 — Integration with VideoGenerator

**Summary:** Added integration-focused `CoolVideoGenerator` tests for `frosted_glass` to verify single-slot execution, any-slot wiring (`effect_params_1`, `effect_params_3`, `effect_params_8`), and ordered composition when chained after `water_drops`.

**Key Decisions:** Reused the existing fake ModernGL harness in `tests/test_video_generator_node.py` instead of adding new test infrastructure, and mirrored established water-drops integration patterns so frosted-glass coverage stays consistent with existing effect behavior checks.

**Pitfalls Encountered:** The injected acceptance criteria were truncated, so the full PRD file was referenced to confirm complete AC wording before implementing tests.

**Useful Context for Future Agents:** The fake framebuffer returns deterministic per-pass bytes (`bytes([frame_index])`), which makes composition-order assertions reliable by checking second-pass texture uploads; this is the quickest way to validate effect chaining without GPU-dependent rendering snapshots.

## US-004 — Directional Blur Quality

**Summary:** Updated `frosted_glass.frag` so its 8-direction blur uses per-direction procedural perturbation (angle and radius), and strengthened high-intensity frost veiling so large blur radii read as heavily obscured while mid settings remain recognizable.

**Key Decisions:** Kept the existing 8-sample ring for performance/compatibility, but introduced hash-based `dir_noise` and `radial_noise` per direction to break uniform ring artifacts. Added tests in `tests/test_frosted_glass_shader.py` that directly assert perturbed sampling logic and validate medium/high parameter behavior through shader-equation thresholds.

**Pitfalls Encountered:** The acceptance criteria text in injected context was truncated; the PRD markdown artifact was used to recover the full AC wording before tuning shader logic and writing assertions.

**Useful Context for Future Agents:** Full visual-output regression tests are not available in this repo; shader ACs are currently validated through source-contract assertions plus parameter-response math checks. If future iterations add GPU snapshot tests, keep these deterministic formula checks as fast guardrails.
