from pathlib import Path
from dataclasses import dataclass
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


def _install_fake_torchaudio(
    call_order: list[str],
    *,
    track_specs: dict[str, dict] | None = None,
    resample_calls: list[tuple[int, int]] | None = None,
) -> None:
    fake_torchaudio = types.ModuleType("torchaudio")

    def _fake_load(path: str):
        file_name = Path(path).name
        call_order.append(file_name)
        if track_specs is None:
            track_index = len(call_order)
            waveform = torch.full((2, 8), float(track_index), dtype=torch.float32)
            return waveform, 44_100
        track_spec = track_specs[file_name]
        return track_spec["waveform"].clone(), int(track_spec["sample_rate"])

    def _fake_resample(waveform: torch.Tensor, orig_freq: int, new_freq: int):
        if resample_calls is not None:
            resample_calls.append((int(orig_freq), int(new_freq)))
        if int(orig_freq) == int(new_freq):
            return waveform
        source_samples = waveform.shape[1]
        target_samples = int(round(source_samples * (float(new_freq) / float(orig_freq))))
        sample_indices = torch.linspace(0, source_samples - 1, target_samples).round().long()
        return waveform[:, sample_indices]

    fake_torchaudio.load = _fake_load
    fake_torchaudio.functional = types.SimpleNamespace(resample=_fake_resample)
    sys.modules["torchaudio"] = fake_torchaudio


def _cleanup_fake_torchaudio() -> None:
    sys.modules.pop("torchaudio", None)


@dataclass
class _FakeVideo:
    images: torch.Tensor
    audio: object
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
        audio: object
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


def test_audio_mixer_node_has_transition_inputs():
    module = _load_module("cool_effects_audio_mixer_inputs_test", "nodes/audio_mixer.py")
    required_inputs = module.CoolAudioMixer.INPUT_TYPES()["required"]

    assert required_inputs["directory_path"] == ("STRING", {"default": ""})
    assert required_inputs["transition_type"] == (
        ["crossfade", "hard_cut", "fade_to_silence"],
        {"default": "crossfade"},
    )
    assert required_inputs["transition_duration"] == (
        "FLOAT",
        {"default": 1.0, "min": 0.1, "max": 10.0, "step": 0.1},
    )
    assert module.CoolAudioMixer.RETURN_TYPES == ("AUDIO",)
    assert module.CoolAudioMixer.RETURN_NAMES == ("audio",)


def test_audio_mixer_scans_case_insensitive_extensions_and_loads_sorted_files(tmp_path):
    (tmp_path / "B_song.MP3").write_bytes(b"track-b")
    (tmp_path / "a_song.wav").write_bytes(b"track-a")
    (tmp_path / "d_song.ogg").write_bytes(b"track-d")
    (tmp_path / "c_song.FlAc").write_bytes(b"track-c")
    (tmp_path / "notes.txt").write_text("not audio", encoding="utf-8")

    call_order: list[str] = []
    _install_fake_torchaudio(call_order)
    try:
        module = _load_module("cool_effects_audio_mixer_scan_test", "nodes/audio_mixer.py")
        node = module.CoolAudioMixer()
        (mixed_audio,) = node.execute(
            directory_path=str(tmp_path),
            transition_type="fade_to_silence",
            transition_duration=0.0001,
        )

        assert call_order == ["a_song.wav", "B_song.MP3", "c_song.FlAc", "d_song.ogg"]
        assert isinstance(mixed_audio["waveform"], torch.Tensor)
        assert mixed_audio["waveform"].shape[0] == 1
        assert mixed_audio["waveform"].shape[1] == 2
        assert mixed_audio["sample_rate"] == 44_100
    finally:
        _cleanup_fake_torchaudio()


def test_audio_mixer_raises_when_directory_has_fewer_than_two_audio_files(tmp_path):
    (tmp_path / "only_track.wav").write_bytes(b"track")

    module = _load_module("cool_effects_audio_mixer_minimum_files_test", "nodes/audio_mixer.py")
    node = module.CoolAudioMixer()

    try:
        node.execute(directory_path=str(tmp_path))
        raise AssertionError("Expected ValueError when directory has fewer than two audio files")
    except ValueError as error:
        message = str(error)

    assert "at least 2 audio files" in message
    assert str(tmp_path) in message


