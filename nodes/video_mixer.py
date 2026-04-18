"""ComfyUI video mixer node."""

from pathlib import Path


_SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv"}
_TRANSITION_TYPE_OPTIONS = ["crossfade", "hard_cut", "fade_to_black"]


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

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("video_files",)
    FUNCTION = "execute"
    CATEGORY = "CoolEffects/video"

    def execute(self, directory_path, transition_type="crossfade", transition_duration=1.0):
        video_paths = _resolve_video_file_paths(directory_path)
        _resolve_effective_transition_duration(transition_type, transition_duration)
        return ("\n".join(str(video_path) for video_path in video_paths),)
