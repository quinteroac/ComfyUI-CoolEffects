"""ComfyUI dedicated Freq Warp effect node."""

import importlib.util
from pathlib import Path


_EFFECT_PARAMS_PATH = Path(__file__).resolve().parent / "effect_params.py"
_EFFECT_PARAMS_SPEC = importlib.util.spec_from_file_location(
    "cool_effects_effect_params_for_freq_warp_effect", _EFFECT_PARAMS_PATH
)
if _EFFECT_PARAMS_SPEC is None or _EFFECT_PARAMS_SPEC.loader is None:
    raise ValueError(f"Missing effect params config at {_EFFECT_PARAMS_PATH}")
_effect_params_module = importlib.util.module_from_spec(_EFFECT_PARAMS_SPEC)
_EFFECT_PARAMS_SPEC.loader.exec_module(_effect_params_module)
build_effect_params = _effect_params_module.build_effect_params


class CoolFreqWarpEffect:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "warp_intensity": (
                    "FLOAT",
                    {"default": 0.4, "min": 0.0, "max": 1.0, "step": 0.01},
                ),
                "warp_frequency": (
                    "FLOAT",
                    {"default": 8.0, "min": 1.0, "max": 32.0, "step": 0.5},
                ),
                "mid_weight": (
                    "FLOAT",
                    {"default": 0.6, "min": 0.0, "max": 1.0, "step": 0.01},
                ),
                "treble_weight": (
                    "FLOAT",
                    {"default": 0.4, "min": 0.0, "max": 1.0, "step": 0.01},
                ),
            }
        }

    RETURN_TYPES = ("EFFECT_PARAMS",)
    RETURN_NAMES = ("EFFECT_PARAMS",)
    FUNCTION = "execute"
    CATEGORY = "CoolEffects"

    def execute(self, warp_intensity, warp_frequency, mid_weight, treble_weight):
        return (
            build_effect_params(
                "freq_warp",
                {
                    "u_warp_intensity": warp_intensity,
                    "u_warp_frequency": warp_frequency,
                    "u_mid_weight": mid_weight,
                    "u_treble_weight": treble_weight,
                },
            ),
        )
