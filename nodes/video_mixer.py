"""ComfyUI video mixer node."""

from __future__ import annotations

import logging
import uuid
from collections import deque
from fractions import Fraction
from pathlib import Path
from typing import Iterator

import numpy as np
import torch


LOGGER = logging.getLogger(__name__)
_SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv"}
_TRANSITION_TYPE_OPTIONS = ["crossfade", "hard_cut", "fade_to_black"]
_DEFAULT_AUDIO_SAMPLE_RATE = 44_100
_DEFAULT_AAC_FRAME_SIZE = 1024


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


def _probe_clip_metadata(video_path: Path) -> dict:
    """Open a video file and return metadata without decoding frames."""
    try:
        import av
    except ImportError as error:
        raise ValueError("PyAV (`av`) is required for CoolVideoMixer.") from error

    with av.open(str(video_path)) as container:
        video_stream = next(
            (stream for stream in container.streams if stream.type == "video"),
            None,
        )
        if video_stream is None:
            raise ValueError(f"Video file has no video stream: {video_path.name}")

        fps = _resolve_video_fps(video_stream, video_path)
        width = int(video_stream.width)
        height = int(video_stream.height)

        duration_seconds: float | None = None
        stream_duration = getattr(video_stream, "duration", None)
        stream_time_base = getattr(video_stream, "time_base", None)
        if stream_duration is not None and stream_time_base is not None:
            try:
                duration_seconds = float(stream_duration * stream_time_base)
            except (TypeError, ValueError):
                duration_seconds = None
        if duration_seconds is None and container.duration is not None:
            duration_seconds = float(container.duration / av.time_base)
        if duration_seconds is None:
            stream_frames = getattr(video_stream, "frames", 0) or 0
            if stream_frames > 0 and fps > 0:
                duration_seconds = float(stream_frames) / fps
        if duration_seconds is None or duration_seconds <= 0.0:
            raise ValueError(
                f"Could not resolve duration for video file: {video_path.name}"
            )

        audio_stream = next(
            (stream for stream in container.streams if stream.type == "audio"),
            None,
        )
        audio_sample_rate = None
        if audio_stream is not None:
            rate = int(getattr(audio_stream, "rate", 0) or 0)
            audio_sample_rate = rate or None

        return {
            "path": str(video_path),
            "filename": video_path.name,
            "width": width,
            "height": height,
            "fps": fps,
            "duration_seconds": duration_seconds,
            "frame_count": int(round(duration_seconds * fps)),
            "audio_sample_rate": audio_sample_rate,
        }


def _iter_clip_video_frames(video_path: Path) -> Iterator[torch.Tensor]:
    """Yield [H, W, 3] float32 RGB frames one at a time, without buffering the full clip."""
    import av

    with av.open(str(video_path)) as container:
        video_stream = next(
            (stream for stream in container.streams if stream.type == "video"),
            None,
        )
        if video_stream is None:
            raise ValueError(f"Video file has no video stream: {video_path.name}")
        try:
            video_stream.thread_type = "AUTO"
        except Exception:
            pass
        for frame in container.decode(video_stream):
            frame_array = frame.to_rgb().to_ndarray()
            yield torch.from_numpy(frame_array).to(dtype=torch.float32).div_(255.0)


def _load_clip_audio(video_path: Path, target_sample_rate: int) -> torch.Tensor | None:
    """Decode a clip's audio, resample to stereo at target_sample_rate. Returns [2, N] or None."""
    import av

    chunks: list[torch.Tensor] = []
    source_sample_rate = 0
    with av.open(str(video_path)) as container:
        audio_stream = next(
            (stream for stream in container.streams if stream.type == "audio"),
            None,
        )
        if audio_stream is None:
            return None
        source_sample_rate = int(getattr(audio_stream, "rate", 0) or 0)
        for frame in container.decode(audio_stream):
            audio_array = frame.to_ndarray()
            chunks.append(_coerce_audio_chunk_to_channels_first(audio_array))
            if source_sample_rate == 0 and getattr(frame, "sample_rate", None):
                source_sample_rate = int(frame.sample_rate)

    if not chunks:
        return None

    waveform = _normalize_waveform_to_stereo(torch.cat(chunks, dim=1))
    if source_sample_rate <= 0:
        source_sample_rate = target_sample_rate
    return _resample_waveform_linear(
        waveform,
        source_sample_rate=source_sample_rate,
        target_sample_rate=target_sample_rate,
    )


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
    """Reference in-memory mixer kept for unit tests of the transition math.

    The runtime node no longer uses this path; see `_stream_mix_to_file`.
    """
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
    """Reference in-memory audio mixer kept for unit tests of the transition math."""
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


