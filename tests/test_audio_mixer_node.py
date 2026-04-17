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


def _install_fake_torchaudio(call_order: list[str]) -> None:
    fake_torchaudio = types.ModuleType("torchaudio")

    def _fake_load(path: str):
        file_name = Path(path).name
        call_order.append(file_name)
        track_index = len(call_order)
        waveform = torch.full((2, 8), float(track_index), dtype=torch.float32)
        return waveform, 44_100

    fake_torchaudio.load = _fake_load
    sys.modules["torchaudio"] = fake_torchaudio


def _cleanup_fake_torchaudio() -> None:
    sys.modules.pop("torchaudio", None)


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
        (loaded_tracks,) = node.execute(
            directory_path=str(tmp_path),
            transition_type="fade_to_silence",
            transition_duration=2.5,
        )

        assert call_order == ["a_song.wav", "B_song.MP3", "c_song.FlAc", "d_song.ogg"]
        assert [track["filename"] for track in loaded_tracks] == call_order
        assert [track["sample_rate"] for track in loaded_tracks] == [44_100, 44_100, 44_100, 44_100]
        assert all(isinstance(track["waveform"], torch.Tensor) for track in loaded_tracks)
        assert all(track["transition_type"] == "fade_to_silence" for track in loaded_tracks)
        assert all(track["transition_duration_seconds"] == 2.5 for track in loaded_tracks)
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
    _install_fake_torchaudio(call_order)
    try:
        module = _load_module("cool_effects_audio_mixer_hard_cut_test", "nodes/audio_mixer.py")
        node = module.CoolAudioMixer()
        (short_duration_tracks,) = node.execute(
            directory_path=str(tmp_path),
            transition_type="hard_cut",
            transition_duration=0.1,
        )
        (long_duration_tracks,) = node.execute(
            directory_path=str(tmp_path),
            transition_type="hard_cut",
            transition_duration=9.5,
        )
    finally:
        _cleanup_fake_torchaudio()

    assert [track["filename"] for track in short_duration_tracks] == [track["filename"] for track in long_duration_tracks]
    assert all(track["transition_type"] == "hard_cut" for track in short_duration_tracks)
    assert all(track["transition_type"] == "hard_cut" for track in long_duration_tracks)
    assert all(track["transition_duration_seconds"] == 0.0 for track in short_duration_tracks)
    assert all(track["transition_duration_seconds"] == 0.0 for track in long_duration_tracks)


def test_audio_mixer_is_registered_in_package_mappings():
    package_module = _load_module("cool_effects_package_audio_mixer_registration_test", "__init__.py")

    assert package_module.NODE_CLASS_MAPPINGS["CoolAudioMixer"] is package_module.CoolAudioMixer
    assert package_module.NODE_DISPLAY_NAME_MAPPINGS["CoolAudioMixer"] == "Cool Audio Mixer"
