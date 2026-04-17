"""ComfyUI audio mixer node."""

from pathlib import Path


_SUPPORTED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg"}


def _resolve_audio_file_paths(directory_path: str) -> list[Path]:
    normalized_path = str(directory_path).strip()
    if not normalized_path:
        raise ValueError("directory_path must be a non-empty string")

    directory = Path(normalized_path).expanduser()
    if not directory.exists():
        raise ValueError(f"Audio directory does not exist: {directory}")
    if not directory.is_dir():
        raise ValueError(f"Audio directory path is not a directory: {directory}")

    audio_paths = sorted(
        [
            file_path
            for file_path in directory.iterdir()
            if file_path.is_file() and file_path.suffix.lower() in _SUPPORTED_AUDIO_EXTENSIONS
        ],
        key=lambda file_path: file_path.name.lower(),
    )
    if len(audio_paths) < 2:
        raise ValueError(
            f"Audio directory must contain at least 2 audio files (.wav, .mp3, .flac, .ogg): {directory}"
        )

    return audio_paths


def _load_audio_files(audio_paths: list[Path]) -> list[dict]:
    try:
        import torchaudio
    except ImportError as error:
        raise ValueError("torchaudio is required to load audio files for CoolAudioMixer.") from error

    loaded_tracks: list[dict] = []
    for audio_path in audio_paths:
        waveform, sample_rate = torchaudio.load(str(audio_path))
        loaded_tracks.append(
            {
                "path": str(audio_path),
                "filename": audio_path.name,
                "waveform": waveform,
                "sample_rate": int(sample_rate),
            }
        )
    return loaded_tracks


class CoolAudioMixer:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "directory_path": ("STRING", {"default": ""}),
            }
        }

    RETURN_TYPES = ("AUDIO_TRACKS",)
    RETURN_NAMES = ("audio_tracks",)
    FUNCTION = "execute"
    CATEGORY = "CoolEffects/audio"

    def execute(self, directory_path):
        audio_paths = _resolve_audio_file_paths(directory_path)
        loaded_tracks = _load_audio_files(audio_paths)
        return (loaded_tracks,)
