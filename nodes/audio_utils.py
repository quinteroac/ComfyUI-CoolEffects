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
    frame_edges = np.linspace(0, mono_audio.shape[0], frame_count + 1, dtype=np.int64)
    rms_values = np.zeros((frame_count,), dtype=np.float32)
    for index in range(frame_count):
        start = int(frame_edges[index])
        end = int(frame_edges[index + 1])
        if end <= start:
            continue
        segment = mono_audio[start:end]
        if segment.size == 0:
            continue
        energy = float(np.mean(segment * segment))
        rms_values[index] = float(np.sqrt(energy))
    return np.clip(rms_values, 0.0, 1.0)


def _detect_beats_energy_spike(rms_values: np.ndarray, fps: int) -> np.ndarray:
    frame_count = rms_values.shape[0]
    beat_flags = np.zeros((frame_count,), dtype=bool)
    if frame_count < 3:
        return beat_flags

    rolling_window = max(2, int(round(0.25 * fps)))
    threshold_multiplier = 1.6
    min_energy = 1e-4

    for index in range(1, frame_count - 1):
        baseline_start = max(0, index - rolling_window)
        baseline = rms_values[baseline_start:index]
        if baseline.size == 0:
            continue
        rolling_mean = float(np.mean(baseline))
        current_energy = float(rms_values[index])
        if current_energy < min_energy:
            continue
        is_local_peak = current_energy > float(rms_values[index - 1]) and current_energy >= float(
            rms_values[index + 1]
        )
        is_spike = current_energy > (rolling_mean * threshold_multiplier)
        if is_local_peak and is_spike:
            beat_flags[index] = True

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

    frame_edges = np.linspace(0, mono_audio.shape[0], frame_count + 1, dtype=np.int64)
    bass_values = np.zeros((frame_count,), dtype=np.float32)
    mid_values = np.zeros((frame_count,), dtype=np.float32)
    treble_values = np.zeros((frame_count,), dtype=np.float32)

    for index in range(frame_count):
        start = int(frame_edges[index])
        end = int(frame_edges[index + 1])
        if end <= start:
            continue
        segment = mono_audio[start:end]
        if segment.size == 0:
            continue

        # Skip FFT entirely for silent frames.
        segment_rms = float(np.sqrt(np.mean(segment * segment)))
        if segment_rms < _SILENCE_THRESHOLD:
            continue

        magnitudes = np.abs(np.fft.rfft(segment))
        frequencies = np.fft.rfftfreq(segment.size, d=1.0 / sample_rate)

        bass_values[index] = _rms_magnitude_in_band(magnitudes, frequencies, 20.0, 250.0)
        mid_values[index] = _rms_magnitude_in_band(magnitudes, frequencies, 250.0, 4000.0)
        treble_values[index] = _rms_magnitude_in_band(magnitudes, frequencies, 4000.0, 20000.01)

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
    frame_edges = np.linspace(0, mono_audio.shape[0], frame_count + 1, dtype=np.int64)
    waveforms: list[list[float]] = []
    for index in range(frame_count):
        start = int(frame_edges[index])
        end = int(frame_edges[index + 1])
        if end <= start:
            waveforms.append([0.0] * sample_count)
            continue
        segment = mono_audio[start:end]
        resampled = _resample_waveform(segment, sample_count)
        waveforms.append(resampled.tolist())
    return waveforms


def extract_audio_features(audio_tensor, fps, duration) -> list[dict]:
    frame_count = round(float(duration) * float(fps))
    if frame_count < 0:
        raise ValueError("duration and fps must produce a non-negative frame count")
    if frame_count == 0:
        return []

    if audio_tensor is None or isinstance(audio_tensor, str):
        return [_preview_feature_frame(i, float(fps)) for i in range(frame_count)]

    mono_audio = _coerce_audio_to_mono(audio_tensor)

    if mono_audio.size == 0:
        return [_preview_feature_frame(i, float(fps)) for i in range(frame_count)]

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
