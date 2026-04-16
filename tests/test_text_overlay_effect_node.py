from pathlib import Path
import importlib.util

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_module(module_name: str, module_path: Path):
    module_spec = importlib.util.spec_from_file_location(module_name, module_path)
    if module_spec is None or module_spec.loader is None:
        raise ValueError(f"Missing module config at {module_path}")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def _create_temp_text_overlay_node(
    tmp_path: Path,
    *,
    font_files: list[str] | None = None,
    create_fonts_dir: bool = True,
) -> Path:
    nodes_dir = tmp_path / "nodes"
    assets_fonts_dir = tmp_path / "assets" / "fonts"
    nodes_dir.mkdir(parents=True, exist_ok=True)
    if create_fonts_dir:
        assets_fonts_dir.mkdir(parents=True, exist_ok=True)
        for font_name in font_files or []:
            (assets_fonts_dir / font_name).write_bytes(b"fake-font-bytes")

    source_node = REPO_ROOT / "nodes" / "text_overlay_effect.py"
    source_effect_params = REPO_ROOT / "nodes" / "effect_params.py"
    temp_node = nodes_dir / "text_overlay_effect.py"
    temp_effect_params = nodes_dir / "effect_params.py"
    temp_node.write_text(source_node.read_text(encoding="utf-8"), encoding="utf-8")
    temp_effect_params.write_text(source_effect_params.read_text(encoding="utf-8"), encoding="utf-8")
    return temp_node


def test_text_overlay_inputs_cover_appearance_controls():
    module = _load_module(
        "cool_effects_text_overlay_effect_inputs_test",
        REPO_ROOT / "nodes" / "text_overlay_effect.py",
    )

    required_inputs = module.CoolTextOverlayEffect.INPUT_TYPES()["required"]

    assert required_inputs["text"] == ("STRING", {"default": "Hello World"})
    assert required_inputs["font_size"] == ("INT", {"default": 48, "min": 8, "max": 256, "step": 1})
    assert required_inputs["color_r"] == (
        "FLOAT",
        {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01},
    )
    assert required_inputs["color_g"] == (
        "FLOAT",
        {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01},
    )
    assert required_inputs["color_b"] == (
        "FLOAT",
        {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01},
    )
    assert required_inputs["opacity"] == (
        "FLOAT",
        {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01},
    )
    assert required_inputs["position"] == (
        [
            "top-left",
            "top-center",
            "top-right",
            "center",
            "bottom-left",
            "bottom-center",
            "bottom-right",
        ],
        {"default": "bottom-center"},
    )
    assert required_inputs["offset_x"] == (
        "FLOAT",
        {"default": 0.0, "min": -1.0, "max": 1.0, "step": 0.01},
    )
    assert required_inputs["offset_y"] == (
        "FLOAT",
        {"default": 0.0, "min": -1.0, "max": 1.0, "step": 0.01},
    )
    assert required_inputs["animation"] == (
        ["none", "fade_in", "fade_in_out", "slide_up", "typewriter"],
        {"default": "fade_in"},
    )
    assert required_inputs["animation_duration"] == (
        "FLOAT",
        {"default": 0.5, "min": 0.0, "max": 5.0, "step": 0.01},
    )


def test_execute_outputs_position_and_offsets():
    module = _load_module(
        "cool_effects_text_overlay_effect_execute_test",
        REPO_ROOT / "nodes" / "text_overlay_effect.py",
    )

    node = module.CoolTextOverlayEffect()
    (effect_params,) = node.execute(
        text="caption",
        font="dejavu_sans.ttf",
        font_size=52,
        color_r=0.1,
        color_g=0.2,
        color_b=0.3,
        opacity=0.9,
        position="top-right",
        offset_x=0.25,
        offset_y=-0.15,
        animation="fade_in_out",
        animation_duration=1.2,
    )

    assert effect_params["effect_name"] == "text_overlay"
    assert effect_params["params"]["position"] == "top-right"
    assert effect_params["params"]["offset_x"] == 0.25
    assert effect_params["params"]["offset_y"] == -0.15
    assert effect_params["params"]["animation"] == "fade_in_out"
    assert effect_params["params"]["animation_duration"] == 1.2


def test_font_combo_uses_alphabetical_ttf_scan_order(tmp_path: Path):
    module_path = _create_temp_text_overlay_node(
        tmp_path,
        font_files=["zeta.ttf", "alpha.ttf", "middle.ttf"],
    )
    module = _load_module("cool_effects_text_overlay_effect_fonts_test", module_path)
    font_input = module.CoolTextOverlayEffect.INPUT_TYPES()["required"]["font"]

    assert font_input == (["alpha.ttf", "middle.ttf", "zeta.ttf"], {"default": "alpha.ttf"})


def test_load_time_error_when_fonts_directory_is_missing(tmp_path: Path):
    module_path = _create_temp_text_overlay_node(tmp_path, create_fonts_dir=False)

    with pytest.raises(ValueError, match=r"assets/fonts"):
        _load_module("cool_effects_text_overlay_effect_missing_fonts_dir_test", module_path)


def test_load_time_error_when_fonts_directory_has_no_ttf_files(tmp_path: Path):
    module_path = _create_temp_text_overlay_node(tmp_path, font_files=[])

    with pytest.raises(ValueError, match=r"\.ttf"):
        _load_module("cool_effects_text_overlay_effect_empty_fonts_dir_test", module_path)