def test_audio_mixer_raises_when_directory_does_not_exist(tmp_path):
    missing_path = tmp_path / "missing-audio-dir"
    module = _load_module("cool_effects_audio_mixer_missing_dir_test", "nodes/audio_mixer.py")
    node = module.CoolAudioMixer()

    try:
        node.execute(directory_path=str(missing_path))
        raise AssertionError("Expected ValueError when directory path does not exist")
    except ValueError as error:
        message = str(error)

    assert "does not exist" in message
    assert str(missing_path) in message


def test_audio_mixer_ignores_transition_duration_for_hard_cut(tmp_path):
    (tmp_path / "a_song.wav").write_bytes(b"track-a")
    (tmp_path / "b_song.wav").write_bytes(b"track-b")

    call_order: list[str] = []
    track_specs = {
        "a_song.wav": {
            "waveform": torch.ones((2, 8), dtype=torch.float32),
            "sample_rate": 44_100,
        },
        "b_song.wav": {
            "waveform": torch.full((2, 8), 2.0, dtype=torch.float32),
            "sample_rate": 44_100,
        },
    }
    _install_fake_torchaudio(call_order, track_specs=track_specs)
    try:
        module = _load_module("cool_effects_audio_mixer_hard_cut_test", "nodes/audio_mixer.py")
        node = module.CoolAudioMixer()
        (short_duration_audio,) = node.execute(
            directory_path=str(tmp_path),
            transition_type="hard_cut",
            transition_duration=0.1,
        )
        (long_duration_audio,) = node.execute(
            directory_path=str(tmp_path),
            transition_type="hard_cut",
            transition_duration=9.5,
        )
    finally:
        _cleanup_fake_torchaudio()

    assert short_duration_audio["sample_rate"] == long_duration_audio["sample_rate"]
    assert torch.equal(short_duration_audio["waveform"], long_duration_audio["waveform"])


def test_audio_mixer_is_registered_in_package_mappings():
    package_module = _load_module("cool_effects_package_audio_mixer_registration_test", "__init__.py")

    assert package_module.NODE_CLASS_MAPPINGS["CoolAudioMixer"] is package_module.CoolAudioMixer
    assert package_module.NODE_DISPLAY_NAME_MAPPINGS["CoolAudioMixer"] == "Cool Audio Mixer"


def test_audio_mixer_crossfade_overlaps_and_applies_linear_fades(tmp_path):
    (tmp_path / "a_song.wav").write_bytes(b"track-a")
    (tmp_path / "b_song.wav").write_bytes(b"track-b")

    call_order: list[str] = []
    track_specs = {
        "a_song.wav": {
            "waveform": torch.ones((2, 6), dtype=torch.float32),
            "sample_rate": 10,
        },
        "b_song.wav": {
            "waveform": torch.full((2, 6), 3.0, dtype=torch.float32),
            "sample_rate": 10,
        },
    }
    _install_fake_torchaudio(call_order, track_specs=track_specs)
    try:
        module = _load_module("cool_effects_audio_mixer_crossfade_test", "nodes/audio_mixer.py")
        node = module.CoolAudioMixer()
        (mixed_audio,) = node.execute(
            directory_path=str(tmp_path),
            transition_type="crossfade",
            transition_duration=0.3,
        )
    finally:
        _cleanup_fake_torchaudio()

    mixed_waveform = mixed_audio["waveform"][0]
    expected = torch.tensor([1.0, 1.0, 1.0, 1.0, 2.0, 3.0, 3.0, 3.0, 3.0], dtype=torch.float32)
    assert mixed_waveform.shape == (2, 9)
    assert torch.allclose(mixed_waveform[0], expected)
    assert torch.allclose(mixed_waveform[1], expected)


