"""ComfyUI video mixer node."""

from __future__ import annotations

import logging
from fractions import Fraction
from pathlib import Path

import numpy as np
import torch


LOGGER = logging.getLogger(__name__)
_SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv"}
_TRANSITION_TYPE_OPTIONS = ["crossfade", "hard_cut", "fade_to_black"]
_DEFAULT_AUDIO_SAMPLE_RATE = 44_100


def _resolve_video_file_paths(directory_path: str) -> list[Path]:
    normalized_path = str(directory_path).strip()
    if not normalized_path:
        raise ValueError("directory_path must be a non-empty string")

    directory = Path(normalized_path).expanduser()
    if not directory.exists():
        raise ValueError(f"Video directory does not exist: {directory}")
    if not directory.is_dir():
        raise ValueError(f"Video directory path is not a directory: {directory}")

    video_paths = sorted(
        [
            file_path
            for file_path in directory.iterdir()
            if file_path.is_file() and file_path.suffix.lower() in _SUPPORTED_VIDEO_EXTENSIONS
        ],
        key=lambda file_path: file_path.name.lower(),
    )
    if len(video_paths) < 2:
        raise ValueError(
            "Video directory must contain at least 2 video files "
            "(.mp4, .mov, .webm, .mkv): "
            f"{directory}"
        )

    return video_paths


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
    return torch.linspace(start, end, steps=steps, dtype=dtype, device=device)


def _coerce_audio_chunk_to_channels_first(audio_chunk: np.ndarray) -> torch.Tensor:
    if audio_chunk.ndim == 1:
        chunk = torch.from_numpy(audio_chunk).float().unsqueeze(0)
    elif audio_chunk.ndim == 2:
        # PyAV can return either [channels, samples] (planar) or [samples, channels].
        if audio_chunk.shape[0] <= 8:
            chunk = torch.from_numpy(audio_chunk).float()
        else:
            chunk = torch.from_numpy(audio_chunk.T).float()
    else:
        raise ValueError(f"Unsupported decoded audio chunk shape: {tuple(audio_chunk.shape)}")

    if chunk.ndim != 2:
        raise ValueError(f"Expected decoded audio chunk shape [channels, samples], got: {tuple(chunk.shape)}")
    return chunk


def _resolve_video_fps(video_stream, file_path: Path) -> float:
    average_rate = getattr(video_stream, "average_rate", None)
    if average_rate in (None, 0):
        guessed_rate = getattr(video_stream, "guessed_rate", None)
        average_rate = guessed_rate
    if average_rate in (None, 0):
        base_rate = getattr(video_stream, "base_rate", None)
        average_rate = base_rate

    if average_rate in (None, 0):
        raise ValueError(f"Could not resolve fps for video file: {file_path.name}")

    fps = float(average_rate)
    if not np.isfinite(fps) or fps <= 0.0:
        raise ValueError(f"Invalid fps for video file {file_path.name}: {average_rate}")
    return fps


