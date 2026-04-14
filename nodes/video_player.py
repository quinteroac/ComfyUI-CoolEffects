"""ComfyUI Video Player node."""

from __future__ import annotations

import logging
import os
import tempfile
import uuid
from pathlib import Path
from urllib.parse import quote


LOGGER = logging.getLogger(__name__)


def _read_video_value(entry, key: str, default=""):
    if isinstance(entry, dict):
        return entry.get(key, default)
    return getattr(entry, key, default)


def _build_view_url(video_entry: dict) -> str:
    filename = str(_read_video_value(video_entry, "filename", "")).strip()
    if not filename:
        return ""

    file_type = str(_read_video_value(video_entry, "type", "input")).strip() or "input"
    subfolder = str(_read_video_value(video_entry, "subfolder", "")).strip()

    query_parts = [
        f"filename={quote(filename)}",
        f"type={quote(file_type)}",
    ]
    if subfolder:
        query_parts.append(f"subfolder={quote(subfolder)}")
    return f"/view?{'&'.join(query_parts)}"


def _normalize_video_entries(video) -> list[dict]:
    if video is None:
        return []

    entries = video if isinstance(video, list) else [video]
    normalized_entries = []
    for entry in entries:
        if isinstance(entry, str):
            normalized_entries.append(
                {
                    "source_url": entry.strip(),
                    "filename": "",
                    "type": "",
                    "subfolder": "",
                    "format": "",
                }
            )
            continue

        source_url = str(
            _read_video_value(entry, "source_url", _read_video_value(entry, "url", ""))
        ).strip()
        if not source_url:
            source_url = _build_view_url(entry)

        filename = str(_read_video_value(entry, "filename", "")).strip()
        file_type = str(_read_video_value(entry, "type", "")).strip()
        subfolder = str(_read_video_value(entry, "subfolder", "")).strip()
        file_format = str(_read_video_value(entry, "format", "")).strip()

        if source_url or filename:
            normalized_entries.append(
                {
                    "source_url": source_url,
                    "filename": filename,
                    "type": file_type,
                    "subfolder": subfolder,
                    "format": file_format,
                }
            )

    return normalized_entries


def _save_video_preview_to_temp(video) -> list[dict]:
    if not hasattr(video, "save_to"):
        return []

    try:
        width, height = video.get_dimensions()
    except Exception:  # pragma: no cover - best effort for runtime compatibility
        width, height = 0, 0

    try:
        import folder_paths  # type: ignore

        full_output_folder, filename, counter, subfolder, _ = folder_paths.get_save_image_path(
            "cool-effects-preview",
            folder_paths.get_temp_directory(),
            width,
            height,
        )
        file = f"{filename}_{counter:05}_.mp4"
        output_path = os.path.join(full_output_folder, file)
    except ImportError:
        temp_dir = Path(tempfile.gettempdir()) / "comfyui-cool-effects"
        temp_dir.mkdir(parents=True, exist_ok=True)
        subfolder = ""
        file = f"cool-effects-preview-{uuid.uuid4().hex}.mp4"
        output_path = str(temp_dir / file)

    video.save_to(output_path)
    return [
        {
            "source_url": _build_view_url(
                {
                    "filename": file,
                    "subfolder": subfolder,
                    "type": "temp",
                }
            ),
            "filename": file,
            "type": "temp",
            "subfolder": subfolder,
            "format": "video/mp4",
        }
    ]


class CoolVideoPlayer:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "video": ("VIDEO",),
            }
        }

    RETURN_TYPES = ()
    FUNCTION = "execute"
    OUTPUT_NODE = True
    CATEGORY = "CoolEffects"

    def execute(self, video):
        normalized_entries = _normalize_video_entries(video)
        if not normalized_entries:
            try:
                normalized_entries = _save_video_preview_to_temp(video)
            except Exception as error:
                LOGGER.warning(
                    "[CoolVideoPlayer] failed to materialize VIDEO preview: %s",
                    error,
                )
        LOGGER.warning(
            "[CoolVideoPlayer] execute received VIDEO payload type=%s normalized_entries=%s raw_video=%s",
            type(video).__name__,
            normalized_entries,
            video,
        )
        return {
            "video": normalized_entries,
            "ui": {
                "video": normalized_entries,
                "video_entries": normalized_entries,
            },
            "result": (),
        }
