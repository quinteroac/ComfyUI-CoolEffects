"""ComfyUI dedicated Chromatic Aberration effect node."""

import importlib.util
from pathlib import Path


_EFFECT_PARAMS_PATH = Path(__file__).resolve().parent / "effect_params.py"
_EFFECT_PARAMS_SPEC = importlib.util.spec_from_file_location(
    "cool_effects_effect_params_for_chromatic_aberration_effect", _EFFECT_PARAMS_PATH
)
if _EFFECT_PARAMS_SPEC is None or _EFFECT_PARAMS_SPEC.loader is None:
    raise ValueError(f"Missing effect params config at {_EFFECT_PARAMS_PATH}")
_effect_params_module = importlib.util.module_from_spec(_EFFECT_PARAMS_SPEC)
_EFFECT_PARAMS_SPEC.loader.exec_module(_effect_params_module)
build_effect_params = _effect_params_module.build_effect_params


class CoolChromaticAberrationEffect:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "strength": (
                    "FLOAT",
                    {"default": 0.01, "min": 0.0, "max": 0.1, "step": 0.001},
                ),
                "radial": ("BOOLEAN", {"default": True}),
            }
        }

    RETURN_TYPES = ("EFFECT_PARAMS",)
    RETURN_NAMES = ("EFFECT_PARAMS",)
    FUNCTION = "execute"
    CATEGORY = "CoolEffects"

    def execute(self, strength, radial):
        return (
            build_effect_params(
                "chromatic_aberration",
                {
                    "u_strength": strength,
                    "u_radial": 1.0 if radial else 0.0,
                },
            ),
        )
