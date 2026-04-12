# Video Generator Node (Backend)

## Context

With shaders centralised (PRD 001) and the effect chosen via the selector node (PRD 002),
the Video Generator Node renders all frames of a GLSL animation offscreen using ModernGL
and returns them as a standard ComfyUI IMAGE batch tensor `[N, H, W, C]`. Outputting a
batch of images (rather than a video file) makes the node compatible with any downstream
ComfyUI node — AnimateDiff, VHS Save, image processors, further effect chaining — and
enables per-frame processing without extra tooling.

## Goals

- Render GLSL effects on the server using ModernGL headless (no display required).
- Return all rendered frames as a single IMAGE batch tensor `[N, H, W, C]`.
- Expose duration and FPS as configurable inputs on the node.
- Eliminate external dependencies (no ffmpeg required).

## User Stories

### US-001: GLSL Frame Rendering
**As a** ComfyUI user, **I want** the node to render each video frame by running the GLSL
shader on my input image server-side **so that** the output frames match the preview I
saw in the selector node.

**Acceptance Criteria:**
- [ ] The node creates a ModernGL offscreen context with `moderngl.create_standalone_context()` (no display dependency).
- [ ] For each frame `i` in `[0, round(duration * fps))`, `u_time` is set to `i / fps`.
- [ ] `u_image` is bound to the input image as an OpenGL texture.
- [ ] `u_resolution` is set to the input image dimensions `(width, height)`.
- [ ] The node raises a descriptive `ValueError` if the shader named by `effect_name`
  does not exist in the shader library (uses `load_shader` which raises `FileNotFoundError`).
- [ ] The ModernGL context and all GL resources are released (`ctx.release()`) after rendering,
  even if an exception occurs (use try/finally).

### US-002: IMAGE Batch Output
**As a** ComfyUI workflow builder, **I want** the node to output an IMAGE batch
**so that** I can connect it directly to any downstream node — VHS Save, AnimateDiff,
image processors — without format conversion.

**Acceptance Criteria:**
- [ ] Each rendered frame is read back from the ModernGL framebuffer as raw RGB bytes.
- [ ] Frames are converted to a `torch.Tensor` of shape `[N, H, W, 3]` with dtype `float32`
  and values in `[0.0, 1.0]`.
- [ ] The output tensor is returned as the node's `IMAGE` output.
- [ ] For an input of shape `[1, H, W, C]`, a duration of 3 s at 30 fps, the output shape
  is `[90, H, W, 3]`.
- [ ] Connecting the output to a ComfyUI `PreviewImage` node displays all frames as a
  scrollable batch without errors.

### US-003: Duration and FPS Configuration
**As a** ComfyUI user, **I want** to configure the animation duration and frame rate directly
on the node **so that** I can generate a 3-second batch or a 10-second batch without
editing code.

**Acceptance Criteria:**
- [ ] The node exposes an `INT` input `fps` with default 30, min 1, max 60.
- [ ] The node exposes a `FLOAT` input `duration` with default 3.0, min 0.5, max 60.0, step 0.5.
- [ ] Total frames rendered equals `round(duration * fps)`.
- [ ] Both inputs are visible and adjustable as standard ComfyUI node widgets.

### US-004: ComfyUI Node Integration
**As a** ComfyUI workflow builder, **I want** the Video Generator Node to accept
IMAGE + EFFECT_NAME inputs and return an IMAGE batch **so that** I can connect it
directly to the Effect Selector Node and any downstream image node.

**Acceptance Criteria:**
- [ ] The node is registered in `NODE_CLASS_MAPPINGS` as `"CoolVideoGenerator"`.
- [ ] The node declares inputs: `image` (IMAGE), `effect_name` (STRING), `fps` (INT), `duration` (FLOAT).
- [ ] The node output type is `("IMAGE",)`.
- [ ] The node appears in the ComfyUI node browser under the category `"CoolEffects"`.
- [ ] The node completes rendering a 512×512 image, 3 s at 30 fps (90 frames) in under
  30 seconds on a machine with a GPU available to ModernGL.

---

## Functional Requirements

- FR-1: The Python node class file is `nodes/video_generator.py`.
- FR-2: Shader source is loaded exclusively via `shaders/loader.py::load_shader(effect_name)` — no inline GLSL strings in the node.
- FR-3: The ModernGL context must be created with `moderngl.create_standalone_context()`.
- FR-4: A full-screen quad (two triangles covering NDC `[-1, 1]`) is used as the render geometry.
- FR-5: Frames are read back via `fbo.read(components=3)` and converted to numpy arrays before stacking into a torch tensor.
- FR-6: The final tensor must be stacked with `torch.stack` or `torch.from_numpy` into shape `[N, H, W, 3]`, dtype `float32`, range `[0, 1]`.
- FR-7: All GL resources (context, texture, program, fbo, vbo) must be released in a `finally` block.

## Non-Goals

- Video file output or ffmpeg encoding (users can feed the batch to VHS Save or similar).
- Audio in any output.
- Multi-image batch input (single image input only for this iteration).
- Real-time or interactive rendering.
- GPU selection or multi-GPU support.
- Resolution upscaling or downscaling relative to input image size.

## Open Questions

- Should the node expose a `seed` / `start_time` input so users can offset the animation
  start point (e.g. render frames 5 s–8 s instead of always starting at t=0)?
