"""ComfyUI dedicated Dithering effect node."""

import importlib.util
from pathlib import Path


_EFFECT_PARAMS_PATH = Path(__file__).resolve().parent / "effect_params.py"
_EFFECT_PARAMS_SPEC = importlib.util.spec_from_file_location(
    "cool_effects_effect_params_for_dithering_effect", _EFFECT_PARAMS_PATH
)
if _EFFECT_PARAMS_SPEC is None or _EFFECT_PARAMS_SPEC.loader is None:
    raise ValueError(f"Missing effect params config at {_EFFECT_PARAMS_PATH}")
_effect_params_module = importlib.util.module_from_spec(_EFFECT_PARAMS_SPEC)
_EFFECT_PARAMS_SPEC.loader.exec_module(_effect_params_module)
build_effect_params = _effect_params_module.build_effect_params


class CoolDitheringEffect:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "dither_scale": (
                    "FLOAT",
                    {"default": 1.0, "min": 0.5, "max": 8.0, "step": 0.01},
                ),
                "threshold": (
                    "FLOAT",
                    {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01},
                ),
                "palette_size": (
                    "INT",
                    {"default": 2, "min": 2, "max": 16, "step": 1},
                ),
            }
        }

    RETURN_TYPES = ("EFFECT_PARAMS",)
    RETURN_NAMES = ("EFFECT_PARAMS",)
    FUNCTION = "execute"
    CATEGORY = "CoolEffects"

    def execute(self, dither_scale, threshold, palette_size):
        return (
            build_effect_params(
                "dithering",
                {
                    "u_dither_scale": dither_scale,
                    "u_threshold": threshold,
                    "u_palette_size": palette_size,
                },
            ),
        )
