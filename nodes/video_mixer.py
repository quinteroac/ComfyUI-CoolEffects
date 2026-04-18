"""ComfyUI video mixer node."""

from pathlib import Path


_SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv"}


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


class CoolVideoMixer:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "directory_path": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("video_files",)
    FUNCTION = "execute"
    CATEGORY = "CoolEffects/video"

    def execute(self, directory_path):
        video_paths = _resolve_video_file_paths(directory_path)
        return ("\n".join(str(video_path) for video_path in video_paths),)
