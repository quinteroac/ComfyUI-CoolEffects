# Requirement: CoolVideoMixer Node

## Context
ComfyUI-CoolEffects currently provides a `CoolAudioMixer` node (iteration 000017) that concatenates audio tracks from a directory using selectable transitions (`crossfade`, `hard_cut`, `fade_to_silence`). This iteration adds an analogous `CoolVideoMixer` node: it loads multiple video files from a directory and produces a single mixed `VIDEO` with configurable transitions between clips. Beyond effect-driven video generation, the package can now assemble pre-rendered clips directly, keeping the ergonomics and semantics of the audio mixer.

## Goals
- Deliver a `CoolVideoMixer` node that mirrors the ergonomics and semantics of `CoolAudioMixer` for video.
- Support three transition types (`crossfade`, `hard_cut`, `fade_to_black`) with a configurable duration.
- Output a single `VIDEO` compatible with the existing `CoolVideoPlayer` node.
- Preserve and mix each video's embedded audio alongside the visual transition.
- Enforce strict input homogeneity (same resolution, same fps) to keep the MVP simple and predictable.

## User Stories

### US-001: Load video files from a directory
**As a** ComfyUI user, **I want** to point the node at a directory and have it load all supported video files in sorted order, **so that** I can assemble a clip sequence without manually wiring each file.

**Acceptance Criteria:**
- [ ] `directory_path` STRING input; empty, non-existent, or non-directory path raises `ValueError`
- [ ] Supported extensions: `.mp4`, `.mov`, `.webm`, `.mkv` (case-insensitive)
- [ ] Files sorted alphabetically by filename (case-insensitive)
- [ ] Raises `ValueError` if fewer than 2 video files are present
- [ ] Typecheck / lint passes

### US-002: Select transition effect and configure its duration
**As a** ComfyUI user, **I want** to pick a transition type and duration from node widgets, **so that** I can control how clips blend together.

**Acceptance Criteria:**
- [ ] `transition_type` COMBO input with options `["crossfade", "hard_cut", "fade_to_black"]`, default `"crossfade"`
- [ ] `transition_duration` FLOAT input, default `1.0`, min `0.1`, max `10.0`, step `0.1`
- [ ] `hard_cut` ignores the duration (effective duration forced to `0.0`)
- [ ] Visually verified in browser — widgets render and update correctly on the `CoolVideoMixer` node
- [ ] Typecheck / lint passes

### US-003: Mix tracks with the selected transition
**As a** ComfyUI user, **I want** the node to concatenate videos using my selected transition (with audio transitioning in parallel), **so that** the output plays as a single seamless clip.

**Acceptance Criteria:**
- [ ] All videos must share identical resolution (width × height) and fps — otherwise raises `ValueError` naming the offending file
- [ ] `crossfade`: alpha-blend overlap of `transition_duration` seconds between adjacent clips (outgoing fades 1→0, incoming fades 0→1)
- [ ] `hard_cut`: straight concatenation, no blending
- [ ] `fade_to_black`: outgoing clip fades to black over the transition window, then a black gap of the transition window, then incoming fades in from black — mirrors the audio mixer's `fade_to_silence` shape
- [ ] Audio tracks are preserved and mixed in parallel using the transition analog: `crossfade` → audio crossfade, `fade_to_black` → `fade_to_silence`, `hard_cut` → direct audio concatenation
- [ ] If a video has no audio track, silent audio of matching duration is synthesized so the combined audio stays aligned with the visuals
- [ ] Raises `ValueError` if `transition_duration` exceeds the shortest adjacent clip's duration (for non-`hard_cut` transitions)
- [ ] Typecheck / lint passes

### US-004: Output a mixed VIDEO
**As a** ComfyUI user, **I want** the node to output a single `VIDEO`, **so that** I can pipe it into `CoolVideoPlayer` or any other downstream node.

**Acceptance Criteria:**
- [ ] `RETURN_TYPES = ("VIDEO",)` with `RETURN_NAMES = ("video",)`
- [ ] VIDEO is assembled via `comfy_api.latest.InputImpl.VideoFromComponents` (same API used by `CoolVideoGenerator`), carrying the mixed image frames and the mixed audio track
- [ ] Visually verified in browser: connecting `CoolVideoMixer` → `CoolVideoPlayer` plays the mixed clip end-to-end with transitions rendering correctly
- [ ] Typecheck / lint passes

