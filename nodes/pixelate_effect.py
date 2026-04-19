"""ComfyUI dedicated Pixelate effect node."""

import importlib.util
from pathlib import Path


_EFFECT_PARAMS_PATH = Path(__file__).resolve().parent / "effect_params.py"
_EFFECT_PARAMS_SPEC = importlib.util.spec_from_file_location(
    "cool_effects_effect_params_for_pixelate_effect", _EFFECT_PARAMS_PATH
)
if _EFFECT_PARAMS_SPEC is None or _EFFECT_PARAMS_SPEC.loader is None:
    raise ValueError(f"Missing effect params config at {_EFFECT_PARAMS_PATH}")
_effect_params_module = importlib.util.module_from_spec(_EFFECT_PARAMS_SPEC)
_EFFECT_PARAMS_SPEC.loader.exec_module(_effect_params_module)
build_effect_params = _effect_params_module.build_effect_params


class CoolPixelateEffect:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "pixel_size": (
                    "INT",
                    {"default": 8, "min": 1, "max": 128, "step": 1},
                ),
                "aspect_ratio": (
                    "FLOAT",
                    {"default": 1.0, "min": 0.25, "max": 4.0, "step": 0.01},
                ),
            }
        }

    RETURN_TYPES = ("EFFECT_PARAMS",)
    RETURN_NAMES = ("EFFECT_PARAMS",)
    FUNCTION = "execute"
    CATEGORY = "CoolEffects"

    def execute(self, pixel_size, aspect_ratio):
        return (
            build_effect_params(
                "pixelate",
                {
                    "u_pixel_size": pixel_size,
                    "u_aspect_ratio": aspect_ratio,
                },
            ),
        )
