# Requirement: Canvas Video Player Node

## Context
ComfyUI-CoolEffects currently produces IMAGE batch tensors or uses VIDEO outputs from other nodes, but has no way to preview or download a video directly within the graph. Artists must leave ComfyUI to inspect results. This node embeds a `<canvas>`-based video player widget inside the node itself, enabling in-graph playback and one-click download — no external tools needed.

## Goals
- Provide a ComfyUI node that accepts a VIDEO input and renders it as a playable, downloadable widget.
- Use only existing dependencies (no new pip packages; plain browser JS/Canvas APIs).
- Integrate seamlessly with ComfyUI's native VIDEO output type.

## User Stories

### US-001: Node receives VIDEO input and displays it in a canvas widget
**As an** artist using ComfyUI, **I want** a node that accepts a VIDEO connection and renders the video frames inside a `<canvas>` widget embedded in the node **so that** I can preview the result without leaving the graph.

**Acceptance Criteria:**
- [ ] A new node `CoolVideoPlayer` is registered in `NODE_CLASS_MAPPINGS` and `NODE_DISPLAY_NAME_MAPPINGS`.
- [ ] The node declares a single input of type `VIDEO`.
- [ ] The node's frontend widget renders a `<canvas>` element inside the node body.
- [ ] When a VIDEO is connected and the graph is executed, the canvas displays the video frames.
- [ ] Typecheck / lint passes.
- [ ] Visually verified in browser: canvas appears inside the node with video content visible.

### US-002: User can play and pause the video in the canvas widget
**As an** artist, **I want** play and pause controls on the canvas widget **so that** I can inspect specific frames of the generated video.

**Acceptance Criteria:**
- [ ] A play/pause toggle button is rendered below the canvas.
- [ ] Clicking play starts frame-by-frame animation on the canvas; clicking pause stops it.
- [ ] Video loops continuously when playing.
- [ ] Typecheck / lint passes.
- [ ] Visually verified in browser: play/pause toggle works correctly.

### US-003: User can download the video from the node widget
**As an** artist, **I want** a download button on the canvas widget **so that** I can save the generated video to disk without leaving ComfyUI.

**Acceptance Criteria:**
- [ ] A "Download" button is rendered in the node widget alongside the canvas.
- [ ] Clicking it triggers a browser download of the video file (preserving the original format served by ComfyUI).
- [ ] The downloaded file opens and plays correctly in a standard video player.
- [ ] Typecheck / lint passes.
- [ ] Visually verified in browser: download button saves a valid video file.

## Functional Requirements
- FR-1: The node class `CoolVideoPlayer` must be defined in `nodes/video_player.py` and registered in `__init__.py`.
- FR-2: The node input must use ComfyUI's native `VIDEO` type so it connects to any node that outputs VIDEO.
- FR-3: The node must pass the VIDEO reference through to the frontend (via `ui` output or ComfyUI's file-serving mechanism) without re-encoding or copying the file in Python.
- FR-4: The frontend widget must be implemented as a plain ES module in `web/video_player.js` — no bundler, no new npm dependencies.
- FR-5: The canvas widget must use the HTML5 `<canvas>` API and a `<video>` element as the frame source (draw video frames to canvas via `drawImage`).
- FR-6: The download link must point to the URL ComfyUI already uses to serve the VIDEO file (no custom HTTP endpoint required unless unavoidable).
- FR-7: The widget must resize the canvas to match the video's intrinsic width/height on load.

## Non-Goals (Out of Scope)
- Re-encoding or transcoding the video (e.g. to MP4 if it is not already).
- Audio playback.
- Scrubbing / seek bar.
- Frame-level controls (step forward/back).
- Generating video from images inside this node (that is `CoolVideoGenerator`'s responsibility).
- Server-side thumbnail generation.

## Open Questions
- None.
