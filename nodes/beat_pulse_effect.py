"""ComfyUI dedicated Beat Pulse effect node."""

import importlib.util
from pathlib import Path


_EFFECT_PARAMS_PATH = Path(__file__).resolve().parent / "effect_params.py"
_EFFECT_PARAMS_SPEC = importlib.util.spec_from_file_location(
    "cool_effects_effect_params_for_beat_pulse_effect", _EFFECT_PARAMS_PATH
)
if _EFFECT_PARAMS_SPEC is None or _EFFECT_PARAMS_SPEC.loader is None:
    raise ValueError(f"Missing effect params config at {_EFFECT_PARAMS_PATH}")
_effect_params_module = importlib.util.module_from_spec(_EFFECT_PARAMS_SPEC)
_EFFECT_PARAMS_SPEC.loader.exec_module(_effect_params_module)
build_effect_params = _effect_params_module.build_effect_params


class CoolBeatPulseEffect:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "pulse_intensity": (
                    "FLOAT",
                    {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01},
                ),
                "zoom_amount": (
                    "FLOAT",
                    {"default": 0.05, "min": 0.0, "max": 0.3, "step": 0.005},
                ),
                "decay": (
                    "FLOAT",
                    {"default": 0.3, "min": 0.0, "max": 1.0, "step": 0.01},
                ),
            }
        }

    RETURN_TYPES = ("EFFECT_PARAMS",)
    RETURN_NAMES = ("EFFECT_PARAMS",)
    FUNCTION = "execute"
    CATEGORY = "CoolEffects"

    def execute(self, pulse_intensity, zoom_amount, decay):
        return (
            build_effect_params(
                "beat_pulse",
                {
                    "u_pulse_intensity": pulse_intensity,
                    "u_zoom_amount": zoom_amount,
                    "u_decay": decay,
                },
            ),
        )
