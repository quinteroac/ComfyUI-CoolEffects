from dataclasses import dataclass
from pathlib import Path
import importlib.util
import sys
import types

import torch


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_module(module_name: str, relative_path: str):
    module_path = REPO_ROOT / relative_path
    module_spec = importlib.util.spec_from_file_location(module_name, module_path)
    if module_spec is None or module_spec.loader is None:
        raise ValueError(f"Missing module config at {module_path}")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


@dataclass
class _FakeVideo:
    images: torch.Tensor
    audio: dict
    frame_rate: object


def _install_fake_comfy_api() -> None:
    comfy_api_module = types.ModuleType("comfy_api")
    latest_module = types.ModuleType("comfy_api.latest")

    class _FakeInputImpl:
        @staticmethod
        def VideoFromComponents(video_components):
            return _FakeVideo(
                images=video_components.images,
                audio=video_components.audio,
                frame_rate=video_components.frame_rate,
            )

    @dataclass
    class _FakeVideoComponents:
        images: torch.Tensor
        audio: dict
        frame_rate: object

    class _FakeTypes:
        VideoComponents = _FakeVideoComponents

    latest_module.InputImpl = _FakeInputImpl
    latest_module.Types = _FakeTypes
    comfy_api_module.latest = latest_module
    sys.modules["comfy_api"] = comfy_api_module
    sys.modules["comfy_api.latest"] = latest_module


def _cleanup_fake_comfy_api() -> None:
    sys.modules.pop("comfy_api.latest", None)
    sys.modules.pop("comfy_api", None)


def _build_clip(
    *,
    filename: str,
    frames: list[float],
    fps: float = 10.0,
    width: int = 1,
    height: int = 1,
    audio_values: list[float] | None = None,
    audio_sample_rate: int | None = 10,
):
    frame_tensor = torch.tensor(frames, dtype=torch.float32).view(-1, 1, 1, 1)
    if width > 1 or height > 1:
        frame_tensor = frame_tensor.repeat(1, height, width, 3)
    else:
        frame_tensor = frame_tensor.repeat(1, 1, 1, 3)

    audio_waveform = None
    if audio_values is not None:
        audio_waveform = torch.tensor(audio_values, dtype=torch.float32).view(1, -1).repeat(2, 1)

    return {
        "path": filename,
        "filename": filename,
        "frames": frame_tensor,
        "frame_count": int(frame_tensor.shape[0]),
        "width": width,
        "height": height,
        "fps": fps,
        "duration_seconds": float(frame_tensor.shape[0]) / float(fps),
        "audio_waveform": audio_waveform,
        "audio_sample_rate": audio_sample_rate if audio_waveform is not None else None,
    }


def test_video_mixer_node_has_transition_inputs():
    module = _load_module("cool_effects_video_mixer_inputs_test", "nodes/video_mixer.py")
    required_inputs = module.CoolVideoMixer.INPUT_TYPES()["required"]

    assert required_inputs["directory_path"] == ("STRING", {"default": ""})
    assert required_inputs["transition_type"] == (
        ["crossfade", "hard_cut", "fade_to_black"],
        {"default": "crossfade"},
    )
    assert required_inputs["transition_duration"] == (
        "FLOAT",
        {"default": 1.0, "min": 0.1, "max": 10.0, "step": 0.1},
    )
    assert module.CoolVideoMixer.RETURN_TYPES == ("VIDEO",)
    assert module.CoolVideoMixer.RETURN_NAMES == ("video",)


def test_video_mixer_scans_case_insensitive_extensions_and_loads_sorted_files(tmp_path):
    (tmp_path / "B_clip.MOV").write_bytes(b"video-b")
    (tmp_path / "a_clip.mp4").write_bytes(b"video-a")
    (tmp_path / "d_clip.MkV").write_bytes(b"video-d")
    (tmp_path / "c_clip.WebM").write_bytes(b"video-c")
    (tmp_path / "notes.txt").write_text("not video", encoding="utf-8")

    module = _load_module("cool_effects_video_mixer_scan_test", "nodes/video_mixer.py")
    video_paths = module._resolve_video_file_paths(str(tmp_path))

    assert [str(path) for path in video_paths] == [
        str(tmp_path / "a_clip.mp4"),
        str(tmp_path / "B_clip.MOV"),
        str(tmp_path / "c_clip.WebM"),
        str(tmp_path / "d_clip.MkV"),
    ]


