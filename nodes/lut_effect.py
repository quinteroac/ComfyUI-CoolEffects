"""ComfyUI LUT effect node for applying .cube color transforms."""

import importlib.util
from pathlib import Path


_EFFECT_PARAMS_PATH = Path(__file__).resolve().parent / "effect_params.py"
_EFFECT_PARAMS_SPEC = importlib.util.spec_from_file_location(
    "cool_effects_effect_params_for_lut_effect", _EFFECT_PARAMS_PATH
)
if _EFFECT_PARAMS_SPEC is None or _EFFECT_PARAMS_SPEC.loader is None:
    raise ValueError(f"Missing effect params config at {_EFFECT_PARAMS_PATH}")
_effect_params_module = importlib.util.module_from_spec(_EFFECT_PARAMS_SPEC)
_EFFECT_PARAMS_SPEC.loader.exec_module(_effect_params_module)
build_effect_params = _effect_params_module.build_effect_params

_LUT_UTILS_PATH = Path(__file__).resolve().parent / "lut_utils.py"
_LUT_UTILS_SPEC = importlib.util.spec_from_file_location(
    "cool_effects_lut_utils_for_lut_effect", _LUT_UTILS_PATH
)
if _LUT_UTILS_SPEC is None or _LUT_UTILS_SPEC.loader is None:
    raise ValueError(f"Missing LUT utils config at {_LUT_UTILS_PATH}")
_lut_utils_module = importlib.util.module_from_spec(_LUT_UTILS_SPEC)
_LUT_UTILS_SPEC.loader.exec_module(_lut_utils_module)
parse_cube_lut_file = _lut_utils_module.parse_cube_lut_file


class CoolLUTEffect:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "lut_path": ("STRING", {"default": ""}),
                "intensity": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
            }
        }

    RETURN_TYPES = ("EFFECT_PARAMS",)
    RETURN_NAMES = ("EFFECT_PARAMS",)
    FUNCTION = "execute"
    CATEGORY = "CoolEffects"

    def execute(self, lut_path, intensity):
        parsed_lut = parse_cube_lut_file(lut_path)
        return (
            build_effect_params(
                "lut",
                {
                    "lut_path": parsed_lut["resolved_path"],
                    "u_intensity": intensity,
                },
            ),
        )
