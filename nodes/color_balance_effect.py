"""ComfyUI dedicated Color Balance effect node."""

import importlib.util
from pathlib import Path


_EFFECT_PARAMS_PATH = Path(__file__).resolve().parent / "effect_params.py"
_EFFECT_PARAMS_SPEC = importlib.util.spec_from_file_location(
    "cool_effects_effect_params_for_color_balance_effect", _EFFECT_PARAMS_PATH
)
if _EFFECT_PARAMS_SPEC is None or _EFFECT_PARAMS_SPEC.loader is None:
    raise ValueError(f"Missing effect params config at {_EFFECT_PARAMS_PATH}")
_effect_params_module = importlib.util.module_from_spec(_EFFECT_PARAMS_SPEC)
_EFFECT_PARAMS_SPEC.loader.exec_module(_effect_params_module)
build_effect_params = _effect_params_module.build_effect_params


class CoolColorBalanceEffect:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "shadows_r": (
                    "FLOAT",
                    {"default": 0.0, "min": -1.0, "max": 1.0, "step": 0.01},
                ),
                "shadows_g": (
                    "FLOAT",
                    {"default": 0.0, "min": -1.0, "max": 1.0, "step": 0.01},
                ),
                "shadows_b": (
                    "FLOAT",
                    {"default": 0.0, "min": -1.0, "max": 1.0, "step": 0.01},
                ),
                "midtones_r": (
                    "FLOAT",
                    {"default": 0.0, "min": -1.0, "max": 1.0, "step": 0.01},
                ),
                "midtones_g": (
                    "FLOAT",
                    {"default": 0.0, "min": -1.0, "max": 1.0, "step": 0.01},
                ),
                "midtones_b": (
                    "FLOAT",
                    {"default": 0.0, "min": -1.0, "max": 1.0, "step": 0.01},
                ),
                "highlights_r": (
                    "FLOAT",
                    {"default": 0.0, "min": -1.0, "max": 1.0, "step": 0.01},
                ),
                "highlights_g": (
                    "FLOAT",
                    {"default": 0.0, "min": -1.0, "max": 1.0, "step": 0.01},
                ),
                "highlights_b": (
                    "FLOAT",
                    {"default": 0.0, "min": -1.0, "max": 1.0, "step": 0.01},
                ),
            }
        }

    RETURN_TYPES = ("EFFECT_PARAMS",)
    RETURN_NAMES = ("EFFECT_PARAMS",)
    FUNCTION = "execute"
    CATEGORY = "CoolEffects"

    def execute(
        self,
        shadows_r,
        shadows_g,
        shadows_b,
        midtones_r,
        midtones_g,
        midtones_b,
        highlights_r,
        highlights_g,
        highlights_b,
    ):
        return (
            build_effect_params(
                "color_balance",
                {
                    "u_shadows_r": shadows_r,
                    "u_shadows_g": shadows_g,
                    "u_shadows_b": shadows_b,
                    "u_midtones_r": midtones_r,
                    "u_midtones_g": midtones_g,
                    "u_midtones_b": midtones_b,
                    "u_highlights_r": highlights_r,
                    "u_highlights_g": highlights_g,
                    "u_highlights_b": highlights_b,
                },
            ),
        )
