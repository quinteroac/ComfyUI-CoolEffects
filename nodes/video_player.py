"""ComfyUI Video Player node."""

from __future__ import annotations

from urllib.parse import quote


def _build_view_url(video_entry: dict) -> str:
    filename = str(video_entry.get("filename", "")).strip()
    if not filename:
        return ""

    file_type = str(video_entry.get("type", "input")).strip() or "input"
    subfolder = str(video_entry.get("subfolder", "")).strip()

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
        if isinstance(entry, dict):
            source_url = str(entry.get("source_url", "")).strip()
            if not source_url:
                source_url = _build_view_url(entry)
            normalized_entries.append(
                {
                    "source_url": source_url,
                    "filename": str(entry.get("filename", "")).strip(),
                    "type": str(entry.get("type", "")).strip(),
                    "subfolder": str(entry.get("subfolder", "")).strip(),
                    "format": str(entry.get("format", "")).strip(),
                }
            )
            continue

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

    return normalized_entries


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
        return {"ui": {"video_entries": _normalize_video_entries(video)}, "result": ()}
