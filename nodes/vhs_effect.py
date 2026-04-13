"""ComfyUI dedicated VHS effect node."""

import importlib.util
from pathlib import Path


_EFFECT_PARAMS_PATH = Path(__file__).resolve().parent / "effect_params.py"
_EFFECT_PARAMS_SPEC = importlib.util.spec_from_file_location(
    "cool_effects_effect_params_for_vhs_effect", _EFFECT_PARAMS_PATH
)
if _EFFECT_PARAMS_SPEC is None or _EFFECT_PARAMS_SPEC.loader is None:
    raise ValueError(f"Missing effect params config at {_EFFECT_PARAMS_PATH}")
_effect_params_module = importlib.util.module_from_spec(_EFFECT_PARAMS_SPEC)
_EFFECT_PARAMS_SPEC.loader.exec_module(_effect_params_module)
build_effect_params = _effect_params_module.build_effect_params


class CoolVHSEffect:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "scanline_intensity": (
                    "FLOAT",
                    {"default": 0.04, "min": 0.0, "max": 0.5, "step": 0.005},
                ),
                "jitter_amount": (
                    "FLOAT",
                    {"default": 0.0018, "min": 0.0, "max": 0.02, "step": 0.0002},
                ),
                "chroma_shift": (
                    "FLOAT",
                    {"default": 0.002, "min": 0.0, "max": 0.02, "step": 0.0002},
                ),
            }
        }

    RETURN_TYPES = ("EFFECT_PARAMS",)
    RETURN_NAMES = ("EFFECT_PARAMS",)
    FUNCTION = "execute"
    CATEGORY = "CoolEffects"

    def execute(self, scanline_intensity, jitter_amount, chroma_shift):
        return (
            build_effect_params(
                "vhs",
                {
                    "u_scanline_intensity": scanline_intensity,
                    "u_jitter_amount": jitter_amount,
                    "u_chroma_shift": chroma_shift,
                },
            ),
        )
