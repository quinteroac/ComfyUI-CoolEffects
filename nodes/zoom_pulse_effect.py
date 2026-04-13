"""ComfyUI dedicated Zoom Pulse effect node."""

import importlib.util
from pathlib import Path


_EFFECT_PARAMS_PATH = Path(__file__).resolve().parent / "effect_params.py"
_EFFECT_PARAMS_SPEC = importlib.util.spec_from_file_location(
    "cool_effects_effect_params_for_zoom_pulse_effect", _EFFECT_PARAMS_PATH
)
if _EFFECT_PARAMS_SPEC is None or _EFFECT_PARAMS_SPEC.loader is None:
    raise ValueError(f"Missing effect params config at {_EFFECT_PARAMS_PATH}")
_effect_params_module = importlib.util.module_from_spec(_EFFECT_PARAMS_SPEC)
_EFFECT_PARAMS_SPEC.loader.exec_module(_effect_params_module)
build_effect_params = _effect_params_module.build_effect_params


class CoolZoomPulseEffect:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "pulse_amp": (
                    "FLOAT",
                    {"default": 0.06, "min": 0.0, "max": 0.5, "step": 0.005},
                ),
                "pulse_speed": (
                    "FLOAT",
                    {"default": 3.0, "min": 0.1, "max": 20.0, "step": 0.1},
                ),
            }
        }

    RETURN_TYPES = ("EFFECT_PARAMS",)
    RETURN_NAMES = ("EFFECT_PARAMS",)
    FUNCTION = "execute"
    CATEGORY = "CoolEffects"

    def execute(self, pulse_amp, pulse_speed):
        return (
            build_effect_params(
                "zoom_pulse",
                {
                    "u_pulse_amp": pulse_amp,
                    "u_pulse_speed": pulse_speed,
                },
            ),
        )
