"""ComfyUI audio mixer node."""

from pathlib import Path

import torch


_SUPPORTED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg"}
_TRANSITION_TYPE_OPTIONS = ["crossfade", "hard_cut", "fade_to_silence"]


def _resolve_audio_file_paths(directory_path: str) -> list[Path]:
    normalized_path = str(directory_path).strip()
    if not normalized_path:
        raise ValueError("directory_path must be a non-empty string")

    directory = Path(normalized_path).expanduser()
    if not directory.exists():
        raise ValueError(f"Audio directory does not exist: {directory}")
    if not directory.is_dir():
        raise ValueError(f"Audio directory path is not a directory: {directory}")

    audio_paths = sorted(
        [
            file_path
            for file_path in directory.iterdir()
            if file_path.is_file() and file_path.suffix.lower() in _SUPPORTED_AUDIO_EXTENSIONS
        ],
        key=lambda file_path: file_path.name.lower(),
    )
    if len(audio_paths) < 2:
        raise ValueError(
            f"Audio directory must contain at least 2 audio files (.wav, .mp3, .flac, .ogg): {directory}"
        )

    return audio_paths


def _load_audio_files(audio_paths: list[Path]) -> list[dict]:
    try:
        import torchaudio
    except ImportError as error:
        raise ValueError("torchaudio is required to load audio files for CoolAudioMixer.") from error

    loaded_tracks: list[dict] = []
    for audio_path in audio_paths:
        waveform, sample_rate = torchaudio.load(str(audio_path))
        loaded_tracks.append(
            {
                "path": str(audio_path),
                "filename": audio_path.name,
                "waveform": waveform,
                "sample_rate": int(sample_rate),
            }
        )
    return loaded_tracks


def _normalize_waveform_to_stereo(waveform: torch.Tensor) -> torch.Tensor:
    if waveform.ndim == 1:
        waveform = waveform.unsqueeze(0)
    if waveform.ndim != 2:
        raise ValueError(
            f"Expected waveform tensor shape [channels, samples], got: {tuple(waveform.shape)}"
        )

    channels = waveform.shape[0]
    if channels == 1:
        return waveform.repeat(2, 1)
    if channels >= 2:
        return waveform[:2, :]

    raise ValueError("Waveform must contain at least one channel")


def _prepare_tracks_for_mixing(loaded_tracks: list[dict]) -> tuple[list[dict], int]:
    try:
        import torchaudio
    except ImportError as error:
        raise ValueError("torchaudio is required to mix audio for CoolAudioMixer.") from error

    target_sample_rate = int(loaded_tracks[0]["sample_rate"])
    prepared_tracks: list[dict] = []
    for track in loaded_tracks:
        waveform = _normalize_waveform_to_stereo(track["waveform"])
        sample_rate = int(track["sample_rate"])
        if sample_rate != target_sample_rate:
            waveform = torchaudio.functional.resample(
                waveform,
                orig_freq=sample_rate,
                new_freq=target_sample_rate,
            )
            sample_rate = target_sample_rate
        prepared_track = dict(track)
        prepared_track["waveform"] = waveform
        prepared_track["sample_rate"] = sample_rate
        prepared_tracks.append(prepared_track)

    return prepared_tracks, target_sample_rate


def _resolve_effective_transition_duration(transition_type: str, transition_duration: float) -> float:
    if transition_type not in _TRANSITION_TYPE_OPTIONS:
        raise ValueError(
            f"Unsupported transition_type: {transition_type}. "
            f"Expected one of: {', '.join(_TRANSITION_TYPE_OPTIONS)}"
        )

    if transition_type == "hard_cut":
        return 0.0

    return float(transition_duration)


def _build_linear_fade(
    start: float,
    end: float,
    steps: int,
    *,
    dtype: torch.dtype,
    device: torch.device,
) -> torch.Tensor:
    return torch.linspace(start, end, steps=steps, dtype=dtype, device=device).unsqueeze(0)