def test_video_mixer_ignores_transition_duration_for_hard_cut():
    module = _load_module("cool_effects_video_mixer_hard_cut_duration_test", "nodes/video_mixer.py")

    short_duration = module._resolve_effective_transition_duration("hard_cut", 0.1)
    long_duration = module._resolve_effective_transition_duration("hard_cut", 9.9)

    assert short_duration == 0.0
    assert long_duration == 0.0


def test_video_mixer_raises_when_directory_path_is_empty():
    module = _load_module("cool_effects_video_mixer_empty_dir_test", "nodes/video_mixer.py")
    node = module.CoolVideoMixer()

    try:
        node.execute(directory_path=" ")
        raise AssertionError("Expected ValueError when directory path is empty")
    except ValueError as error:
        message = str(error)

    assert "non-empty string" in message


def test_video_mixer_raises_when_directory_does_not_exist(tmp_path):
    missing_path = tmp_path / "missing-video-dir"
    module = _load_module("cool_effects_video_mixer_missing_dir_test", "nodes/video_mixer.py")
    node = module.CoolVideoMixer()

    try:
        node.execute(directory_path=str(missing_path))
        raise AssertionError("Expected ValueError when directory path does not exist")
    except ValueError as error:
        message = str(error)

    assert "does not exist" in message
    assert str(missing_path) in message


def test_video_mixer_raises_when_directory_path_is_not_a_directory(tmp_path):
    file_path = tmp_path / "not_a_directory.mp4"
    file_path.write_bytes(b"video")
    module = _load_module("cool_effects_video_mixer_not_directory_test", "nodes/video_mixer.py")
    node = module.CoolVideoMixer()

    try:
        node.execute(directory_path=str(file_path))
        raise AssertionError("Expected ValueError when directory path is not a directory")
    except ValueError as error:
        message = str(error)

    assert "not a directory" in message
    assert str(file_path) in message


def test_video_mixer_raises_when_directory_has_fewer_than_two_video_files(tmp_path):
    (tmp_path / "only_clip.mp4").write_bytes(b"video")

    module = _load_module("cool_effects_video_mixer_minimum_files_test", "nodes/video_mixer.py")
    node = module.CoolVideoMixer()

    try:
        node.execute(directory_path=str(tmp_path))
        raise AssertionError("Expected ValueError when directory has fewer than two video files")
    except ValueError as error:
        message = str(error)

    assert "at least 2 video files" in message
    assert str(tmp_path) in message


def test_video_mixer_raises_for_mismatched_resolution_with_offending_filename():
    module = _load_module("cool_effects_video_mixer_homogeneous_resolution_test", "nodes/video_mixer.py")
    clips = [
        _build_clip(filename="a.mp4", frames=[1.0, 1.0], width=4, height=3),
        _build_clip(filename="b.mp4", frames=[2.0, 2.0], width=5, height=3),
    ]

    try:
        module._validate_homogeneous(clips)
        raise AssertionError("Expected ValueError for mismatched resolution")
    except ValueError as error:
        message = str(error)

    assert "b.mp4" in message
    assert "resolution mismatch" in message.lower()


def test_video_mixer_raises_for_mismatched_fps_with_offending_filename():
    module = _load_module("cool_effects_video_mixer_homogeneous_fps_test", "nodes/video_mixer.py")
    clips = [
        _build_clip(filename="a.mp4", frames=[1.0, 1.0], fps=10.0),
        _build_clip(filename="b.mp4", frames=[2.0, 2.0], fps=12.0),
    ]

    try:
        module._validate_homogeneous(clips)
        raise AssertionError("Expected ValueError for mismatched fps")
    except ValueError as error:
        message = str(error)

    assert "b.mp4" in message
    assert "fps mismatch" in message.lower()