class _StreamingMixWriter:
    """Encodes mixed video/audio to an mp4 file as frames/samples arrive.

    Keeps peak memory bounded to a single frame (video) plus a small audio FIFO,
    regardless of total output duration.
    """

    def __init__(
        self,
        output_path: Path,
        *,
        width: int,
        height: int,
        fps: float,
        audio_sample_rate: int,
    ) -> None:
        try:
            import av
        except ImportError as error:
            raise ValueError("PyAV (`av`) is required for CoolVideoMixer.") from error

        self._av = av
        self._container = av.open(str(output_path), mode="w")

        frame_rate = Fraction(float(fps)).limit_denominator(60000)
        self._video_stream = self._container.add_stream("libx264", rate=frame_rate)
        self._video_stream.width = int(width)
        self._video_stream.height = int(height)
        self._video_stream.pix_fmt = "yuv420p"
        self._video_stream.options = {"crf": "20", "preset": "medium"}

        self._audio_sample_rate = int(audio_sample_rate)
        self._audio_stream = self._container.add_stream(
            "aac", rate=self._audio_sample_rate, layout="stereo"
        )
        self._audio_fifo = av.AudioFifo()
        self._audio_pts = 0

    def write_video_frame(self, frame_tensor: torch.Tensor) -> None:
        frame_u8 = (
            (frame_tensor.clamp(0.0, 1.0) * 255.0)
            .to(torch.uint8)
            .contiguous()
            .cpu()
            .numpy()
        )
        av_frame = self._av.VideoFrame.from_ndarray(frame_u8, format="rgb24")
        av_frame = av_frame.reformat(format="yuv420p")
        for packet in self._video_stream.encode(av_frame):
            self._container.mux(packet)

    def write_audio_chunk(self, waveform: torch.Tensor) -> None:
        if waveform is None or waveform.numel() == 0 or waveform.shape[-1] == 0:
            return
        samples = waveform.contiguous().to(torch.float32).cpu().numpy()
        av_frame = self._av.AudioFrame.from_ndarray(
            samples, format="fltp", layout="stereo"
        )
        av_frame.sample_rate = self._audio_sample_rate
        av_frame.pts = self._audio_pts
        self._audio_pts += int(samples.shape[1])
        self._audio_fifo.write(av_frame)
        self._drain_audio_fifo(final=False)

    def _drain_audio_fifo(self, *, final: bool) -> None:
        frame_size = (
            getattr(self._audio_stream.codec_context, "frame_size", None)
            or _DEFAULT_AAC_FRAME_SIZE
        )
        while self._audio_fifo.samples >= frame_size:
            out_frame = self._audio_fifo.read(frame_size)
            for packet in self._audio_stream.encode(out_frame):
                self._container.mux(packet)
        if final and self._audio_fifo.samples > 0:
            # Drop the trailing partial frame; AAC cannot encode a partial frame and the
            # resulting few milliseconds of audio loss at the end are imperceptible.
            self._audio_fifo.read(self._audio_fifo.samples)

    def close(self) -> None:
        try:
            self._drain_audio_fifo(final=True)
            for packet in self._video_stream.encode():
                self._container.mux(packet)
            for packet in self._audio_stream.encode():
                self._container.mux(packet)
        finally:
            self._container.close()


