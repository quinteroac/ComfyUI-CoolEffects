# Lessons Learned — Iteration 000008

## US-001 — Node receives VIDEO input and displays it in a canvas widget

**Summary:** Added a new `CoolVideoPlayer` output node that accepts a `VIDEO` input, emits normalized video preview metadata via UI payloads, and a frontend Comfy extension that mounts a canvas widget and draws decoded video frames after graph execution events.

**Key Decisions:** Kept backend logic minimal and deterministic by normalizing `VIDEO` payloads into `video_entries` with `source_url` values (including `/view` URL synthesis from filename metadata); implemented frontend playback with a hidden `<video>` source drawn into `<canvas>` via `requestAnimationFrame`; used a single shared `executed` event listener keyed by node ID to avoid per-node listener duplication.

**Pitfalls Encountered:** Runtime environment did not provide a system `pytest`; tests were run through an existing local virtual environment (`/home/victor/venv`) and the repository’s full test suite already has unrelated baseline failures, so verification focused on new and directly impacted tests.

**Useful Context for Future Agents:** For ComfyUI custom preview nodes, returning `{"ui": ..., "result": ()}` from an `OUTPUT_NODE` is a reliable way to pass execution-time metadata to frontend widgets; widget tests in this repo use Node.js module execution with fake DOM/video/canvas objects, which is fast and sufficient to validate embedded-canvas behavior without a browser.
