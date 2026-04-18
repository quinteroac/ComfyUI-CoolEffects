"""Audio feature extraction utilities for audio-reactive effect nodes."""

from __future__ import annotations

import math
from collections.abc import Mapping

import numpy as np

WAVEFORM_SAMPLE_COUNT = 256

# Frequency (Hz) of the synthetic preview sine wave shown when no audio is connected.
_PREVIEW_SINE_HZ = 2.0


def _default_feature_frame() -> dict[str, float | bool | list[float]]:
    return {
        "rms": 0.0,
        "beat": False,
        "bass": 0.0,
        "mid": 0.0,
        "treble": 0.0,
        "waveform": [0.0] * WAVEFORM_SAMPLE_COUNT,
    }


def _preview_feature_frame(frame_index: int, fps: float) -> dict[str, float | bool | list[float]]:
    """Synthetic animated frame shown when no audio is connected.

    Generates a moving sine-wave waveform so audio-reactive effects render a
    visible preview instead of a static flat line.
    """
    t = frame_index / max(fps, 1.0)
    phase = 2.0 * math.pi * _PREVIEW_SINE_HZ * t
    waveform = [
        math.sin(phase + 2.0 * math.pi * i / WAVEFORM_SAMPLE_COUNT)
        for i in range(WAVEFORM_SAMPLE_COUNT)
    ]
    rms = float(abs(math.sin(phase)) * 0.5)
    bass = float(max(0.0, math.sin(phase) * 0.6))
    mid = float(max(0.0, math.sin(phase + math.pi / 3) * 0.5))
    treble = float(max(0.0, math.sin(phase + 2 * math.pi / 3) * 0.4))
    return {
        "rms": rms,
        "beat": False,
        "bass": bass,
        "mid": mid,
        "treble": treble,
        "waveform": waveform,
    }


def _preview_feature_frames_batch(frame_count: int, fps: float) -> list[dict]:
    """Vectorized equivalent of calling _preview_feature_frame for each frame."""
    if frame_count == 0:
        return []
    safe_fps = max(float(fps), 1.0)
    t = np.arange(frame_count, dtype=np.float64) / safe_fps
    phase = (2.0 * math.pi * _PREVIEW_SINE_HZ) * t
    sample_indices = np.arange(WAVEFORM_SAMPLE_COUNT, dtype=np.float64)
    waveform_matrix = np.sin(
        phase[:, None] + (2.0 * math.pi / WAVEFORM_SAMPLE_COUNT) * sample_indices[None, :]
    )
    sin_phase = np.sin(phase)
    rms_values = np.abs(sin_phase) * 0.5
    bass_values = np.maximum(0.0, sin_phase * 0.6)
    mid_values = np.maximum(0.0, np.sin(phase + math.pi / 3.0) * 0.5)
    treble_values = np.maximum(0.0, np.sin(phase + 2.0 * math.pi / 3.0) * 0.4)
    waveform_lists = waveform_matrix.tolist()
    return [
        {
            "rms": float(rms_values[i]),
            "beat": False,
            "bass": float(bass_values[i]),
            "mid": float(mid_values[i]),
            "treble": float(treble_values[i]),
            "waveform": waveform_lists[i],
        }
        for i in range(frame_count)
    ]


def _resolve_sample_rate(audio_tensor, mono_audio: np.ndarray, duration: float) -> float:
    # Unwrap list/tuple wrappers to find the audio dict.
    candidate = audio_tensor
    if isinstance(candidate, (list, tuple)) and len(candidate) > 0:
        candidate = candidate[0]
    if isinstance(candidate, Mapping):
        for key in ("sample_rate", "sampling_rate", "samplerate"):
            value = candidate.get(key)
            if value is None:
                continue
            sample_rate = float(value)
            if np.isfinite(sample_rate) and sample_rate > 0.0:
                return sample_rate

    if duration > 0.0 and mono_audio.size > 0:
        inferred_rate = float(mono_audio.shape[0]) / float(duration)
        if np.isfinite(inferred_rate) and inferred_rate > 0.0:
            return inferred_rate

    return 44_100.0


