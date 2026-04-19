"""ComfyUI dedicated Color Quantization effect node."""

import importlib.util
from pathlib import Path


_EFFECT_PARAMS_PATH = Path(__file__).resolve().parent / "effect_params.py"
_EFFECT_PARAMS_SPEC = importlib.util.spec_from_file_location(
    "cool_effects_effect_params_for_color_quantization_effect", _EFFECT_PARAMS_PATH
)
if _EFFECT_PARAMS_SPEC is None or _EFFECT_PARAMS_SPEC.loader is None:
    raise ValueError(f"Missing effect params config at {_EFFECT_PARAMS_PATH}")
_effect_params_module = importlib.util.module_from_spec(_EFFECT_PARAMS_SPEC)
_EFFECT_PARAMS_SPEC.loader.exec_module(_effect_params_module)
build_effect_params = _effect_params_module.build_effect_params


class CoolColorQuantizationEffect:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "levels_r": (
                    "INT",
                    {"default": 4, "min": 2, "max": 32, "step": 1},
                ),
                "levels_g": (
                    "INT",
                    {"default": 4, "min": 2, "max": 32, "step": 1},
                ),
                "levels_b": (
                    "INT",
                    {"default": 4, "min": 2, "max": 32, "step": 1},
                ),
            }
        }

    RETURN_TYPES = ("EFFECT_PARAMS",)
    RETURN_NAMES = ("EFFECT_PARAMS",)
    FUNCTION = "execute"
    CATEGORY = "CoolEffects"

    def execute(self, levels_r, levels_g, levels_b):
        return (
            build_effect_params(
                "color_quantization",
                {
                    "u_levels_r": levels_r,
                    "u_levels_g": levels_g,
                    "u_levels_b": levels_b,
                },
            ),
        )
