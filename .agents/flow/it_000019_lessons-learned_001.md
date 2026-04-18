# Lessons Learned — Iteration 000019

## US-001 — Load video files from a directory

**Summary:** Added a new `CoolVideoMixer` node scaffold with directory scanning logic that validates `directory_path`, filters supported video extensions (`.mp4`, `.mov`, `.webm`, `.mkv`) case-insensitively, sorts by filename case-insensitively, and rejects directories with fewer than two matching files.

**Key Decisions:** Reused the same path-resolution and validation pattern used by `CoolAudioMixer` to keep behavior consistent across media directory inputs; exposed a single `directory_path` widget for this story and deferred transition/mixing behavior to later stories.

**Pitfalls Encountered:** The environment lacks `pytest` and `pip`, so repository tests could not be executed directly with `python3 -m pytest`; validation had to rely on static checks and code-level consistency with existing node patterns.

**Useful Context for Future Agents:** `CoolVideoMixer` is now registered in `__init__.py` and documented in `README.md`; future stories can extend `nodes/video_mixer.py` incrementally (transition controls, decode/mix pipeline, VIDEO output) without reworking file discovery behavior.

## US-002 — Select transition effect and configure its duration

**Summary:** Added transition widgets to `CoolVideoMixer` by exposing `transition_type` (`crossfade`, `hard_cut`, `fade_to_black`) and `transition_duration` (`FLOAT` with `default=1.0`, `min=0.1`, `max=10.0`, `step=0.1`) in `INPUT_TYPES`, and wired runtime transition-duration resolution so `hard_cut` always uses effective duration `0.0`.

**Key Decisions:** Reused the same transition-duration resolution pattern as `CoolAudioMixer` to keep node behavior and validation semantics consistent across media mixers; preserved the current `CoolVideoMixer` output contract (`STRING` list of scanned files) while preparing transition controls for later mixing pipeline stories.

**Pitfalls Encountered:** `CoolVideoMixer` does not yet execute clip blending, so effective transition duration is currently validated/resolved as an explicit contract step rather than applied to rendered output; tests therefore assert the helper behavior directly.

**Useful Context for Future Agents:** For future clip-composition stories, reuse `_resolve_effective_transition_duration()` in `nodes/video_mixer.py` as the single source of truth for transition duration semantics, and keep the transition widget schema aligned with `tests/test_video_mixer_node.py`.