def _coerce_audio_to_mono(audio_tensor) -> np.ndarray:
    # Unwrap ComfyUI AUDIO containers (dict, Mapping, or list-of-dict) to reach the raw tensor.
    _max_depth = 8
    while _max_depth > 0:
        _max_depth -= 1
        if audio_tensor is None:
            return np.array([], dtype=np.float32)
        if isinstance(audio_tensor, (list, tuple)):
            if len(audio_tensor) == 0:
                return np.array([], dtype=np.float32)
            audio_tensor = audio_tensor[0]
            continue
        if isinstance(audio_tensor, Mapping):
            if "waveform" in audio_tensor:
                audio_tensor = audio_tensor["waveform"]
            elif "samples" in audio_tensor:
                audio_tensor = audio_tensor["samples"]
            else:
                return np.array([], dtype=np.float32)
            continue
        break
    else:
        return np.array([], dtype=np.float32)

    if audio_tensor is None:
        return np.array([], dtype=np.float32)

    # Reject any string-like value at any stage (plain str, numpy.str_, bytes, etc.)
    if isinstance(audio_tensor, (str, bytes, np.str_, np.bytes_)):
        return np.array([], dtype=np.float32)

    if hasattr(audio_tensor, "detach"):
        audio_tensor = audio_tensor.detach()
    if hasattr(audio_tensor, "cpu"):
        audio_tensor = audio_tensor.cpu()
    if hasattr(audio_tensor, "numpy"):
        audio_tensor = audio_tensor.numpy()

    # Re-check after conversion — .numpy() could return unexpected types
    if isinstance(audio_tensor, (str, bytes, np.str_, np.bytes_)):
        return np.array([], dtype=np.float32)
    if isinstance(audio_tensor, np.ndarray) and audio_tensor.dtype.kind not in ("f", "i", "u", "c"):
        return np.array([], dtype=np.float32)

    try:
        audio_array = np.asarray(audio_tensor, dtype=np.float32)
    except (ValueError, TypeError):
        return np.array([], dtype=np.float32)
    if audio_array.size == 0:
        return np.array([], dtype=np.float32)

    audio_array = np.squeeze(audio_array)
    if audio_array.ndim == 0:
        return np.array([float(audio_array)], dtype=np.float32)

    if audio_array.ndim == 1:
        mono = audio_array
    else:
        channel_axis = int(np.argmin(audio_array.shape))
        mono = np.mean(audio_array, axis=channel_axis)
        mono = np.reshape(mono, (-1,))

    mono = np.nan_to_num(mono, nan=0.0, posinf=0.0, neginf=0.0)
    return np.clip(mono, -1.0, 1.0).astype(np.float32, copy=False)


def _compute_rms_per_frame(mono_audio: np.ndarray, frame_count: int) -> np.ndarray:
    if frame_count == 0 or mono_audio.size == 0:
        return np.zeros((frame_count,), dtype=np.float32)
    frame_edges = np.linspace(0, mono_audio.shape[0], frame_count + 1, dtype=np.int64)
    starts = frame_edges[:-1]
    sizes = (frame_edges[1:] - starts).astype(np.int64)
    # np.add.reduceat sums each contiguous slice [starts[i]:starts[i+1]] in a
    # single C loop without allocating a cumsum over the whole audio.
    squared = mono_audio * mono_audio  # float32
    sums = np.add.reduceat(squared, starts).astype(np.float32, copy=False)
    safe_sizes = np.maximum(sizes, 1).astype(np.float32)
    mean_energy = np.where(sizes > 0, sums / safe_sizes, np.float32(0.0))
    rms_values = np.sqrt(np.maximum(mean_energy, 0.0)).astype(np.float32, copy=False)
    return np.clip(rms_values, 0.0, 1.0)


def _detect_beats_energy_spike(rms_values: np.ndarray, fps: int) -> np.ndarray:
    frame_count = rms_values.shape[0]
    beat_flags = np.zeros((frame_count,), dtype=bool)
    if frame_count < 3:
        return beat_flags

    rolling_window = max(2, int(round(0.25 * fps)))
    threshold_multiplier = 1.6
    min_energy = 1e-4

    # Rolling mean over a trailing window [index-rolling_window, index) using
    # prefix sums — equivalent to the previous Python-loop mean but O(n) total.
    rms_f64 = rms_values.astype(np.float64, copy=False)
    prefix_sum = np.concatenate(([0.0], np.cumsum(rms_f64)))
    indices = np.arange(frame_count, dtype=np.int64)
    baseline_start = np.maximum(0, indices - rolling_window)
    baseline_count = indices - baseline_start
    baseline_sum = prefix_sum[indices] - prefix_sum[baseline_start]
    rolling_mean = np.where(baseline_count > 0, baseline_sum / np.maximum(baseline_count, 1), 0.0)

    inner = slice(1, frame_count - 1)
    current = rms_f64[inner]
    is_local_peak = (current > rms_f64[:-2]) & (current >= rms_f64[2:])
    is_spike = current > (rolling_mean[inner] * threshold_multiplier)
    is_loud_enough = current >= min_energy
    has_baseline = baseline_count[inner] > 0
    beat_flags[inner] = is_local_peak & is_spike & is_loud_enough & has_baseline
    return beat_flags


