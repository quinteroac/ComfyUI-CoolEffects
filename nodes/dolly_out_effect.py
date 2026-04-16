"""ComfyUI dedicated Dolly Out effect node."""

import importlib.util
from pathlib import Path


_EFFECT_PARAMS_PATH = Path(__file__).resolve().parent / "effect_params.py"
_EFFECT_PARAMS_SPEC = importlib.util.spec_from_file_location(
    "cool_effects_effect_params_for_dolly_out_effect", _EFFECT_PARAMS_PATH
)
if _EFFECT_PARAMS_SPEC is None or _EFFECT_PARAMS_SPEC.loader is None:
    raise ValueError(f"Missing effect params config at {_EFFECT_PARAMS_PATH}")
_effect_params_module = importlib.util.module_from_spec(_EFFECT_PARAMS_SPEC)
_EFFECT_PARAMS_SPEC.loader.exec_module(_effect_params_module)
build_effect_params = _effect_params_module.build_effect_params


class CoolDollyOutEffect:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "dolly_strength": (
                    "FLOAT",
                    {"default": 0.35, "min": 0.0, "max": 2.0, "step": 0.01},
                ),
                "dolly_speed": (
                    "FLOAT",
                    {"default": 0.7, "min": 0.0, "max": 5.0, "step": 0.05},
                ),
                "focus_x": (
                    "FLOAT",
                    {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01},
                ),
                "focus_y": (
                    "FLOAT",
                    {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01},
                ),
            }
        }

    RETURN_TYPES = ("EFFECT_PARAMS",)
    RETURN_NAMES = ("EFFECT_PARAMS",)
    FUNCTION = "execute"
    CATEGORY = "CoolEffects"

    def execute(self, dolly_strength, dolly_speed, focus_x, focus_y):
        return (
            build_effect_params(
                "dolly_out",
                {
                    "u_dolly_strength": dolly_strength,
                    "u_dolly_speed": dolly_speed,
                    "u_focus_x": focus_x,
                    "u_focus_y": focus_y,
                },
            ),
        )