## Functional Requirements
- FR-1: Node class `CoolVideoMixer` registered under category `CoolEffects/video`; mapping key `"CoolVideoMixer"` in `NODE_CLASS_MAPPINGS`.
- FR-2: `INPUT_TYPES` exposes required inputs: `directory_path` (STRING, default `""`), `transition_type` (COMBO over `["crossfade", "hard_cut", "fade_to_black"]`, default `"crossfade"`), `transition_duration` (FLOAT, default `1.0`, min `0.1`, max `10.0`, step `0.1`).
- FR-3: `RETURN_TYPES = ("VIDEO",)`, `RETURN_NAMES = ("video",)`, `FUNCTION = "execute"`.
- FR-4: Directory resolution uses `Path(directory_path).expanduser()`; accepts absolute and `~`-prefixed paths.
- FR-5: Supported video extensions: `.mp4`, `.mov`, `.webm`, `.mkv` (case-insensitive); minimum 2 files; sort alphabetically by filename (case-insensitive).
- FR-6: Strict homogeneity check: every loaded video must match the first video's width, height, and fps exactly; otherwise raise `ValueError` identifying the offending file and the mismatched attribute.
- FR-7: Transition types: `crossfade`, `hard_cut`, `fade_to_black`. `hard_cut` forces effective transition duration to `0.0`.
- FR-8: `transition_duration` widget-clamped to `[0.1, 10.0]`; at runtime, validated against the shortest adjacent clip's duration (raises `ValueError` if exceeded).
- FR-9: Audio propagation: each video's audio is loaded; missing audio is synthesized as silence of matching duration and a `logging.warning(...)` is emitted naming the file; audio is mixed using the transition-analog rule (FR-7 mapping) so audio transitions line up with visual transitions.
- FR-10: Output VIDEO assembled via `comfy_api.latest.InputImpl.VideoFromComponents` with the common fps, resolution, and audio sample rate; must be compatible with `CoolVideoPlayer`.
- FR-11: Video decoding uses `av` (PyAV — direct ffmpeg bindings) for both frame and audio extraction. `av` is added to `requirements.txt` and imported with `try/except ImportError` following the `torchaudio` pattern in `audio_mixer.py`.
- FR-14: `fade_to_black` visual shape mirrors the audio mixer's `fade_to_silence` exactly: outgoing fades to black over `transition_duration` seconds, then a black gap of `transition_duration` seconds, then incoming fades in from black over `transition_duration` seconds (total transition window = `2 × transition_duration`). Audio fade_to_silence aligns sample-for-sample with the visual fade/gap/fade structure.
- FR-12: Node registration in `__init__.py` follows the existing `importlib.util.spec_from_file_location` pattern used by sibling nodes; soft failure on missing decoder dep (node not registered if import fails).
- FR-13: Structure the implementation in `nodes/video_mixer.py` with internal helpers mirroring `audio_mixer.py` (`_resolve_video_file_paths`, `_load_video_files`, `_validate_homogeneous`, `_mix_prepared_tracks`, etc.).

## Non-Goals (Out of Scope)
- Per-clip trim / start / end time controls (clips are mixed in their entirety, minus transition overlap).
- Reordering or filtering clips from the UI — order is strictly alphabetical by filename.
- Resolution or fps normalization (resize / resample) — MVP requires matching inputs; a future iteration may relax this.
- Additional transitions such as wipes, slides, zoom, or `fade_to_white`.
- Per-clip audio volume controls or independent audio/video transition durations.
- Reading videos from sources other than a local directory (URLs, remote storage, `VIDEO` inputs).
- Frontend widget — no canvas preview on the `CoolVideoMixer` node itself (downstream `CoolVideoPlayer` provides playback).

## Open Questions
- None — all resolved during interview:
  - Video decoding library → `av` (PyAV) — see FR-11.
  - Missing-audio handling → synthesize silence + emit `logging.warning(...)` naming the file — see FR-9.
  - `fade_to_black` shape → mirror `fade_to_silence` exactly (fade-out + black gap + fade-in, total `2 × transition_duration`) — see FR-14.