def test_audio_mixer_hard_cut_concatenates_without_overlap_or_gap(tmp_path):
    (tmp_path / "a_song.wav").write_bytes(b"track-a")
    (tmp_path / "b_song.wav").write_bytes(b"track-b")

    call_order: list[str] = []
    track_specs = {
        "a_song.wav": {
            "waveform": torch.ones((2, 6), dtype=torch.float32),
            "sample_rate": 10,
        },
        "b_song.wav": {
            "waveform": torch.full((2, 6), 3.0, dtype=torch.float32),
            "sample_rate": 10,
        },
    }
    _install_fake_torchaudio(call_order, track_specs=track_specs)
    try:
        module = _load_module("cool_effects_audio_mixer_hard_cut_mix_test", "nodes/audio_mixer.py")
        node = module.CoolAudioMixer()
        (mixed_audio,) = node.execute(
            directory_path=str(tmp_path),
            transition_type="hard_cut",
            transition_duration=9.0,
        )
    finally:
        _cleanup_fake_torchaudio()

    mixed_waveform = mixed_audio["waveform"][0]
    expected = torch.tensor(
        [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0], dtype=torch.float32
    )
    assert mixed_waveform.shape == (2, 12)
    assert torch.allclose(mixed_waveform[0], expected)
    assert torch.allclose(mixed_waveform[1], expected)


def test_audio_mixer_fade_to_silence_adds_silence_gap_between_tracks(tmp_path):
    (tmp_path / "a_song.wav").write_bytes(b"track-a")
    (tmp_path / "b_song.wav").write_bytes(b"track-b")

    call_order: list[str] = []
    track_specs = {
        "a_song.wav": {
            "waveform": torch.ones((2, 6), dtype=torch.float32),
            "sample_rate": 10,
        },
        "b_song.wav": {
            "waveform": torch.full((2, 6), 3.0, dtype=torch.float32),
            "sample_rate": 10,
        },
    }
    _install_fake_torchaudio(call_order, track_specs=track_specs)
    try:
        module = _load_module("cool_effects_audio_mixer_fade_to_silence_test", "nodes/audio_mixer.py")
        node = module.CoolAudioMixer()
        (mixed_audio,) = node.execute(
            directory_path=str(tmp_path),
            transition_type="fade_to_silence",
            transition_duration=0.2,
        )
    finally:
        _cleanup_fake_torchaudio()

    mixed_waveform = mixed_audio["waveform"][0]
    expected = torch.tensor(
        [1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 3.0, 3.0, 3.0, 3.0, 3.0],
        dtype=torch.float32,
    )
    assert mixed_waveform.shape == (2, 14)
    assert torch.allclose(mixed_waveform[0], expected)
    assert torch.allclose(mixed_waveform[1], expected)


def test_audio_mixer_resamples_to_first_track_rate_and_normalizes_to_stereo(tmp_path):
    (tmp_path / "a_song.wav").write_bytes(b"track-a")
    (tmp_path / "b_song.wav").write_bytes(b"track-b")
    (tmp_path / "c_song.wav").write_bytes(b"track-c")

    call_order: list[str] = []
    resample_calls: list[tuple[int, int]] = []
    track_specs = {
        "a_song.wav": {
            "waveform": torch.tensor([[1.0, 2.0, 3.0, 4.0]], dtype=torch.float32),
            "sample_rate": 8,
        },
        "b_song.wav": {
            "waveform": torch.tensor(
                [[10.0, 20.0, 30.0, 40.0], [11.0, 21.0, 31.0, 41.0]], dtype=torch.float32
            ),
            "sample_rate": 16,
        },
        "c_song.wav": {
            "waveform": torch.tensor(
                [
                    [100.0, 200.0, 300.0, 400.0],
                    [101.0, 201.0, 301.0, 401.0],
                    [102.0, 202.0, 302.0, 402.0],
                ],
                dtype=torch.float32,
            ),
            "sample_rate": 8,
        },
    }
    _install_fake_torchaudio(call_order, track_specs=track_specs, resample_calls=resample_calls)
    try:
        module = _load_module("cool_effects_audio_mixer_resample_stereo_test", "nodes/audio_mixer.py")
        node = module.CoolAudioMixer()
        (mixed_audio,) = node.execute(
            directory_path=str(tmp_path),
            transition_type="hard_cut",
            transition_duration=1.0,
        )
    finally:
        _cleanup_fake_torchaudio()

    mixed_waveform = mixed_audio["waveform"][0]
    assert mixed_audio["sample_rate"] == 8
    assert mixed_waveform.shape == (2, 10)
    assert resample_calls == [(16, 8)]
    assert torch.equal(
        mixed_waveform,
        torch.tensor(
            [
                [1.0, 2.0, 3.0, 4.0, 10.0, 40.0, 100.0, 200.0, 300.0, 400.0],
                [1.0, 2.0, 3.0, 4.0, 11.0, 41.0, 101.0, 201.0, 301.0, 401.0],
            ],
            dtype=torch.float32,
        ),
    )


