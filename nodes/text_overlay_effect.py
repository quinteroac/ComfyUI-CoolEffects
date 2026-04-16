"""ComfyUI dedicated Text Overlay effect node."""

import importlib.util
from pathlib import Path


_EFFECT_PARAMS_PATH = Path(__file__).resolve().parent / "effect_params.py"
_EFFECT_PARAMS_SPEC = importlib.util.spec_from_file_location(
    "cool_effects_effect_params_for_text_overlay_effect", _EFFECT_PARAMS_PATH
)
if _EFFECT_PARAMS_SPEC is None or _EFFECT_PARAMS_SPEC.loader is None:
    raise ValueError(f"Missing effect params config at {_EFFECT_PARAMS_PATH}")
_effect_params_module = importlib.util.module_from_spec(_EFFECT_PARAMS_SPEC)
_EFFECT_PARAMS_SPEC.loader.exec_module(_effect_params_module)
build_effect_params = _effect_params_module.build_effect_params

_FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"


def _scan_font_options(fonts_dir: Path) -> list[str]:
    if not fonts_dir.exists():
        raise ValueError(
            f"Font directory is missing at {fonts_dir}. Add at least one .ttf file under assets/fonts/."
        )
    if not fonts_dir.is_dir():
        raise ValueError(
            f"Font path is not a directory: {fonts_dir}. Expected assets/fonts/ containing .ttf files."
        )

    font_options = sorted(
        [font_file.name for font_file in fonts_dir.glob("*.ttf") if font_file.is_file()],
        key=str.lower,
    )
    if not font_options:
        raise ValueError(
            f"No .ttf files found in {fonts_dir}. Add at least one font file to assets/fonts/."
        )
    return font_options


_FONT_OPTIONS = _scan_font_options(_FONTS_DIR)
_POSITION_OPTIONS = [
    "top-left",
    "top-center",
    "top-right",
    "center",
    "bottom-left",
    "bottom-center",
    "bottom-right",
]
_ANIMATION_OPTIONS = [
    "none",
    "fade_in",
    "fade_in_out",
    "slide_up",
    "typewriter",
]


class CoolTextOverlayEffect:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"default": "Hello World"}),
                "font": (_FONT_OPTIONS, {"default": _FONT_OPTIONS[0]}),
                "font_size": ("INT", {"default": 48, "min": 8, "max": 256, "step": 1}),
                "color_r": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "color_g": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "color_b": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "opacity": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
                "position": (_POSITION_OPTIONS, {"default": "bottom-center"}),
                "offset_x": ("FLOAT", {"default": 0.0, "min": -1.0, "max": 1.0, "step": 0.01}),
                "offset_y": ("FLOAT", {"default": 0.0, "min": -1.0, "max": 1.0, "step": 0.01}),
                "animation": (_ANIMATION_OPTIONS, {"default": "fade_in"}),
                "animation_duration": (
                    "FLOAT",
                    {"default": 0.5, "min": 0.0, "max": 5.0, "step": 0.01},
                ),
            }
        }

    RETURN_TYPES = ("EFFECT_PARAMS",)
    RETURN_NAMES = ("EFFECT_PARAMS",)
    FUNCTION = "execute"
    CATEGORY = "CoolEffects"

    def execute(
        self,
        text,
        font,
        font_size,
        color_r,
        color_g,
        color_b,
        opacity,
        position,
        offset_x,
        offset_y,
        animation,
        animation_duration,
    ):
        return (
            build_effect_params(
                "text_overlay",
                {
                    "text": text,
                    "font": font,
                    "font_size": font_size,
                    "color_r": color_r,
                    "color_g": color_g,
                    "color_b": color_b,
                    "opacity": opacity,
                    "position": position,
                    "offset_x": offset_x,
                    "offset_y": offset_y,
                    "animation": animation,
                    "animation_duration": animation_duration,
                },
            ),
        )
