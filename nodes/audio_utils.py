"""Audio feature extraction utilities for audio-reactive effect nodes."""

from __future__ import annotations

import numpy as np


def _default_feature_frame() -> dict[str, float | bool]:
    return {
        "rms": 0.0,
        "beat": False,
        "bass": 0.0,
        "mid": 0.0,
        "treble": 0.0,
    }


def _coerce_audio_to_mono(audio_tensor) -> np.ndarray:
    if isinstance(audio_tensor, dict):
        if "waveform" in audio_tensor:
            audio_tensor = audio_tensor["waveform"]
        elif "samples" in audio_tensor:
            audio_tensor = audio_tensor["samples"]

    if audio_tensor is None:
        return np.array([], dtype=np.float32)

    if hasattr(audio_tensor, "detach"):
        audio_tensor = audio_tensor.detach()
    if hasattr(audio_tensor, "cpu"):
        audio_tensor = audio_tensor.cpu()
    if hasattr(audio_tensor, "numpy"):
        audio_tensor = audio_tensor.numpy()

    audio_array = np.asarray(audio_tensor, dtype=np.float32)
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


def extract_audio_features(audio_tensor, fps, duration) -> list[dict]:
    frame_count = round(float(duration) * float(fps))
    if frame_count < 0:
        raise ValueError("duration and fps must produce a non-negative frame count")
    if frame_count == 0:
        return []

    if audio_tensor is None:
        return [_default_feature_frame() for _ in range(frame_count)]

    mono_audio = _coerce_audio_to_mono(audio_tensor)
    if mono_audio.size == 0:
        return [_default_feature_frame() for _ in range(frame_count)]

    rms_values = _compute_rms_per_frame(mono_audio, frame_count)
    beat_flags = _detect_beats_energy_spike(rms_values, int(fps))

    features: list[dict] = []
    for index in range(frame_count):
        features.append(
            {
                "rms": float(rms_values[index]),
                "beat": bool(beat_flags[index]),
                "bass": 0.0,
                "mid": 0.0,
                "treble": 0.0,
            }
        )
    return features
