"""ComfyUI Effect Selector node."""

import importlib.util
from pathlib import Path


_LOADER_PATH = Path(__file__).resolve().parent.parent / "shaders" / "loader.py"
_LOADER_SPEC = importlib.util.spec_from_file_location(
    "cool_effects_shader_loader_for_selector", _LOADER_PATH
)
if _LOADER_SPEC is None or _LOADER_SPEC.loader is None:
    raise ValueError(f"Missing shader loader config at {_LOADER_PATH}")
_shader_loader_module = importlib.util.module_from_spec(_LOADER_SPEC)
_LOADER_SPEC.loader.exec_module(_shader_loader_module)
list_shaders = _shader_loader_module.list_shaders


class CoolEffectSelector:
    @classmethod
    def INPUT_TYPES(cls):
        shader_names = list_shaders()
        if not shader_names:
            raise ValueError("No shaders found in shaders/glsl")
        return {
            "required": {
                "image": ("IMAGE",),
                "effect_name": (shader_names, {"default": shader_names[0]}),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("IMAGE", "EFFECT_NAME")
    FUNCTION = "execute"
    CATEGORY = "CoolEffects"

    def execute(self, image, effect_name):
        return (image, effect_name)