def _load_video_files(video_paths: list[Path]) -> list[dict]:
    try:
        import av
    except ImportError as error:
        raise ValueError("PyAV (`av`) is required to load video files for CoolVideoMixer.") from error

    loaded_clips: list[dict] = []
    for video_path in video_paths:
        with av.open(str(video_path)) as container:
            video_stream = next((stream for stream in container.streams if stream.type == "video"), None)
            if video_stream is None:
                raise ValueError(f"Video file has no video stream: {video_path.name}")

            fps = _resolve_video_fps(video_stream, video_path)
            width = int(video_stream.width)
            height = int(video_stream.height)

            audio_stream = next((stream for stream in container.streams if stream.type == "audio"), None)
            audio_sample_rate: int | None = None
            if audio_stream is not None:
                audio_sample_rate = int(getattr(audio_stream, "rate", 0) or 0) or None

            streams_to_decode = [video_stream]
            if audio_stream is not None:
                streams_to_decode.append(audio_stream)

            decoded_frames: list[torch.Tensor] = []
            audio_chunks: list[torch.Tensor] = []
            for packet in container.demux(*streams_to_decode):
                for frame in packet.decode():
                    if frame.__class__.__name__ == "VideoFrame":
                        frame_array = frame.to_rgb().to_ndarray()
                        decoded_frames.append(torch.from_numpy(frame_array).float() / 255.0)
                    elif frame.__class__.__name__ == "AudioFrame":
                        audio_array = frame.to_ndarray()
                        audio_chunks.append(_coerce_audio_chunk_to_channels_first(audio_array))
                        if audio_sample_rate is None and getattr(frame, "sample_rate", None):
                            audio_sample_rate = int(frame.sample_rate)

            if not decoded_frames:
                raise ValueError(f"Video file has no decodable frames: {video_path.name}")

            video_frames = torch.stack(decoded_frames, dim=0)

            audio_waveform = None
            if audio_chunks:
                audio_waveform = torch.cat(audio_chunks, dim=1)

            loaded_clips.append(
                {
                    "path": str(video_path),
                    "filename": video_path.name,
                    "frames": video_frames,
                    "frame_count": int(video_frames.shape[0]),
                    "width": width,
                    "height": height,
                    "fps": fps,
                    "duration_seconds": float(video_frames.shape[0]) / fps,
                    "audio_waveform": audio_waveform,
                    "audio_sample_rate": audio_sample_rate,
                }
            )

    return loaded_clips


def _validate_homogeneous(loaded_clips: list[dict]) -> tuple[int, int, float]:
    first_clip = loaded_clips[0]
    expected_width = int(first_clip["width"])
    expected_height = int(first_clip["height"])
    expected_fps = float(first_clip["fps"])

    for clip in loaded_clips[1:]:
        if int(clip["width"]) != expected_width or int(clip["height"]) != expected_height:
            raise ValueError(
                "Video resolution mismatch for "
                f"{clip['filename']}: expected {expected_width}x{expected_height}, "
                f"got {clip['width']}x{clip['height']}"
            )
        if not np.isclose(float(clip["fps"]), expected_fps, atol=1e-6):
            raise ValueError(
                f"Video fps mismatch for {clip['filename']}: expected {expected_fps:g}, got {clip['fps']:g}"
            )

    return expected_width, expected_height, expected_fps


def _validate_transition_duration_against_adjacent_clips(
    loaded_clips: list[dict], transition_type: str, transition_duration: float
) -> None:
    if transition_type == "hard_cut":
        return

    for clip_index in range(1, len(loaded_clips)):
        previous_clip = loaded_clips[clip_index - 1]
        current_clip = loaded_clips[clip_index]
        shortest_duration = min(
            float(previous_clip["duration_seconds"]),
            float(current_clip["duration_seconds"]),
        )
        if transition_duration > shortest_duration:
            raise ValueError(
                "transition_duration is longer than the shortest adjacent clip for "
                f"{transition_type}: {transition_duration}s between "
                f"{previous_clip['filename']} and {current_clip['filename']}"
            )