def _rms_magnitude_in_band(
    magnitudes: np.ndarray, frequencies: np.ndarray, low_hz: float, high_hz: float
) -> float:
    mask = (frequencies >= low_hz) & (frequencies < high_hz)
    if not np.any(mask):
        return 0.0
    band_magnitudes = magnitudes[mask]
    return float(np.sqrt(np.mean(band_magnitudes * band_magnitudes)))


def _compute_frequency_band_rms_per_frame(
    mono_audio: np.ndarray, frame_count: int, sample_rate: float
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    # Minimum RMS energy for a frame to be considered non-silent.
    # Below this threshold all frequency bands are forced to zero, preventing
    # FFT numerical noise from producing ghost bass/mid/treble values in silences.
    _SILENCE_THRESHOLD = 1e-3

    bass_values = np.zeros((frame_count,), dtype=np.float32)
    mid_values = np.zeros((frame_count,), dtype=np.float32)
    treble_values = np.zeros((frame_count,), dtype=np.float32)
    if frame_count == 0 or mono_audio.size == 0:
        return bass_values, mid_values, treble_values

    frame_edges = np.linspace(0, mono_audio.shape[0], frame_count + 1, dtype=np.int64)
    starts = frame_edges[:-1].astype(np.int64)
    ends = frame_edges[1:].astype(np.int64)
    sizes = (ends - starts).astype(np.int64)
    max_size = int(sizes.max()) if sizes.size else 0
    if max_size == 0:
        return bass_values, mid_values, treble_values

    # Zero-pad segments into a uniform matrix so np.fft.rfft can batch them.
    # Shorter segments get trailing zeros — this shifts the frequency resolution
    # by at most 1 bin, negligible for the coarse bass/mid/treble bands used here.
    segments = np.zeros((frame_count, max_size), dtype=np.float32)
    for index in range(frame_count):
        segment_size = int(sizes[index])
        if segment_size > 0:
            segments[index, :segment_size] = mono_audio[starts[index] : ends[index]]

    # Silence gate — identical threshold to the previous per-frame implementation.
    segment_rms = np.sqrt(np.mean(segments * segments, axis=1))
    active_mask = segment_rms >= _SILENCE_THRESHOLD
    if not np.any(active_mask):
        return bass_values, mid_values, treble_values

    magnitudes = np.abs(np.fft.rfft(segments[active_mask], axis=1))
    frequencies = np.fft.rfftfreq(max_size, d=1.0 / sample_rate)

    bass_mask = (frequencies >= 20.0) & (frequencies < 250.0)
    mid_mask = (frequencies >= 250.0) & (frequencies < 4000.0)
    treble_mask = (frequencies >= 4000.0) & (frequencies < 20000.01)

    def _band_rms(band_mask: np.ndarray) -> np.ndarray:
        if not np.any(band_mask):
            return np.zeros((int(active_mask.sum()),), dtype=np.float32)
        band = magnitudes[:, band_mask]
        return np.sqrt(np.mean(band * band, axis=1)).astype(np.float32, copy=False)

    bass_values[active_mask] = _band_rms(bass_mask)
    mid_values[active_mask] = _band_rms(mid_mask)
    treble_values[active_mask] = _band_rms(treble_mask)

    return bass_values, mid_values, treble_values


def _normalize_per_signal(values: np.ndarray) -> np.ndarray:
    max_value = float(np.max(values)) if values.size > 0 else 0.0
    if max_value <= 0.0:
        return np.zeros_like(values, dtype=np.float32)
    return np.clip(values / max_value, 0.0, 1.0).astype(np.float32, copy=False)


def _resample_waveform(segment: np.ndarray, sample_count: int) -> np.ndarray:
    if segment.size == 0:
        return np.zeros((sample_count,), dtype=np.float32)

    finite_segment = np.nan_to_num(segment, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32, copy=False)
    clipped = np.clip(finite_segment, -1.0, 1.0)

    if clipped.size == 1:
        return np.full((sample_count,), float(clipped[0]), dtype=np.float32)

    source_x = np.linspace(0.0, 1.0, clipped.size, dtype=np.float32)
    target_x = np.linspace(0.0, 1.0, sample_count, dtype=np.float32)
    resampled = np.interp(target_x, source_x, clipped)
    return resampled.astype(np.float32, copy=False)


def _compute_waveform_per_frame(mono_audio: np.ndarray, frame_count: int, sample_count: int) -> list[list[float]]:
    if frame_count == 0:
        return []
    if mono_audio.size == 0:
        zero_row = [0.0] * sample_count
        return [list(zero_row) for _ in range(frame_count)]

    finite_audio = np.nan_to_num(mono_audio, nan=0.0, posinf=0.0, neginf=0.0).astype(
        np.float32, copy=False
    )
    finite_audio = np.clip(finite_audio, -1.0, 1.0)

    frame_edges = np.linspace(0, finite_audio.shape[0], frame_count + 1, dtype=np.int64)
    starts = frame_edges[:-1].astype(np.int64)
    ends = frame_edges[1:].astype(np.int64)
    sizes = (ends - starts).astype(np.int64)

    # Vectorized linear interpolation across all frames at once. For each frame i
    # we want sample_count equispaced samples inside [start_i, end_i); build a
    # (frame_count, sample_count) matrix of fractional indices, then do a single
    # fancy lookup + weighted average.
    target_norm = np.linspace(0.0, 1.0, sample_count, dtype=np.float64)
    sample_positions = starts[:, None].astype(np.float64) + target_norm[None, :] * np.maximum(
        sizes[:, None].astype(np.float64) - 1.0, 0.0
    )
    floor_indices = np.floor(sample_positions).astype(np.int64)
    max_index = max(finite_audio.size - 1, 0)
    floor_indices = np.clip(floor_indices, 0, max_index)
    ceil_indices = np.clip(floor_indices + 1, 0, max_index)
    frac = (sample_positions - floor_indices).astype(np.float32)

    floor_samples = finite_audio[floor_indices]
    ceil_samples = finite_audio[ceil_indices]
    interpolated = floor_samples * (1.0 - frac) + ceil_samples * frac

    empty_mask = sizes == 0
    if np.any(empty_mask):
        interpolated[empty_mask] = 0.0

    single_sample_mask = sizes == 1
    if np.any(single_sample_mask):
        single_values = finite_audio[starts[single_sample_mask]].astype(np.float32, copy=False)
        interpolated[single_sample_mask] = single_values[:, None]

    return interpolated.tolist()


def extract_audio_features(audio_tensor, fps, duration) -> list[dict]:
    frame_count = round(float(duration) * float(fps))
    if frame_count < 0:
        raise ValueError("duration and fps must produce a non-negative frame count")
    if frame_count == 0:
        return []

    if audio_tensor is None or isinstance(audio_tensor, str):
        return _preview_feature_frames_batch(frame_count, float(fps))

    mono_audio = _coerce_audio_to_mono(audio_tensor)

    if mono_audio.size == 0:
        return _preview_feature_frames_batch(frame_count, float(fps))

    sample_rate = _resolve_sample_rate(audio_tensor, mono_audio, float(duration))
    rms_values = _compute_rms_per_frame(mono_audio, frame_count)
    beat_flags = _detect_beats_energy_spike(rms_values, int(fps))
    bass_raw, mid_raw, treble_raw = _compute_frequency_band_rms_per_frame(
        mono_audio, frame_count, sample_rate
    )
    bass_values = _normalize_per_signal(bass_raw)
    mid_values = _normalize_per_signal(mid_raw)
    treble_values = _normalize_per_signal(treble_raw)
    waveform_values = _compute_waveform_per_frame(mono_audio, frame_count, WAVEFORM_SAMPLE_COUNT)

    features: list[dict] = []
    for index in range(frame_count):
        features.append(
            {
                "rms": float(rms_values[index]),
                "beat": bool(beat_flags[index]),
                "bass": float(bass_values[index]),
                "mid": float(mid_values[index]),
                "treble": float(treble_values[index]),
                "waveform": waveform_values[index],
            }
        )
    return features
