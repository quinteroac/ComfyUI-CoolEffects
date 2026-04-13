# CoolVideoGenerator Refactor — EFFECT_PARAMS Input

## Context

`CoolVideoGenerator` currently accepts `IMAGE + EFFECT_NAME (STRING)` and renders frames using hardcoded uniform values. Now that shaders accept per-effect uniforms and the `EFFECT_PARAMS` type defines defaults, the video generator must be refactored to accept `EFFECT_PARAMS` instead, merge the incoming params with the effect's defaults, and forward the resulting uniforms to ModernGL. This is a breaking change — existing workflows using `EFFECT_NAME STRING` will require rewiring to a per-effect node.

## Goals

- Replace the `EFFECT_NAME` STRING input with an `EFFECT_PARAMS` typed input.
- Merge incoming params with `DEFAULT_PARAMS` so missing params always fall back to sensible values.
- Pass the merged uniform dict to the ModernGL render loop.

## User Stories

### US-001: Accept EFFECT_PARAMS input
**As a** ComfyUI user, **I want** `CoolVideoGenerator` to accept an `EFFECT_PARAMS` connection **so that** I can wire any per-effect node directly to the video generator.

**Acceptance Criteria:**
- [ ] `CoolVideoGenerator.INPUT_TYPES` declares `effect_params` with type `"EFFECT_PARAMS"` under `required`.
- [ ] The `EFFECT_NAME` STRING input is removed from `INPUT_TYPES`.
- [ ] The `execute` method signature is `execute(self, image, effect_params, fps, duration)`.

### US-002: Default param merging
**As a** ComfyUI user, **I want** missing parameters in the EFFECT_PARAMS bundle to fall back to the effect's defaults **so that** partial params produce valid renders instead of broken output.

**Acceptance Criteria:**
- [ ] Before rendering, the node calls `merge_params(effect_params["effect_name"], effect_params["params"])` to produce the final uniform dict.
- [ ] If `effect_params["params"]` is empty (`{}`), the render uses all default values and produces the same output as the original hardcoded implementation.
- [ ] If `effect_params["effect_name"]` is not in `DEFAULT_PARAMS`, a `ValueError` is raised with a message identifying the unknown effect.

### US-003: Per-uniform ModernGL dispatch
**As a** ComfyUI user, **I want** each uniform in the merged params dict to be set on the shader program before rendering **so that** the rendered frames reflect the configured parameters.

**Acceptance Criteria:**
- [ ] Inside the render loop, for each `(name, value)` in the merged params dict, `program[name].value = float(value)` is called if the uniform exists in the program; non-existent uniform names are silently skipped.
- [ ] The base uniforms `u_time`, `u_image`, and `u_resolution` continue to be set as before, independently of the params dict.

### US-004: Backward-compatible frame output
**As a** ComfyUI user, **I want** the output tensor shape and dtype to remain unchanged **so that** downstream nodes continue to work without modification.

**Acceptance Criteria:**
- [ ] Output tensor shape is `[N, H, W, 3]`, dtype `float32`, values in `[0, 1]`.
- [ ] Frame count `N = round(duration * fps)` is unchanged.
- [ ] `fps` and `duration` input definitions (type, default, min, max, step) are unchanged.

---

## Functional Requirements

- FR-1: `CoolVideoGenerator.INPUT_TYPES` replaces `effect_name (STRING)` with `effect_params (EFFECT_PARAMS)`.
- FR-2: `nodes/video_generator.py` imports `EFFECT_PARAMS` and `merge_params` from `nodes/effect_params.py`.
- FR-3: The render loop calls `merge_params` before iterating frames, and sets per-effect uniforms via `program[name].value = float(value)` with a `try/except KeyError` guard for unknown uniform names.
- FR-4: GL resource cleanup (`try/finally`) for ctx, texture, program, fbo, vbo is preserved.
- FR-5: `__init__.py` node registration is updated if needed to reflect the new input type.

## Non-Goals

- This PRD does not add a preview widget to `CoolVideoGenerator`.
- This PRD does not create per-effect node classes.
- This PRD does not keep backward compatibility with `EFFECT_NAME STRING` — existing workflows must be rewired.

## Open Questions

- None.
