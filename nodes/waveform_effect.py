"""ComfyUI dedicated Waveform effect node."""

import importlib.util
from pathlib import Path


_EFFECT_PARAMS_PATH = Path(__file__).resolve().parent / "effect_params.py"
_EFFECT_PARAMS_SPEC = importlib.util.spec_from_file_location(
    "cool_effects_effect_params_for_waveform_effect", _EFFECT_PARAMS_PATH
)
if _EFFECT_PARAMS_SPEC is None or _EFFECT_PARAMS_SPEC.loader is None:
    raise ValueError(f"Missing effect params config at {_EFFECT_PARAMS_PATH}")
_effect_params_module = importlib.util.module_from_spec(_EFFECT_PARAMS_SPEC)
_EFFECT_PARAMS_SPEC.loader.exec_module(_effect_params_module)
build_effect_params = _effect_params_module.build_effect_params


def _parse_line_color(line_color: str) -> tuple[float, float, float]:
    if not isinstance(line_color, str):
        raise ValueError("line_color must be a comma-separated RGB string")
    parts = [part.strip() for part in line_color.split(",")]
    if len(parts) != 3:
        raise ValueError("line_color must have exactly three comma-separated values")
    try:
        r, g, b = (float(parts[0]), float(parts[1]), float(parts[2]))
    except ValueError as error:
        raise ValueError("line_color values must be numeric") from error
    return (r, g, b)


class CoolWaveformEffect:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "line_color": ("STRING", {"default": "1.0,0.8,0.2"}),
                "line_thickness": (
                    "FLOAT",
                    {"default": 0.005, "min": 0.001, "max": 0.05, "step": 0.001},
                ),
                "waveform_height": (
                    "FLOAT",
                    {"default": 0.2, "min": 0.05, "max": 0.8, "step": 0.01},
                ),
                "waveform_y": (
                    "FLOAT",
                    {"default": 0.8, "min": 0.0, "max": 1.0, "step": 0.01},
                ),
                "opacity": (
                    "FLOAT",
                    {"default": 0.85, "min": 0.0, "max": 1.0, "step": 0.01},
                ),
            }
        }

    RETURN_TYPES = ("EFFECT_PARAMS",)
    RETURN_NAMES = ("EFFECT_PARAMS",)
    FUNCTION = "execute"
    CATEGORY = "CoolEffects"

    def execute(self, line_color, line_thickness, waveform_height, waveform_y, opacity):
        return (
            build_effect_params(
                "waveform",
                {
                    "u_line_color": _parse_line_color(line_color),
                    "u_line_thickness": line_thickness,
                    "u_waveform_height": waveform_height,
                    "u_waveform_y": waveform_y,
                    "u_opacity": opacity,
                },
            ),
        )