def _stream_mix_video_transition(
    writer: _StreamingMixWriter,
    *,
    tail_frames: list[torch.Tensor],
    head_frames: list[torch.Tensor],
    transition_type: str,
) -> None:
    transition_frames = len(tail_frames)
    if len(head_frames) != transition_frames:
        raise ValueError(
            f"tail/head frame count mismatch: {transition_frames} vs {len(head_frames)}"
        )
    if transition_frames == 0:
        return

    fade_out = torch.linspace(1.0, 0.0, transition_frames, dtype=torch.float32)
    fade_in = torch.linspace(0.0, 1.0, transition_frames, dtype=torch.float32)

    if transition_type == "crossfade":
        for i in range(transition_frames):
            blended = tail_frames[i] * float(fade_out[i]) + head_frames[i] * float(fade_in[i])
            writer.write_video_frame(blended)
        return

    if transition_type == "fade_to_black":
        for i in range(transition_frames):
            writer.write_video_frame(tail_frames[i] * float(fade_out[i]))
        black_frame = torch.zeros_like(head_frames[0])
        for _ in range(transition_frames):
            writer.write_video_frame(black_frame)
        for i in range(transition_frames):
            writer.write_video_frame(head_frames[i] * float(fade_in[i]))
        return

    raise ValueError(
        f"Unsupported transition_type: {transition_type}. "
        f"Expected one of: {', '.join(_TRANSITION_TYPE_OPTIONS)}"
    )


def _stream_mix_audio_transition(
    writer: _StreamingMixWriter,
    *,
    tail_audio: torch.Tensor,
    head_audio: torch.Tensor,
    transition_type: str,
) -> None:
    transition_samples = int(tail_audio.shape[1])
    if int(head_audio.shape[1]) != transition_samples:
        raise ValueError(
            f"tail/head audio sample count mismatch: {transition_samples} vs {int(head_audio.shape[1])}"
        )
    if transition_samples == 0:
        return

    fade_out = torch.linspace(1.0, 0.0, transition_samples, dtype=torch.float32).unsqueeze(0)
    fade_in = torch.linspace(0.0, 1.0, transition_samples, dtype=torch.float32).unsqueeze(0)

    if transition_type == "crossfade":
        writer.write_audio_chunk(tail_audio * fade_out + head_audio * fade_in)
        return

    if transition_type == "fade_to_silence":
        writer.write_audio_chunk(tail_audio * fade_out)
        writer.write_audio_chunk(torch.zeros_like(tail_audio))
        writer.write_audio_chunk(head_audio * fade_in)
        return

    raise ValueError(
        f"Unsupported audio transition_type: {transition_type}. "
        "Expected one of: crossfade, hard_cut, fade_to_silence"
    )


def _stream_clip_audio(
    writer: _StreamingMixWriter,
    *,
    clip_path: Path,
    clip_metadata: dict,
    target_sample_rate: int,
    transition_samples: int,
    audio_transition_type: str,
    is_first: bool,
    is_last: bool,
    pending_audio_tail: torch.Tensor | None,
) -> torch.Tensor | None:
    """Mix one clip's audio into the writer and return the new pending tail (or None)."""
    waveform = _load_clip_audio(clip_path, target_sample_rate)
    if waveform is None:
        silent_samples = int(round(float(clip_metadata["duration_seconds"]) * target_sample_rate))
        waveform = torch.zeros((2, silent_samples), dtype=torch.float32)
        LOGGER.warning(
            "[CoolVideoMixer] no audio in %s; synthesizing %d silent samples at %d Hz",
            clip_metadata["filename"],
            silent_samples,
            target_sample_rate,
        )

    if transition_samples <= 0 or audio_transition_type == "hard_cut":
        writer.write_audio_chunk(waveform)
        return None

    if is_first:
        if waveform.shape[1] <= transition_samples:
            return waveform
        writer.write_audio_chunk(waveform[:, :-transition_samples])
        return waveform[:, -transition_samples:]

    head_audio = waveform[:, :transition_samples]
    body_audio = waveform[:, transition_samples:]

    assert pending_audio_tail is not None
    _stream_mix_audio_transition(
        writer,
        tail_audio=pending_audio_tail,
        head_audio=head_audio,
        transition_type=audio_transition_type,
    )

    if is_last:
        writer.write_audio_chunk(body_audio)
        return None

    if body_audio.shape[1] <= transition_samples:
        return body_audio
    writer.write_audio_chunk(body_audio[:, :-transition_samples])
    return body_audio[:, -transition_samples:]