def test_video_mixer_crossfade_overlaps_and_applies_linear_blend():
    module = _load_module("cool_effects_video_mixer_crossfade_test", "nodes/video_mixer.py")
    clips = [
        _build_clip(filename="a.mp4", frames=[1.0] * 6),
        _build_clip(filename="b.mp4", frames=[3.0] * 6),
    ]

    mixed_frames = module._mix_video_tracks(clips, "crossfade", 0.3, 10.0)
    expected = torch.tensor([1.0, 1.0, 1.0, 1.0, 2.0, 3.0, 3.0, 3.0, 3.0], dtype=torch.float32)
    assert mixed_frames.shape == (9, 1, 1, 3)
    assert torch.allclose(mixed_frames[:, 0, 0, 0], expected)


def test_video_mixer_hard_cut_concatenates_without_blend():
    module = _load_module("cool_effects_video_mixer_hard_cut_mix_test", "nodes/video_mixer.py")
    clips = [
        _build_clip(filename="a.mp4", frames=[1.0] * 6),
        _build_clip(filename="b.mp4", frames=[3.0] * 6),
    ]

    mixed_frames = module._mix_video_tracks(clips, "hard_cut", 0.0, 10.0)
    expected = torch.tensor(
        [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0], dtype=torch.float32
    )
    assert mixed_frames.shape == (12, 1, 1, 3)
    assert torch.allclose(mixed_frames[:, 0, 0, 0], expected)


def test_video_mixer_fade_to_black_fades_out_in_with_black_gap():
    module = _load_module("cool_effects_video_mixer_fade_to_black_test", "nodes/video_mixer.py")
    clips = [
        _build_clip(filename="a.mp4", frames=[1.0] * 6),
        _build_clip(filename="b.mp4", frames=[3.0] * 6),
    ]

    mixed_frames = module._mix_video_tracks(clips, "fade_to_black", 0.2, 10.0)
    expected = torch.tensor(
        [1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 3.0, 3.0, 3.0, 3.0, 3.0],
        dtype=torch.float32,
    )
    assert mixed_frames.shape == (14, 1, 1, 3)
    assert torch.allclose(mixed_frames[:, 0, 0, 0], expected)


def test_video_mixer_audio_transition_analog_crossfade(monkeypatch):
    module = _load_module("cool_effects_video_mixer_audio_crossfade_test", "nodes/video_mixer.py")
    _install_fake_comfy_api()
    try:
        clips = [
            _build_clip(filename="a.mp4", frames=[1.0] * 6, audio_values=[1.0] * 6),
            _build_clip(filename="b.mp4", frames=[3.0] * 6, audio_values=[3.0] * 6),
        ]
        monkeypatch.setattr(module, "_resolve_video_file_paths", lambda _directory_path: [Path("a.mp4"), Path("b.mp4")])
        monkeypatch.setattr(module, "_load_video_files", lambda _video_paths: clips)

        node = module.CoolVideoMixer()
        (video,) = node.execute("unused", transition_type="crossfade", transition_duration=0.3)
    finally:
        _cleanup_fake_comfy_api()

    expected_audio = torch.tensor([1.0, 1.0, 1.0, 1.0, 2.0, 3.0, 3.0, 3.0, 3.0], dtype=torch.float32)
    assert isinstance(video, _FakeVideo)
    assert torch.allclose(video.audio["waveform"][0, 0], expected_audio)


