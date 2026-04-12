# Effect Selector Node (Frontend)

## Context

With the shader library in place (PRD 001), the Effect Selector Node provides the user
interface layer: a custom ComfyUI node whose widget renders a live GLSL preview using
Three.js, React Three Fiber (R3F), and drei. The user picks an effect from a dropdown,
sees it applied to the input image in real time, and the node outputs both the original
image and the selected effect name for downstream consumption by the Video Generator Node.

## Goals

- Deliver a ComfyUI node with a custom React widget that previews GLSL effects.
- Use Three.js ShaderMaterial fed by shaders from the shared JS shader loader (PRD 001).
- Output the selected effect name as a string type that the Video Generator Node consumes.
- Keep the node self-contained: no server round-trip needed for the preview.

## User Stories

### US-001: Effect Dropdown
**As a** ComfyUI user, **I want** a dropdown in the node that lists all available GLSL effects
**so that** I can select the effect I want to apply without editing configuration files.

**Acceptance Criteria:**
- [ ] The node widget renders a `<select>` (or equivalent R3F/Leva control) listing every
  shader present in `shaders/glsl/` by name (filename without extension).
- [ ] Changing the dropdown selection updates the preview within 100 ms without a page reload.
- [ ] The selected effect name is emitted as the node's `EFFECT_NAME` output string.

### US-002: Live GLSL Preview
**As a** ComfyUI user, **I want** to see my input image rendered with the selected GLSL
shader in the node widget **so that** I can judge the effect before committing to a full
video render.

**Acceptance Criteria:**
- [ ] The widget contains a Three.js canvas (via R3F) showing a plane mesh with the input
  image as `u_image` texture and the selected shader as the fragment program.
- [ ] The preview animates `u_time` in real time (requestAnimationFrame loop).
- [ ] `u_resolution` is set to the canvas dimensions and updates on resize.
- [ ] If no input image is connected, the canvas shows a grey placeholder without errors.

### US-003: Node Inputs and Outputs
**As a** ComfyUI workflow builder, **I want** the Effect Selector Node to accept an IMAGE
input and produce IMAGE + EFFECT_NAME outputs **so that** I can chain it with the Video
Generator Node in a standard workflow.

**Acceptance Criteria:**
- [ ] The node is registered in `NODE_CLASS_MAPPINGS` as `"CoolEffectSelector"`.
- [ ] The node's Python class declares input `image` of type `IMAGE` and outputs
  `(IMAGE, STRING)` where STRING carries the effect name.
- [ ] The Python `execute` method passes `image` through unchanged and returns the
  selected effect name string alongside it.
- [ ] The node appears in the ComfyUI node browser under the category `"CoolEffects"`.

### US-004: Shader Loading in Frontend
**As a** frontend developer, **I want** the widget to load GLSL source via the JS shader
loader from PRD 001 **so that** shaders are not duplicated between frontend and backend.

**Acceptance Criteria:**
- [ ] The widget calls `loadShader(effectName)` (from `web/shaders/loader.js`) to obtain
  the GLSL string and sets it as the `fragmentShader` of the Three.js `ShaderMaterial`.
- [ ] If `loadShader` throws, the widget displays an inline error message inside the canvas
  area instead of crashing the whole ComfyUI frontend.

---

## Functional Requirements

- FR-1: The Python node class file is `nodes/effect_selector.py`.
- FR-2: The React widget is registered via ComfyUI's frontend extension system under `web/effect_selector.js`.
- FR-3: The widget must use R3F (`@react-three/fiber`) and drei (`@react-three/drei`) for the 3D canvas.
- FR-4: The Three.js `ShaderMaterial` must set `u_image`, `u_time`, and `u_resolution` uniforms on every frame.
- FR-5: The effect dropdown must be populated dynamically from the list of available shader names
  (fetched or bundled at widget init time) — not hardcoded.
- FR-6: The node output type for the effect name must be the ComfyUI built-in `STRING` type.

## Non-Goals

- Video rendering or ffmpeg (covered in PRD 003).
- Editing shader source code from within the node widget.
- Supporting vertex shader customisation.
- Saving or exporting the preview frame as an image.

## Open Questions

- Should the effect name list be fetched from a backend endpoint (so the frontend always
  reflects what shaders are on disk) or bundled as a static JSON at server start?
- Does the preview canvas need a configurable size, or is a fixed 512×512 sufficient?
