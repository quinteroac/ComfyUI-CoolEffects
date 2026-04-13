# Requirement: Batch Image Input for CoolVideoGenerator

## Context

The `CoolVideoGenerator` node currently accepts a single image as the base texture and renders N frames by animating the GLSL shader over time (`u_time`). When a ComfyUI workflow produces a sequence of images (e.g. from an animation pipeline), there is no way to feed that sequence into the video generator — the node silently discards all frames except the first.

This feature extends the node to treat an IMAGE batch as a temporal sequence of textures: frame `i` of the output video uses `batch[i % N]` as its base texture, enabling the batch to loop seamlessly when the requested duration exceeds the number of input images.

## Goals

- Accept IMAGE batches of any size (including batch-of-1) without breaking existing workflows.
- Loop the input batch automatically when `round(duration * fps) > batch_size`.
- Keep GPU/VRAM usage bounded: upload only one texture per render frame (never all frames at once).

## User Stories

### US-001: Single image input remains backward-compatible

**As a** ComfyUI artist, **I want** the node to behave identically when I connect a single image (batch of 1) **so that** my existing workflows are not broken.

**Acceptance Criteria:**
- [ ] A tensor with shape `[1, H, W, 3]` or `[H, W, 3]` produces the same output as before (all output frames use that single image as texture).
- [ ] No change to `INPUT_TYPES`, `RETURN_TYPES`, or node registration is required for single-image workflows.
- [ ] Existing test suite passes without modification.
- [ ] Typecheck / lint passes.

---

### US-002: IMAGE batch used as per-frame texture sequence

**As a** ComfyUI artist, **I want** to connect a batch of images to the `CoolVideoGenerator` node **so that** each output frame renders the GLSL shader on top of the corresponding input frame of the batch.

**Acceptance Criteria:**
- [ ] A tensor with shape `[N, H, W, 3]` is accepted without error.
- [ ] Output frame at index `i` uses `batch[i % N]` as the `u_image` texture (modulo loop).
- [ ] The total number of output frames is still `round(duration * fps)` regardless of batch size.
- [ ] When `round(duration * fps) <= N`, only the first `round(duration * fps)` batch frames are used (no unnecessary GPU uploads).
- [ ] Typecheck / lint passes.

---

### US-003: Batch texture upload is memory-efficient

**As a** ComfyUI artist running on a GPU with limited VRAM, **I want** the node to upload only one frame texture per render cycle **so that** large batches don't exhaust GPU memory.

**Acceptance Criteria:**
- [ ] Only one ModernGL texture object is alive at any point during the render loop (the previous frame's data is overwritten or the texture is updated in-place via `texture.write()`).
- [ ] No list or array of N ModernGL textures is created upfront.
- [ ] A batch of 100+ frames can be processed without OOM errors on a GPU with typical VRAM (tested by inspection / code review).
- [ ] Typecheck / lint passes.

---

### US-004: Tests cover the batch rendering path

**As a** developer, **I want** automated tests for the batch input path **so that** regressions are caught before merge.

**Acceptance Criteria:**
- [ ] A test verifies that output frame `i` corresponds to `batch[i % N]` (mock or stub ModernGL; assert texture `write()` is called with the correct bytes for each frame index).
- [ ] A test verifies that a batch-of-1 tensor produces the same result as the existing single-image path.
- [ ] All tests in `tests/` pass with `pytest`.
- [ ] Typecheck / lint passes.

## Functional Requirements

- **FR-1:** `_extract_input_image` (or a replacement function) must handle a batch tensor `[N, H, W, 3]` and return the full batch as a list/array of N uint8 frames, not just `frame[0]`.
- **FR-2:** In `CoolVideoGenerator.execute`, the render loop must select `batch_frame = frames[frame_index % batch_size]` for each iteration and update the input texture data in-place using `texture.write(batch_frame.tobytes())`.
- **FR-3:** The input texture object must be created once (using dimensions from the first batch frame) and reused across all render iterations; only its pixel data is updated per frame.
- **FR-4:** Width and height must be taken from the first frame of the batch; all frames in the batch are assumed to share the same resolution (no resize step required).
- **FR-5:** The `image` input type remains `("IMAGE",)` — no schema change needed, as ComfyUI's IMAGE type already supports batches.

## Non-Goals (Out of Scope)

- Resizing or padding frames with mismatched resolutions within the same batch.
- Interpolation or blending between consecutive batch frames.
- Any change to the frontend / JS widgets.
- Exposing batch size or loop count as explicit node parameters.
- Exporting video files (output remains an IMAGE batch tensor).

## Open Questions

- None.