def _mix_video_tracks(
    loaded_clips: list[dict],
    transition_type: str,
    transition_duration: float,
    fps: float,
) -> torch.Tensor:
    mixed_frames = loaded_clips[0]["frames"]
    transition_frames = int(round(transition_duration * fps))

    for clip_index in range(1, len(loaded_clips)):
        next_frames = loaded_clips[clip_index]["frames"]
        if transition_type == "hard_cut" or transition_frames <= 0:
            mixed_frames = torch.cat([mixed_frames, next_frames], dim=0)
            continue

        shortest_pair_frames = min(
            int(loaded_clips[clip_index - 1]["frame_count"]),
            int(next_frames.shape[0]),
        )
        if transition_frames > shortest_pair_frames:
            raise ValueError(
                "transition_duration is longer than the shortest adjacent clip for "
                f"{transition_type}: {transition_duration}s"
            )

        fade_out = _build_linear_fade(
            1.0,
            0.0,
            transition_frames,
            dtype=mixed_frames.dtype,
            device=mixed_frames.device,
        ).view(-1, 1, 1, 1)
        fade_in = _build_linear_fade(
            0.0,
            1.0,
            transition_frames,
            dtype=mixed_frames.dtype,
            device=mixed_frames.device,
        ).view(-1, 1, 1, 1)

        if transition_type == "crossfade":
            overlap = mixed_frames[-transition_frames:] * fade_out + next_frames[:transition_frames] * fade_in
            mixed_frames = torch.cat(
                [
                    mixed_frames[:-transition_frames],
                    overlap,
                    next_frames[transition_frames:],
                ],
                dim=0,
            )
            continue

        if transition_type == "fade_to_black":
            black_gap = torch.zeros(
                (transition_frames, mixed_frames.shape[1], mixed_frames.shape[2], mixed_frames.shape[3]),
                dtype=mixed_frames.dtype,
                device=mixed_frames.device,
            )
            mixed_frames = torch.cat(
                [
                    mixed_frames[:-transition_frames],
                    mixed_frames[-transition_frames:] * fade_out,
                    black_gap,
                    next_frames[:transition_frames] * fade_in,
                    next_frames[transition_frames:],
                ],
                dim=0,
            )
            continue

        raise ValueError(
            f"Unsupported transition_type: {transition_type}. "
            f"Expected one of: {', '.join(_TRANSITION_TYPE_OPTIONS)}"
        )

    return mixed_frames


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


def _resample_waveform_linear(
    waveform: torch.Tensor,
    *,
    source_sample_rate: int,
    target_sample_rate: int,
) -> torch.Tensor:
    if source_sample_rate == target_sample_rate:
        return waveform

    source_samples = int(waveform.shape[1])
    if source_samples == 0:
        return waveform

    target_samples = int(round(source_samples * (float(target_sample_rate) / float(source_sample_rate))))
    if target_samples <= 0:
        return waveform[:, :0]
    if target_samples == source_samples:
        return waveform
    if source_samples == 1:
        return waveform.repeat(1, target_samples)

    positions = torch.linspace(
        0,
        source_samples - 1,
        target_samples,
        dtype=torch.float32,
        device=waveform.device,
    )
    lower_indices = torch.floor(positions).to(dtype=torch.long)
    upper_indices = torch.clamp(lower_indices + 1, max=source_samples - 1)
    upper_weights = positions - lower_indices.to(dtype=torch.float32)
    lower_weights = 1.0 - upper_weights

    return waveform[:, lower_indices] * lower_weights.unsqueeze(0) + waveform[:, upper_indices] * upper_weights.unsqueeze(0)


def _prepare_audio_tracks_for_mixing(loaded_clips: list[dict], fps: float) -> tuple[list[dict], int]:
    target_sample_rate = _DEFAULT_AUDIO_SAMPLE_RATE
    for clip in loaded_clips:
        clip_sample_rate = clip.get("audio_sample_rate")
        if clip_sample_rate:
            target_sample_rate = int(clip_sample_rate)
            break

    prepared_tracks: list[dict] = []
    for clip in loaded_clips:
        clip_duration_seconds = float(clip["frame_count"]) / fps
        audio_waveform = clip.get("audio_waveform")
        clip_sample_rate = int(clip.get("audio_sample_rate") or target_sample_rate)

        if audio_waveform is None:
            sample_count = int(round(clip_duration_seconds * target_sample_rate))
            waveform = torch.zeros((2, sample_count), dtype=torch.float32)
            LOGGER.warning(
                "[CoolVideoMixer] no audio in %s; synthesizing %d silent samples at %d Hz",
                clip["filename"],
                sample_count,
                target_sample_rate,
            )
        else:
            waveform = _normalize_waveform_to_stereo(audio_waveform.float())
            waveform = _resample_waveform_linear(
                waveform,
                source_sample_rate=clip_sample_rate,
                target_sample_rate=target_sample_rate,
            )

        prepared_tracks.append(
            {
                "filename": clip["filename"],
                "waveform": waveform,
            }
        )

    return prepared_tracks, target_sample_rate


