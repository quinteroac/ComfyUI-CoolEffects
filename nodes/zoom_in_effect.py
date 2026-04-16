"""ComfyUI dedicated Zoom In effect node."""

import importlib.util
from pathlib import Path


_EFFECT_PARAMS_PATH = Path(__file__).resolve().parent / "effect_params.py"
_EFFECT_PARAMS_SPEC = importlib.util.spec_from_file_location(
    "cool_effects_effect_params_for_zoom_in_effect", _EFFECT_PARAMS_PATH
)
if _EFFECT_PARAMS_SPEC is None or _EFFECT_PARAMS_SPEC.loader is None:
    raise ValueError(f"Missing effect params config at {_EFFECT_PARAMS_PATH}")
_effect_params_module = importlib.util.module_from_spec(_EFFECT_PARAMS_SPEC)
_EFFECT_PARAMS_SPEC.loader.exec_module(_effect_params_module)
build_effect_params = _effect_params_module.build_effect_params


class CoolZoomInEffect:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "zoom_strength": (
                    "FLOAT",
                    {"default": 0.25, "min": 0.0, "max": 2.0, "step": 0.01},
                ),
                "zoom_speed": (
                    "FLOAT",
                    {"default": 0.6, "min": 0.0, "max": 5.0, "step": 0.05},
                ),
            }
        }

    RETURN_TYPES = ("EFFECT_PARAMS",)
    RETURN_NAMES = ("EFFECT_PARAMS",)
    FUNCTION = "execute"
    CATEGORY = "CoolEffects"

    def execute(self, zoom_strength, zoom_speed):
        return (
            build_effect_params(
                "zoom_in",
                {
                    "u_zoom_strength": zoom_strength,
                    "u_zoom_speed": zoom_speed,
                },
            ),
        )
