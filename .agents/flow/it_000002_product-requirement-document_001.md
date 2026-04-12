# Standalone Effect Selector with Built-in Preview

## Context

The current `CoolEffectSelector` node requires a connected IMAGE input to function and to show a live preview. This creates unnecessary friction: the user must wire an image before being able to see the effect. The node's real job is to select an effect and emit its name — not to pass images through. The preview should work immediately with a built-in placeholder so the user can evaluate effects without connecting anything.

## Goals

- Remove the IMAGE input and IMAGE output from `CoolEffectSelector` so it becomes a pure effect-name selector.
- Ensure the frontend live preview always runs using a synthetic placeholder texture (no image connection required).
- Remove the "Connect an image to preview this effect." overlay message.

## User Stories

### US-001: Effect selection without image input
**As a** ComfyUI user, **I want** to add the `CoolEffectSelector` node and immediately see the effect preview **so that** I can choose the right effect before wiring any image.

**Acceptance Criteria:**
- [ ] `CoolEffectSelector.INPUT_TYPES` does not contain an `image` key in `required` or `optional`.
- [ ] `CoolEffectSelector.RETURN_TYPES` is `("STRING",)` and `RETURN_NAMES` is `("EFFECT_NAME",)`.
- [ ] `CoolEffectSelector.execute()` takes no `image` parameter and returns `(effect_name,)`.
- [ ] Connecting the node's output to `CoolVideoGenerator.effect_name` works without any IMAGE output from the selector.

### US-002: Built-in preview placeholder
**As a** ComfyUI user, **I want** the effect preview canvas to display the GLSL effect over a synthetic image immediately **so that** I never see a blank or gray canvas when the node is first added.

**Acceptance Criteria:**
- [ ] On `mount_effect_selector_widget_for_node`, `create_live_glsl_preview` is called with a programmatically generated placeholder texture (e.g. a 512×512 UV-gradient or checkerboard drawn on an offscreen canvas).
- [ ] The overlay element never displays "Connect an image to preview this effect." — that message is removed entirely.
- [ ] The canvas background is `transparent` (not gray) once the placeholder texture is set.
- [ ] Switching effects in the dropdown updates the GLSL shader while keeping the same placeholder texture.
- [ ] The placeholder is generated purely in JS — no new HTTP endpoint or Python change is required for this.

---

## Functional Requirements

- FR-1: Remove `image` from `CoolEffectSelector.INPUT_TYPES` (both `required` and `optional` sections).
- FR-2: Set `RETURN_TYPES = ("STRING",)` and `RETURN_NAMES = ("EFFECT_NAME",)` on `CoolEffectSelector`.
- FR-3: Update `execute(self, effect_name)` signature — no `image` parameter.
- FR-4: Add a `generate_placeholder_texture(document_ref, width=512, height=512)` function in `effect_selector.js` that draws a UV-gradient (red = U, green = V, blue = 0.5) onto an offscreen `HTMLCanvasElement` and returns a `THREE.CanvasTexture` (or equivalent texture object compatible with the existing `ShaderMaterial` uniform).
- FR-5: Call `generate_placeholder_texture` inside `mount_effect_selector_widget_for_node` and pass the result as `input_image` to `create_live_glsl_preview`.
- FR-6: Remove the conditional overlay message `"Connect an image to preview this effect."` from `update_overlay_message` in `create_live_glsl_preview`.
- FR-7: Set `canvas_element.style.background = "transparent"` unconditionally once the placeholder is provided (remove the `input_image ? "transparent" : "rgb(128,128,128)"` branch).

## Non-Goals

- Allowing the user to swap the placeholder for a custom image at runtime (out of scope).
- Changing `CoolVideoGenerator` — it still requires an IMAGE input from the graph.
- Adding a new HTTP endpoint for serving placeholder images.
- Modifying any shader GLSL files.

## Open Questions

- None.
