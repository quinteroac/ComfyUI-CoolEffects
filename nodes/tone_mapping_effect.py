"""ComfyUI dedicated tone mapping effect node (none / bw / sepia / duotone)."""

import importlib.util
from pathlib import Path


_EFFECT_PARAMS_PATH = Path(__file__).resolve().parent / "effect_params.py"
_EFFECT_PARAMS_SPEC = importlib.util.spec_from_file_location(
    "cool_effects_effect_params_for_tone_mapping_effect", _EFFECT_PARAMS_PATH
)
if _EFFECT_PARAMS_SPEC is None or _EFFECT_PARAMS_SPEC.loader is None:
    raise ValueError(f"Missing effect params config at {_EFFECT_PARAMS_PATH}")
_effect_params_module = importlib.util.module_from_spec(_EFFECT_PARAMS_SPEC)
_EFFECT_PARAMS_SPEC.loader.exec_module(_effect_params_module)
build_effect_params = _effect_params_module.build_effect_params

_MODE_OPTIONS = ["none", "bw", "sepia", "duotone"]
_MODE_TO_UNIFORM = {
    "none": 0.0,
    "bw": 1.0,
    "sepia": 2.0,
    "duotone": 3.0,
}


class CoolToneMappingEffect:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mode": (_MODE_OPTIONS, {"default": "none"}),
                "intensity": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "shadow_r": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "shadow_g": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "shadow_b": ("FLOAT", {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "highlight_r": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "highlight_g": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "highlight_b": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
            }
        }

    RETURN_TYPES = ("EFFECT_PARAMS",)
    RETURN_NAMES = ("EFFECT_PARAMS",)
    FUNCTION = "execute"
    CATEGORY = "CoolEffects"

    def execute(
        self,
        mode,
        intensity,
        shadow_r,
        shadow_g,
        shadow_b,
        highlight_r,
        highlight_g,
        highlight_b,
    ):
        if mode not in _MODE_TO_UNIFORM:
            raise ValueError(f"Unsupported tone mapping mode: {mode}")

        return (
            build_effect_params(
                "tone_mapping",
                {
                    "u_mode": _MODE_TO_UNIFORM[mode],
                    "u_intensity": intensity,
                    "u_shadow_r": shadow_r,
                    "u_shadow_g": shadow_g,
                    "u_shadow_b": shadow_b,
                    "u_highlight_r": highlight_r,
                    "u_highlight_g": highlight_g,
                    "u_highlight_b": highlight_b,
                },
            ),
        )
