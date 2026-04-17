# Requirement: CoolAudioMixer Node

## Context
ComfyUI-CoolEffects currently supports audio-reactive effects (bass zoom, freq warp, waveform, etc.) but has no way to mix multiple audio tracks before feeding them into the pipeline. Users who want to combine several audio files — e.g. a music bed + a voice-over, or multiple music segments — must pre-mix outside ComfyUI. The `CoolAudioMixer` node closes this gap by reading all audio files from a directory, applying transition effects between tracks, and delivering a single merged AUDIO output compatible with `CoolVideoGenerator`.

## Goals
- Allow users to combine multiple audio tracks directly in ComfyUI without external tools.
- Support three transition modes (Crossfade, Hard Cut, Fade to Silence) to control how tracks flow into each other.
- Output a standard ComfyUI AUDIO object that connects to any node expecting AUDIO input.

## User Stories

### US-001: Load audio tracks from a directory
**As a** ComfyUI creator, **I want** to point the node at a directory path and have it automatically load all audio files found there **so that** I don't need to wire individual files one by one.

**Acceptance Criteria:**
- [ ] Node has a `directory_path` STRING input (text field).
- [ ] Node scans the directory for audio files with extensions `.wav`, `.mp3`, `.flac`, `.ogg` (case-insensitive).
- [ ] Files are loaded and sorted alphabetically by filename.
- [ ] If the directory contains fewer than 2 audio files, the node raises a `ValueError` with a clear message.
- [ ] If the directory does not exist, the node raises a `ValueError` with a clear message.
- [ ] Typecheck / lint passes.

### US-002: Select transition effect and configure its duration
**As a** ComfyUI creator, **I want** to choose a transition type and set its duration **so that** I can control how tracks blend together.

**Acceptance Criteria:**
- [ ] Node has a `transition_type` COMBO input with options: `["crossfade", "hard_cut", "fade_to_silence"]`.
- [ ] Node has a `transition_duration` FLOAT input (range 0.1–10.0 s, default 1.0 s, step 0.1).
- [ ] `transition_duration` is ignored (has no effect) when `transition_type` is `hard_cut`.
- [ ] Typecheck / lint passes.

### US-003: Mix tracks with the selected transition
**As a** ComfyUI creator, **I want** the node to concatenate all loaded tracks applying the chosen transition between each pair **so that** the output audio sounds like a smooth mix rather than isolated segments.

**Acceptance Criteria:**
- [ ] **Crossfade:** the last `transition_duration` seconds of track N overlap with the first `transition_duration` seconds of track N+1; volume of track N fades linearly to 0 while volume of track N+1 fades linearly from 0.
- [ ] **Hard Cut:** track N+1 starts immediately after the last sample of track N with no gap and no overlap.
- [ ] **Fade to Silence:** track N fades out to silence over `transition_duration` seconds, then track N+1 fades in from silence over `transition_duration` seconds (gap of silence between tracks).
- [ ] Tracks with different sample rates are resampled to the sample rate of the first loaded track before mixing.
- [ ] Tracks with different channel counts are normalised to stereo (2 channels) before mixing.
- [ ] Typecheck / lint passes.

### US-004: Output mixed AUDIO
**As a** ComfyUI creator, **I want** the node to output a standard AUDIO object **so that** I can connect it directly to `CoolVideoGenerator` or any other AUDIO-consuming node.

**Acceptance Criteria:**
- [ ] Node output type is `AUDIO` (ComfyUI standard: `{"waveform": Tensor[1, channels, samples], "sample_rate": int}`).
- [ ] The mixed audio can be connected to `CoolVideoGenerator`'s AUDIO input and the generated video plays the mixed audio correctly.
- [ ] Visually verified in ComfyUI: node executes without error, output connects to `CoolVideoGenerator`, video has mixed audio.
- [ ] Typecheck / lint passes.

## Functional Requirements
- FR-1: Node class name is `CoolAudioMixer`; registered as `"CoolAudioMixer"` in `NODE_CLASS_MAPPINGS`.
- FR-2: Node display name is `"Cool Audio Mixer"`.
- FR-3: Node category is `"CoolEffects/audio"`.
- FR-4: Node file is `nodes/audio_mixer.py`; JS extension (if any) is `web/audio_mixer.js`.
- FR-5: Audio file loading uses `torchaudio.load()` (add `torchaudio` to `requirements.txt` if not already present; check first).
- FR-6: Resampling uses `torchaudio.functional.resample()`.
- FR-7: All waveform tensors are normalised to shape `[channels, samples]` (2D) before mixing; final output is wrapped as `[1, channels, samples]` (3D) per ComfyUI AUDIO convention.
- FR-8: Crossfade overlap must not exceed the duration of the shorter of the two adjacent tracks; raise `ValueError` if `transition_duration` is longer than the shortest track.
- FR-9: Node is registered in `__init__.py` following the existing `importlib.util.spec_from_file_location` pattern.

## Non-Goals (Out of Scope)
- Volume/gain adjustment per track.
- Fade in / fade out on the first or last track of the mix.
- Audio normalization or peak limiting of the final mix.
- UI preview of the mixed audio waveform inside the node.
- Support for video files as audio sources.
- Explicit track ordering UI (order is always alphabetical by filename).

## Open Questions
- Should `torchaudio` be added to `requirements.txt`, or is there a preferred alternative already available in the environment (e.g. `soundfile` + `scipy`)?
