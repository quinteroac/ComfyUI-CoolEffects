# Lessons Learned — Iteration 000001

## US-001 — GLSL Frame Rendering

**Summary:** Implemented `nodes/video_generator.py` with a server-side ModernGL rendering loop that loads fragment shaders from `shaders/loader.py`, binds the input image as `u_image`, sets `u_resolution` and per-frame `u_time`, renders each frame offscreen, and returns an `IMAGE` batch tensor.

**Key Decisions:** Kept shader loading path-based (matching repository import conventions for hyphenated package directories); used `moderngl.create_standalone_context()` and full-screen quad rendering; enforced GL cleanup in a single `finally` block that releases VAO/VBO/FBO/textures/program/context.

**Pitfalls Encountered:** `pytest` is not available in this environment (`python3 -m pytest` fails with `No module named pytest`), so execution of the suite could not be completed locally in-session.

**Useful Context for Future Agents:** The new tests (`tests/test_video_generator_node.py`) use a fake ModernGL module injected via `sys.modules["moderngl"]`, which makes AC-level behavior checks deterministic without GPU/backend dependencies.

## US-002 — IMAGE Batch Output

**Summary:** Expanded `CoolVideoGenerator` coverage for IMAGE batch output behavior and tightened frame normalization to guarantee float32 output tensors in `[0, 1]`.

**Key Decisions:** Kept rendering pipeline unchanged (`fbo.read(components=3)` → numpy → torch) and validated each acceptance criterion through deterministic fake-ModernGL tests, including 90-frame output at 3s/30fps and PreviewImage-style frame iteration compatibility.

**Pitfalls Encountered:** Acceptance criteria text in JSON artifacts was truncated in some fields; full wording in the markdown PRD was used to derive precise assertions for shape/range/compatibility expectations.

**Useful Context for Future Agents:** `_FakeFramebuffer` now tracks read component usage and emits non-zero per-frame byte patterns, making it safer to assert readback, dtype, and normalization behavior without GPU dependencies.