def _mix_prepared_tracks(
    prepared_tracks: list[dict],
    transition_type: str,
    transition_duration: float,
    target_sample_rate: int,
) -> torch.Tensor:
    mixed_waveform = prepared_tracks[0]["waveform"]
    transition_samples = int(round(transition_duration * target_sample_rate))

    for track_index in range(1, len(prepared_tracks)):
        next_waveform = prepared_tracks[track_index]["waveform"]
        if transition_type == "hard_cut" or transition_samples <= 0:
            mixed_waveform = torch.cat([mixed_waveform, next_waveform], dim=1)
            continue

        previous_original_waveform = prepared_tracks[track_index - 1]["waveform"]
        shortest_pair_samples = min(previous_original_waveform.shape[1], next_waveform.shape[1])
        if transition_samples > shortest_pair_samples:
            raise ValueError(
                "transition_duration is longer than the shortest adjacent track for "
                f"{transition_type}: {transition_duration}s"
            )

        if transition_type == "crossfade":
            fade_out = _build_linear_fade(
                1.0,
                0.0,
                transition_samples,
                dtype=mixed_waveform.dtype,
                device=mixed_waveform.device,
            )
            fade_in = _build_linear_fade(
                0.0,
                1.0,
                transition_samples,
                dtype=mixed_waveform.dtype,
                device=mixed_waveform.device,
            )
            overlap = (
                mixed_waveform[:, -transition_samples:] * fade_out
                + next_waveform[:, :transition_samples] * fade_in
            )
            mixed_waveform = torch.cat(
                [
                    mixed_waveform[:, :-transition_samples],
                    overlap,
                    next_waveform[:, transition_samples:],
                ],
                dim=1,
            )
            continue

        if transition_type == "fade_to_silence":
            fade_out = _build_linear_fade(
                1.0,
                0.0,
                transition_samples,
                dtype=mixed_waveform.dtype,
                device=mixed_waveform.device,
            )
            fade_in = _build_linear_fade(
                0.0,
                1.0,
                transition_samples,
                dtype=mixed_waveform.dtype,
                device=mixed_waveform.device,
            )
            silence = torch.zeros(
                (mixed_waveform.shape[0], transition_samples),
                dtype=mixed_waveform.dtype,
                device=mixed_waveform.device,
            )
            mixed_waveform = torch.cat(
                [
                    mixed_waveform[:, :-transition_samples],
                    mixed_waveform[:, -transition_samples:] * fade_out,
                    silence,
                    next_waveform[:, :transition_samples] * fade_in,
                    next_waveform[:, transition_samples:],
                ],
                dim=1,
            )
            continue

        raise ValueError(
            f"Unsupported transition_type: {transition_type}. "
            f"Expected one of: {', '.join(_TRANSITION_TYPE_OPTIONS)}"
        )

    return mixed_waveform


class CoolAudioMixer:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "directory_path": ("STRING", {"default": ""}),
                "transition_type": (_TRANSITION_TYPE_OPTIONS, {"default": "crossfade"}),
                "transition_duration": (
                    "FLOAT",
                    {"default": 1.0, "min": 0.1, "max": 10.0, "step": 0.1},
                ),
            }
        }

    RETURN_TYPES = ("AUDIO_TRACKS",)
    RETURN_NAMES = ("audio_tracks",)
    FUNCTION = "execute"
    CATEGORY = "CoolEffects/audio"

    def execute(self, directory_path, transition_type="crossfade", transition_duration=1.0):
        audio_paths = _resolve_audio_file_paths(directory_path)
        loaded_tracks = _load_audio_files(audio_paths)
        prepared_tracks, target_sample_rate = _prepare_tracks_for_mixing(loaded_tracks)
        effective_transition_duration = _resolve_effective_transition_duration(
            transition_type, transition_duration
        )
        mixed_waveform = _mix_prepared_tracks(
            prepared_tracks,
            transition_type,
            effective_transition_duration,
            target_sample_rate,
        )
        for track in prepared_tracks:
            track["transition_type"] = transition_type
            track["transition_duration_seconds"] = effective_transition_duration
        prepared_tracks[0]["mixed_waveform"] = mixed_waveform
        prepared_tracks[0]["mixed_sample_rate"] = target_sample_rate
        return (prepared_tracks,)
