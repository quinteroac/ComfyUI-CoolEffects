"""ComfyUI dedicated Water Drops effect node."""

import importlib.util
from pathlib import Path


_EFFECT_PARAMS_PATH = Path(__file__).resolve().parent / "effect_params.py"
_EFFECT_PARAMS_SPEC = importlib.util.spec_from_file_location(
    "cool_effects_effect_params_for_water_drops_effect", _EFFECT_PARAMS_PATH
)
if _EFFECT_PARAMS_SPEC is None or _EFFECT_PARAMS_SPEC.loader is None:
    raise ValueError(f"Missing effect params config at {_EFFECT_PARAMS_PATH}")
_effect_params_module = importlib.util.module_from_spec(_EFFECT_PARAMS_SPEC)
_EFFECT_PARAMS_SPEC.loader.exec_module(_effect_params_module)
build_effect_params = _effect_params_module.build_effect_params


class CoolWaterDropsEffect:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "drop_density": (
                    "INT",
                    {"default": 60, "min": 1, "max": 200, "step": 1},
                ),
                "drop_size": (
                    "FLOAT",
                    {"default": 0.08, "min": 0.01, "max": 0.5, "step": 0.01},
                ),
                "fall_speed": (
                    "FLOAT",
                    {"default": 1.0, "min": 0.1, "max": 5.0, "step": 0.1},
                ),
                "refraction_strength": (
                    "FLOAT",
                    {"default": 0.3, "min": 0.0, "max": 1.0, "step": 0.01},
                ),
                "gravity": (
                    "FLOAT",
                    {"default": 1.0, "min": 0.1, "max": 5.0, "step": 0.1},
                ),
                "wind": (
                    "FLOAT",
                    {"default": 0.0, "min": -2.0, "max": 2.0, "step": 0.1},
                ),
                "blur": (
                    "FLOAT",
                    {"default": 1.0, "min": 0.0, "max": 2.0, "step": 0.1},
                ),
            }
        }

    RETURN_TYPES = ("EFFECT_PARAMS",)
    RETURN_NAMES = ("EFFECT_PARAMS",)
    FUNCTION = "execute"
    CATEGORY = "CoolEffects"

    def execute(
        self,
        drop_density,
        drop_size,
        fall_speed,
        refraction_strength,
        gravity,
        wind,
        blur,
    ):
        return (
            build_effect_params(
                "water_drops",
                {
                    "u_drop_density": drop_density,
                    "u_drop_size": drop_size,
                    "u_fall_speed": fall_speed,
                    "u_refraction_strength": refraction_strength,
                    "u_gravity": gravity,
                    "u_wind": wind,
                    "u_blur": blur,
                },
            ),
        )