def _resolve_audio_transition_type(transition_type: str) -> str:
    if transition_type == "fade_to_black":
        return "fade_to_silence"
    return transition_type


def _mix_audio_tracks(
    prepared_audio_tracks: list[dict],
    transition_type: str,
    transition_duration: float,
    target_sample_rate: int,
) -> torch.Tensor:
    mixed_waveform = prepared_audio_tracks[0]["waveform"]
    transition_samples = int(round(transition_duration * target_sample_rate))

    for track_index in range(1, len(prepared_audio_tracks)):
        next_waveform = prepared_audio_tracks[track_index]["waveform"]
        if transition_type == "hard_cut" or transition_samples <= 0:
            mixed_waveform = torch.cat([mixed_waveform, next_waveform], dim=1)
            continue

        shortest_pair_samples = min(
            int(prepared_audio_tracks[track_index - 1]["waveform"].shape[1]),
            int(next_waveform.shape[1]),
        )
        if transition_samples > shortest_pair_samples:
            raise ValueError(
                "transition_duration is longer than the shortest adjacent track for "
                f"{transition_type}: {transition_duration}s"
            )

        fade_out = _build_linear_fade(
            1.0,
            0.0,
            transition_samples,
            dtype=mixed_waveform.dtype,
            device=mixed_waveform.device,
        ).unsqueeze(0)
        fade_in = _build_linear_fade(
            0.0,
            1.0,
            transition_samples,
            dtype=mixed_waveform.dtype,
            device=mixed_waveform.device,
        ).unsqueeze(0)

        if transition_type == "crossfade":
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
            "Expected one of: crossfade, hard_cut, fade_to_silence"
        )

    return mixed_waveform


class CoolVideoMixer:
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

    RETURN_TYPES = ("VIDEO",)
    RETURN_NAMES = ("video",)
    FUNCTION = "execute"
    CATEGORY = "CoolEffects/video"

    def execute(self, directory_path, transition_type="crossfade", transition_duration=1.0):
        video_paths = _resolve_video_file_paths(directory_path)
        loaded_clips = _load_video_files(video_paths)
        _, _, fps = _validate_homogeneous(loaded_clips)

        effective_transition_duration = _resolve_effective_transition_duration(
            transition_type, transition_duration
        )
        _validate_transition_duration_against_adjacent_clips(
            loaded_clips,
            transition_type,
            effective_transition_duration,
        )

        mixed_frames = _mix_video_tracks(
            loaded_clips,
            transition_type,
            effective_transition_duration,
            fps,
        )
        prepared_audio_tracks, target_audio_sample_rate = _prepare_audio_tracks_for_mixing(
            loaded_clips, fps
        )
        mixed_audio_waveform = _mix_audio_tracks(
            prepared_audio_tracks,
            _resolve_audio_transition_type(transition_type),
            effective_transition_duration,
            target_audio_sample_rate,
        )
        mixed_audio = {
            "waveform": mixed_audio_waveform.unsqueeze(0),
            "sample_rate": target_audio_sample_rate,
        }

        try:
            from comfy_api.latest import InputImpl, Types  # type: ignore
        except ImportError as error:
            raise ValueError(
                "comfy_api.latest is required to build VIDEO output for CoolVideoMixer."
            ) from error

        video = InputImpl.VideoFromComponents(
            Types.VideoComponents(
                images=mixed_frames,
                audio=mixed_audio,
                frame_rate=Fraction(fps),
            )
        )
        return (video,)
