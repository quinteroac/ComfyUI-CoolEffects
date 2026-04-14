"""ComfyUI dedicated Frosted Glass effect node."""

import importlib.util
from pathlib import Path


_EFFECT_PARAMS_PATH = Path(__file__).resolve().parent / "effect_params.py"
_EFFECT_PARAMS_SPEC = importlib.util.spec_from_file_location(
    "cool_effects_effect_params_for_frosted_glass_effect", _EFFECT_PARAMS_PATH
)
if _EFFECT_PARAMS_SPEC is None or _EFFECT_PARAMS_SPEC.loader is None:
    raise ValueError(f"Missing effect params config at {_EFFECT_PARAMS_PATH}")
_effect_params_module = importlib.util.module_from_spec(_EFFECT_PARAMS_SPEC)
_EFFECT_PARAMS_SPEC.loader.exec_module(_effect_params_module)
build_effect_params = _effect_params_module.build_effect_params


class CoolFrostedGlassEffect:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "frost_intensity": (
                    "FLOAT",
                    {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01},
                ),
                "blur_radius": (
                    "FLOAT",
                    {"default": 0.015, "min": 0.0, "max": 0.05, "step": 0.001},
                ),
                "uniformity": (
                    "FLOAT",
                    {"default": 0.6, "min": 0.0, "max": 1.0, "step": 0.01},
                ),
                "tint_temperature": (
                    "FLOAT",
                    {"default": 0.0, "min": -1.0, "max": 1.0, "step": 0.01},
                ),
                "condensation_rate": (
                    "FLOAT",
                    {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01},
                ),
            }
        }

    RETURN_TYPES = ("EFFECT_PARAMS",)
    RETURN_NAMES = ("EFFECT_PARAMS",)
    FUNCTION = "execute"
    CATEGORY = "CoolEffects"

    def execute(
        self,
        frost_intensity,
        blur_radius,
        uniformity,
        tint_temperature,
        condensation_rate,
    ):
        return (
            build_effect_params(
                "frosted_glass",
                {
                    "u_frost_intensity": frost_intensity,
                    "u_blur_radius": blur_radius,
                    "u_uniformity": uniformity,
                    "u_tint_temperature": tint_temperature,
                    "u_condensation_rate": condensation_rate,
                },
            ),
        )
