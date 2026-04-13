# Pan Dedicated Nodes & Registration

## Context

PRD 001 delivers the five pan GLSL shaders and `DEFAULT_PARAMS` entries. This PRD wires them into the ComfyUI node graph by creating five dedicated effect nodes (`CoolPanLeftEffect`, `CoolPanRightEffect`, `CoolPanUpEffect`, `CoolPanDownEffect`, `CoolPanDiagonalEffect`), registering them in `__init__.py`, and covering the integration with tests. The node pattern follows exactly `CoolGlitchEffect` / `CoolVHSEffect` / `CoolZoomPulseEffect`: typed inputs, `build_effect_params()`, returns `EFFECT_PARAMS`.

## Goals

- Expose all five pan effects as first-class ComfyUI nodes with named, typed inputs.
- Keep the implementation consistent with the existing dedicated-node pattern.
- Provide pytest tests that exercise the full rendering path for each pan direction.

## User Stories

### US-001: CoolPanLeftEffect node produces valid EFFECT_PARAMS
**As a** ComfyUI user, **I want** a `CoolPanLeftEffect` node **so that** I can connect it to `CoolVideoGenerator` to render a left-scrolling animation with explicit speed and origin controls.

**Acceptance Criteria:**
- [ ] `nodes/pan_left_effect.py` defines `CoolPanLeftEffect` with inputs `speed` (FLOAT, default 0.2, min 0.0, max 5.0, step 0.05), `origin_x` (FLOAT, default 0.0, min 0.0, max 1.0, step 0.01), `origin_y` (FLOAT, default 0.0, min 0.0, max 1.0, step 0.01).
- [ ] `RETURN_TYPES = ("EFFECT_PARAMS",)` and `CATEGORY = "CoolEffects"`.
- [ ] `execute()` returns `build_effect_params("pan_left", {"u_speed": speed, "u_origin_x": origin_x, "u_origin_y": origin_y})`.
- [ ] Node is listed under `NODE_CLASS_MAPPINGS["CoolPanLeftEffect"]` in `__init__.py`.

---

### US-002: CoolPanRightEffect node produces valid EFFECT_PARAMS
**As a** ComfyUI user, **I want** a `CoolPanRightEffect` node **so that** I can render a right-scrolling animation.

**Acceptance Criteria:**
- [ ] `nodes/pan_right_effect.py` defines `CoolPanRightEffect` with the same input schema as US-001.
- [ ] `execute()` returns `build_effect_params("pan_right", {"u_speed": speed, "u_origin_x": origin_x, "u_origin_y": origin_y})`.
- [ ] Node is listed under `NODE_CLASS_MAPPINGS["CoolPanRightEffect"]` in `__init__.py`.

---

### US-003: CoolPanUpEffect node produces valid EFFECT_PARAMS
**As a** ComfyUI user, **I want** a `CoolPanUpEffect` node **so that** I can render a bottom-to-top scrolling animation.

**Acceptance Criteria:**
- [ ] `nodes/pan_up_effect.py` defines `CoolPanUpEffect` with the same input schema as US-001.
- [ ] `execute()` returns `build_effect_params("pan_up", {"u_speed": speed, "u_origin_x": origin_x, "u_origin_y": origin_y})`.
- [ ] Node is listed under `NODE_CLASS_MAPPINGS["CoolPanUpEffect"]` in `__init__.py`.

---

### US-004: CoolPanDownEffect node produces valid EFFECT_PARAMS
**As a** ComfyUI user, **I want** a `CoolPanDownEffect` node **so that** I can render a top-to-bottom scrolling animation.

**Acceptance Criteria:**
- [ ] `nodes/pan_down_effect.py` defines `CoolPanDownEffect` with the same input schema as US-001.
- [ ] `execute()` returns `build_effect_params("pan_down", {"u_speed": speed, "u_origin_x": origin_x, "u_origin_y": origin_y})`.
- [ ] Node is listed under `NODE_CLASS_MAPPINGS["CoolPanDownEffect"]` in `__init__.py`.

---

### US-005: CoolPanDiagonalEffect node produces valid EFFECT_PARAMS
**As a** ComfyUI user, **I want** a `CoolPanDiagonalEffect` node **so that** I can render a diagonal scrolling animation with a configurable angle.

**Acceptance Criteria:**
- [ ] `nodes/pan_diagonal_effect.py` defines `CoolPanDiagonalEffect` with inputs `speed` (FLOAT, default 0.2, min 0.0, max 5.0, step 0.05), `origin_x`, `origin_y` (same as US-001), `dir_x` (FLOAT, default 0.7071, min -1.0, max 1.0, step 0.01), `dir_y` (FLOAT, default 0.7071, min -1.0, max 1.0, step 0.01).
- [ ] `execute()` returns `build_effect_params("pan_diagonal", {"u_speed": speed, "u_origin_x": origin_x, "u_origin_y": origin_y, "u_dir_x": dir_x, "u_dir_y": dir_y})`.
- [ ] Node is listed under `NODE_CLASS_MAPPINGS["CoolPanDiagonalEffect"]` in `__init__.py`.

---

### US-006: Integration tests verify rendered output shape and dtype for all five pan nodes
**As a** developer, **I want** pytest tests that exercise the full rendering path for each pan node **so that** regressions in shader loading or uniform passing are caught automatically.

**Acceptance Criteria:**
- [ ] `tests/test_pan_effects.py` exists with one test function per pan direction (five total).
- [ ] Each test constructs a 1×4×4×3 float32 torch tensor as input, calls `CoolVideoGenerator.execute()` with the corresponding pan `EFFECT_PARAMS`, `fps=1`, `duration=1.0`.
- [ ] Each test asserts the output tensor has shape `(1, 4, 4, 3)`, dtype `torch.float32`, and all values in `[0.0, 1.0]`.
- [ ] Tests are skipped (via `pytest.importorskip("moderngl")`) if `moderngl` is not available.

---

## Functional Requirements

- FR-1: All five node files must import `build_effect_params` from `effect_params.py` using the same `importlib.util` pattern as the existing effect nodes.
- FR-2: `RETURN_TYPES = ("EFFECT_PARAMS",)`, `RETURN_NAMES = ("EFFECT_PARAMS",)`, `FUNCTION = "execute"`, `CATEGORY = "CoolEffects"` must be set on every node class.
- FR-3: Each node must be added to both `NODE_CLASS_MAPPINGS` and `NODE_DISPLAY_NAME_MAPPINGS` in `__init__.py` (display names: "Cool Pan Left Effect", "Cool Pan Right Effect", "Cool Pan Up Effect", "Cool Pan Down Effect", "Cool Pan Diagonal Effect").
- FR-4: Adding the five nodes must not break the existing nodes — `CoolGlitchEffect`, `CoolVHSEffect`, `CoolZoomPulseEffect`, `CoolEffectSelector`, and `CoolVideoGenerator` must still load and register correctly.
- FR-5: Tests must not require a display or GPU — `moderngl.create_standalone_context(backend="egl")` must be the only rendering context used.

## Non-Goals

- GLSL shader files — covered by PRD 001.
- `DEFAULT_PARAMS` entries in `effect_params.py` — covered by PRD 001.
- Frontend live-preview widget updates for pan effects.
- Clamp-at-edge (no-wrap) mode.

## Open Questions

- None.