def test_audio_mixer_crossfade_raises_when_transition_longer_than_adjacent_track(tmp_path):
    (tmp_path / "a_song.wav").write_bytes(b"track-a")
    (tmp_path / "b_song.wav").write_bytes(b"track-b")

    call_order: list[str] = []
    track_specs = {
        "a_song.wav": {
            "waveform": torch.ones((2, 3), dtype=torch.float32),
            "sample_rate": 10,
        },
        "b_song.wav": {
            "waveform": torch.full((2, 2), 3.0, dtype=torch.float32),
            "sample_rate": 10,
        },
    }
    _install_fake_torchaudio(call_order, track_specs=track_specs)
    try:
        module = _load_module("cool_effects_audio_mixer_crossfade_duration_validation_test", "nodes/audio_mixer.py")
        node = module.CoolAudioMixer()
        try:
            node.execute(
                directory_path=str(tmp_path),
                transition_type="crossfade",
                transition_duration=0.3,
            )
            raise AssertionError("Expected ValueError for transition_duration longer than shortest track")
        except ValueError as error:
            message = str(error)
    finally:
        _cleanup_fake_torchaudio()

    assert "transition_duration is longer than the shortest adjacent track" in message


def test_audio_mixer_output_connects_to_video_generator_audio_input(tmp_path):
    (tmp_path / "a_song.wav").write_bytes(b"track-a")
    (tmp_path / "b_song.wav").write_bytes(b"track-b")

    call_order: list[str] = []
    _install_fake_torchaudio(call_order)
    _install_fake_comfy_api()
    try:
        mixer_module = _load_module("cool_effects_audio_mixer_to_video_generator_test", "nodes/audio_mixer.py")
        video_generator_module = _load_module(
            "cool_effects_video_generator_audio_contract_test",
            "nodes/video_generator.py",
        )
        video_generator_module.extract_audio_features = lambda audio, fps, duration: []
        video_generator_module._render_frames = (
            lambda image, effect_params, fps, duration, audio_features=None: image
        )

        mixer_node = mixer_module.CoolAudioMixer()
        (mixed_audio,) = mixer_node.execute(
            directory_path=str(tmp_path),
            transition_type="hard_cut",
            transition_duration=0.1,
        )

        generator_node = video_generator_module.CoolVideoGenerator()
        output = generator_node.execute(
            image=torch.zeros((1, 4, 4, 3), dtype=torch.float32),
            fps=24,
            duration=1.0,
            effect_count=1,
            audio=mixed_audio,
            effect_params_1={"effect_name": "glitch", "params": {}},
        )

        result_video = output["result"][0]
        assert isinstance(result_video, _FakeVideo)
        assert result_video.audio is mixed_audio
        assert mixed_audio["waveform"].ndim == 3
        assert mixed_audio["waveform"].shape[0] == 1
        assert mixed_audio["waveform"].shape[1] == 2
        assert isinstance(mixed_audio["sample_rate"], int)
    finally:
        _cleanup_fake_comfy_api()
        _cleanup_fake_torchaudio()
