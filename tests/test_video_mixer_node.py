from pathlib import Path
import importlib.util


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_module(module_name: str, relative_path: str):
    module_path = REPO_ROOT / relative_path
    module_spec = importlib.util.spec_from_file_location(module_name, module_path)
    if module_spec is None or module_spec.loader is None:
        raise ValueError(f"Missing module config at {module_path}")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def test_video_mixer_node_has_directory_input():
    module = _load_module("cool_effects_video_mixer_inputs_test", "nodes/video_mixer.py")
    required_inputs = module.CoolVideoMixer.INPUT_TYPES()["required"]

    assert required_inputs["directory_path"] == ("STRING", {"default": ""})


def test_video_mixer_scans_case_insensitive_extensions_and_loads_sorted_files(tmp_path):
    (tmp_path / "B_clip.MOV").write_bytes(b"video-b")
    (tmp_path / "a_clip.mp4").write_bytes(b"video-a")
    (tmp_path / "d_clip.MkV").write_bytes(b"video-d")
    (tmp_path / "c_clip.WebM").write_bytes(b"video-c")
    (tmp_path / "notes.txt").write_text("not video", encoding="utf-8")

    module = _load_module("cool_effects_video_mixer_scan_test", "nodes/video_mixer.py")
    node = module.CoolVideoMixer()
    (video_files,) = node.execute(directory_path=str(tmp_path))

    assert video_files.splitlines() == [
        str(tmp_path / "a_clip.mp4"),
        str(tmp_path / "B_clip.MOV"),
        str(tmp_path / "c_clip.WebM"),
        str(tmp_path / "d_clip.MkV"),
    ]


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
