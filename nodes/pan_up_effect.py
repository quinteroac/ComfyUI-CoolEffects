"""ComfyUI dedicated Pan Up effect node."""

import importlib.util
from pathlib import Path


_EFFECT_PARAMS_PATH = Path(__file__).resolve().parent / "effect_params.py"
_EFFECT_PARAMS_SPEC = importlib.util.spec_from_file_location(
    "cool_effects_effect_params_for_pan_up_effect", _EFFECT_PARAMS_PATH
)
if _EFFECT_PARAMS_SPEC is None or _EFFECT_PARAMS_SPEC.loader is None:
    raise ValueError(f"Missing effect params config at {_EFFECT_PARAMS_PATH}")
_effect_params_module = importlib.util.module_from_spec(_EFFECT_PARAMS_SPEC)
_EFFECT_PARAMS_SPEC.loader.exec_module(_effect_params_module)
build_effect_params = _effect_params_module.build_effect_params


class CoolPanUpEffect:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "speed": (
                    "FLOAT",
                    {"default": 0.2, "min": 0.0, "max": 5.0, "step": 0.05},
                ),
                "origin_x": (
                    "FLOAT",
                    {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01},
                ),
                "origin_y": (
                    "FLOAT",
                    {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01},
                ),
                "zoom": (
                    "FLOAT",
                    {"default": 0.0, "min": -0.9, "max": 5.0, "step": 0.05},
                ),
            }
        }

    RETURN_TYPES = ("EFFECT_PARAMS",)
    RETURN_NAMES = ("EFFECT_PARAMS",)
    FUNCTION = "execute"
    CATEGORY = "CoolEffects"

    def execute(self, speed, origin_x, origin_y, zoom):
        return (
            build_effect_params(
                "pan_up",
                {"u_speed": speed, "u_origin_x": origin_x, "u_origin_y": origin_y, "u_zoom": zoom},
            ),
        )