def _stream_clip_video(
    writer: _StreamingMixWriter,
    *,
    clip_path: Path,
    transition_frames: int,
    transition_type: str,
    is_first: bool,
    is_last: bool,
    pending_video_tail: deque[torch.Tensor],
) -> deque[torch.Tensor]:
    """Mix one clip's video into the writer and return the new pending tail deque."""
    frame_iter = _iter_clip_video_frames(clip_path)
    uses_transition = transition_frames > 0 and transition_type != "hard_cut"

    if uses_transition and not is_first:
        head_frames: list[torch.Tensor] = []
        for _ in range(transition_frames):
            try:
                head_frames.append(next(frame_iter))
            except StopIteration:
                break
        if len(head_frames) < transition_frames:
            raise ValueError(
                f"Clip {clip_path.name} has too few frames for the requested transition"
            )
        tail_frames = list(pending_video_tail)
        pending_video_tail.clear()
        _stream_mix_video_transition(
            writer,
            tail_frames=tail_frames,
            head_frames=head_frames,
            transition_type=transition_type,
        )

    tail_hold = transition_frames if (uses_transition and not is_last) else 0
    rolling: deque[torch.Tensor] = deque()
    for frame in frame_iter:
        if tail_hold > 0:
            rolling.append(frame)
            if len(rolling) > tail_hold:
                writer.write_video_frame(rolling.popleft())
        else:
            writer.write_video_frame(frame)

    if is_last:
        while rolling:
            writer.write_video_frame(rolling.popleft())
        return deque()

    return rolling


def _stream_mix_to_file(
    *,
    video_paths: list[Path],
    clips_metadata: list[dict],
    transition_type: str,
    transition_duration: float,
    fps: float,
    target_audio_sample_rate: int,
    output_path: Path,
) -> None:
    transition_frames = int(round(transition_duration * fps))
    transition_samples = int(round(transition_duration * target_audio_sample_rate))
    audio_transition_type = _resolve_audio_transition_type(transition_type)

    writer = _StreamingMixWriter(
        output_path,
        width=int(clips_metadata[0]["width"]),
        height=int(clips_metadata[0]["height"]),
        fps=fps,
        audio_sample_rate=target_audio_sample_rate,
    )

    try:
        pending_video_tail: deque[torch.Tensor] = deque()
        pending_audio_tail: torch.Tensor | None = None

        for clip_index, clip_path in enumerate(video_paths):
            is_first = clip_index == 0
            is_last = clip_index == len(video_paths) - 1

            pending_video_tail = _stream_clip_video(
                writer,
                clip_path=clip_path,
                transition_frames=transition_frames,
                transition_type=transition_type,
                is_first=is_first,
                is_last=is_last,
                pending_video_tail=pending_video_tail,
            )

            pending_audio_tail = _stream_clip_audio(
                writer,
                clip_path=clip_path,
                clip_metadata=clips_metadata[clip_index],
                target_sample_rate=target_audio_sample_rate,
                transition_samples=transition_samples,
                audio_transition_type=audio_transition_type,
                is_first=is_first,
                is_last=is_last,
                pending_audio_tail=pending_audio_tail,
            )
    finally:
        writer.close()


def _resolve_output_directory() -> Path:
    try:
        import folder_paths  # type: ignore

        return Path(folder_paths.get_temp_directory())
    except ImportError:
        import tempfile

        return Path(tempfile.gettempdir()) / "comfyui-cool-effects"


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
        clips_metadata = [_probe_clip_metadata(path) for path in video_paths]
        _, _, fps = _validate_homogeneous(clips_metadata)

        effective_transition_duration = _resolve_effective_transition_duration(
            transition_type, transition_duration
        )
        _validate_transition_duration_against_adjacent_clips(
            clips_metadata, transition_type, effective_transition_duration
        )

        target_audio_sample_rate = _DEFAULT_AUDIO_SAMPLE_RATE
        for metadata in clips_metadata:
            rate = metadata.get("audio_sample_rate")
            if rate:
                target_audio_sample_rate = int(rate)
                break

        output_dir = _resolve_output_directory()
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"cool-effects-mixer-{uuid.uuid4().hex}.mp4"

        _stream_mix_to_file(
            video_paths=video_paths,
            clips_metadata=clips_metadata,
            transition_type=transition_type,
            transition_duration=effective_transition_duration,
            fps=fps,
            target_audio_sample_rate=target_audio_sample_rate,
            output_path=output_path,
        )

        try:
            from comfy_api.latest import InputImpl  # type: ignore
        except ImportError as error:
            raise ValueError(
                "comfy_api.latest is required to build VIDEO output for CoolVideoMixer."
            ) from error

        return (InputImpl.VideoFromFile(str(output_path)),)
