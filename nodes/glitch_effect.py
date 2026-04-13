"""ComfyUI dedicated Glitch effect node."""

import importlib.util
from pathlib import Path


_EFFECT_PARAMS_PATH = Path(__file__).resolve().parent / "effect_params.py"
_EFFECT_PARAMS_SPEC = importlib.util.spec_from_file_location(
    "cool_effects_effect_params_for_glitch_effect", _EFFECT_PARAMS_PATH
)
if _EFFECT_PARAMS_SPEC is None or _EFFECT_PARAMS_SPEC.loader is None:
    raise ValueError(f"Missing effect params config at {_EFFECT_PARAMS_PATH}")
_effect_params_module = importlib.util.module_from_spec(_EFFECT_PARAMS_SPEC)
_EFFECT_PARAMS_SPEC.loader.exec_module(_effect_params_module)
build_effect_params = _effect_params_module.build_effect_params


class CoolGlitchEffect:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "wave_freq": (
                    "FLOAT",
                    {"default": 120.0, "min": 1.0, "max": 500.0, "step": 1.0},
                ),
                "wave_amp": (
                    "FLOAT",
                    {"default": 0.0025, "min": 0.0, "max": 0.05, "step": 0.0005},
                ),
                "speed": (
                    "FLOAT",
                    {"default": 10.0, "min": 0.0, "max": 100.0, "step": 0.5},
                ),
            }
        }

    RETURN_TYPES = ("EFFECT_PARAMS",)
    RETURN_NAMES = ("EFFECT_PARAMS",)
    FUNCTION = "execute"
    CATEGORY = "CoolEffects"

    def execute(self, wave_freq, wave_amp, speed):
        return (
            build_effect_params(
                "glitch",
                {
                    "u_wave_freq": wave_freq,
                    "u_wave_amp": wave_amp,
                    "u_speed": speed,
                },
            ),
        )