def test_video_mixer_audio_transition_analog_hard_cut(monkeypatch):
    module = _load_module("cool_effects_video_mixer_audio_hard_cut_test", "nodes/video_mixer.py")
    _install_fake_comfy_api()
    try:
        clips = [
            _build_clip(filename="a.mp4", frames=[1.0] * 6, audio_values=[1.0] * 6),
            _build_clip(filename="b.mp4", frames=[3.0] * 6, audio_values=[3.0] * 6),
        ]
        monkeypatch.setattr(module, "_resolve_video_file_paths", lambda _directory_path: [Path("a.mp4"), Path("b.mp4")])
        monkeypatch.setattr(module, "_load_video_files", lambda _video_paths: clips)

        node = module.CoolVideoMixer()
        (video,) = node.execute("unused", transition_type="hard_cut", transition_duration=3.0)
    finally:
        _cleanup_fake_comfy_api()

    expected_audio = torch.tensor(
        [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0], dtype=torch.float32
    )
    assert isinstance(video, _FakeVideo)
    assert torch.allclose(video.audio["waveform"][0, 0], expected_audio)


def test_video_mixer_audio_transition_analog_fade_to_black_uses_fade_to_silence(monkeypatch):
    module = _load_module("cool_effects_video_mixer_audio_fade_to_black_test", "nodes/video_mixer.py")
    _install_fake_comfy_api()
    try:
        clips = [
            _build_clip(filename="a.mp4", frames=[1.0] * 6, audio_values=[1.0] * 6),
            _build_clip(filename="b.mp4", frames=[3.0] * 6, audio_values=[3.0] * 6),
        ]
        monkeypatch.setattr(module, "_resolve_video_file_paths", lambda _directory_path: [Path("a.mp4"), Path("b.mp4")])
        monkeypatch.setattr(module, "_load_video_files", lambda _video_paths: clips)

        node = module.CoolVideoMixer()
        (video,) = node.execute("unused", transition_type="fade_to_black", transition_duration=0.2)
    finally:
        _cleanup_fake_comfy_api()

    expected_audio = torch.tensor(
        [1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 3.0, 3.0, 3.0, 3.0, 3.0],
        dtype=torch.float32,
    )
    assert isinstance(video, _FakeVideo)
    assert torch.allclose(video.audio["waveform"][0, 0], expected_audio)


def test_video_mixer_synthesizes_silence_for_missing_audio_track():
    module = _load_module("cool_effects_video_mixer_missing_audio_test", "nodes/video_mixer.py")
    clips = [
        _build_clip(filename="a.mp4", frames=[1.0] * 6, audio_values=[1.0] * 6, audio_sample_rate=10),
        _build_clip(filename="b.mp4", frames=[3.0] * 6, audio_values=None),
    ]

    prepared_tracks, sample_rate = module._prepare_audio_tracks_for_mixing(clips, 10.0)
    mixed_audio = module._mix_audio_tracks(prepared_tracks, "hard_cut", 0.0, sample_rate)

    expected_audio = torch.tensor(
        [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], dtype=torch.float32
    )
    assert sample_rate == 10
    assert mixed_audio.shape == (2, 12)
    assert torch.allclose(mixed_audio[0], expected_audio)
    assert torch.allclose(mixed_audio[1], expected_audio)


def test_video_mixer_raises_when_transition_duration_longer_than_shortest_adjacent_clip():
    module = _load_module("cool_effects_video_mixer_duration_validation_test", "nodes/video_mixer.py")
    clips = [
        _build_clip(filename="a.mp4", frames=[1.0, 1.0, 1.0], fps=10.0),
        _build_clip(filename="b.mp4", frames=[2.0, 2.0], fps=10.0),
    ]

    try:
        module._validate_transition_duration_against_adjacent_clips(clips, "crossfade", 0.3)
        raise AssertionError("Expected ValueError for transition_duration longer than shortest clip")
    except ValueError as error:
        message = str(error)

    assert "transition_duration is longer than the shortest adjacent clip" in message


def test_video_mixer_hard_cut_skips_shortest_adjacent_clip_duration_validation():
    module = _load_module("cool_effects_video_mixer_hard_cut_duration_validation_test", "nodes/video_mixer.py")
    clips = [
        _build_clip(filename="a.mp4", frames=[1.0, 1.0], fps=10.0),
        _build_clip(filename="b.mp4", frames=[2.0], fps=10.0),
    ]

    module._validate_transition_duration_against_adjacent_clips(clips, "hard_cut", 999.0)
