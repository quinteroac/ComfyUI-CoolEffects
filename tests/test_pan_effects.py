import importlib.util
import uuid
from pathlib import Path

import pytest

pytest.importorskip("moderngl")
torch = pytest.importorskip("torch")


PACKAGE_ROOT = Path(__file__).resolve().parent.parent
VIDEO_GENERATOR_PATH = PACKAGE_ROOT / "nodes" / "video_generator.py"
EFFECT_PARAMS_PATH = PACKAGE_ROOT / "nodes" / "effect_params.py"

INPUT_IMAGE = torch.linspace(0.0, 1.0, steps=48, dtype=torch.float32).reshape(1, 4, 4, 3)


def _load_module(module_path: Path):
    module_name = f"cool_effects_pan_effects_test_module_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _build_effect_params(effect_name: str, params: dict) -> dict:
    effect_params_module = _load_module(EFFECT_PARAMS_PATH)
    return effect_params_module.build_effect_params(effect_name, params)


def _render_pan_effect(effect_name: str, params: dict):
    video_module = _load_module(VIDEO_GENERATOR_PATH)
    generator = video_module.CoolVideoGenerator()
    output, = generator.execute(
        image=INPUT_IMAGE,
        effect_params=_build_effect_params(effect_name, params),
        fps=1,
        duration=1.0,
    )
    return output


def _assert_output_contract(output):
    assert output.shape == (1, 4, 4, 3)
    assert output.dtype == torch.float32
    assert torch.all(output >= 0.0).item()
    assert torch.all(output <= 1.0).item()


def test_pan_left_render_output_shape_dtype_and_range():
    output = _render_pan_effect(
        "pan_left",
        {"u_speed": 0.2, "u_origin_x": 0.1, "u_origin_y": 0.2},
    )
    _assert_output_contract(output)


def test_pan_right_render_output_shape_dtype_and_range():
    output = _render_pan_effect(
        "pan_right",
        {"u_speed": 0.2, "u_origin_x": 0.1, "u_origin_y": 0.2},
    )
    _assert_output_contract(output)


def test_pan_up_render_output_shape_dtype_and_range():
    output = _render_pan_effect(
        "pan_up",
        {"u_speed": 0.2, "u_origin_x": 0.1, "u_origin_y": 0.2},
    )
    _assert_output_contract(output)


def test_pan_down_render_output_shape_dtype_and_range():
    output = _render_pan_effect(
        "pan_down",
        {"u_speed": 0.2, "u_origin_x": 0.1, "u_origin_y": 0.2},
    )
    _assert_output_contract(output)


def test_pan_diagonal_render_output_shape_dtype_and_range():
    output = _render_pan_effect(
        "pan_diagonal",
        {
            "u_speed": 0.2,
            "u_origin_x": 0.1,
            "u_origin_y": 0.2,
            "u_dir_x": 0.7071,
            "u_dir_y": 0.7071,
        },
    )
    _assert_output_contract(output)
