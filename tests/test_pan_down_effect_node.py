import importlib.util
import inspect
import uuid
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent.parent
NODE_PATH = PACKAGE_ROOT / "nodes" / "pan_down_effect.py"
PACKAGE_INIT = PACKAGE_ROOT / "__init__.py"


def _load_module(module_path: Path):
    module_name = f"cool_effects_test_pan_down_module_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_pan_down_input_types_expose_native_float_controls():
    module = _load_module(NODE_PATH)
    required_inputs = module.CoolPanDownEffect.INPUT_TYPES()["required"]

    assert required_inputs["speed"] == (
        "FLOAT",
        {"default": 0.2, "min": 0.0, "max": 5.0, "step": 0.05},
    )
    assert required_inputs["origin_x"] == (
        "FLOAT",
        {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01},
    )
    assert required_inputs["origin_y"] == (
        "FLOAT",
        {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01},
    )


def test_pan_down_node_declares_effect_params_output_contract():
    module = _load_module(NODE_PATH)

    assert module.CoolPanDownEffect.RETURN_TYPES == ("EFFECT_PARAMS",)
    assert module.CoolPanDownEffect.RETURN_NAMES == ("EFFECT_PARAMS",)


def test_pan_down_execute_returns_pan_down_effect_params_bundle():
    module = _load_module(NODE_PATH)
    node = module.CoolPanDownEffect()

    output, = node.execute(speed=0.5, origin_x=0.25, origin_y=0.75)

    assert output == {
        "effect_name": "pan_down",
        "params": {"u_speed": 0.5, "u_origin_x": 0.25, "u_origin_y": 0.75},
    }


def test_pan_down_execute_signature_matches_pan_down_controls():
    module = _load_module(NODE_PATH)

    assert list(inspect.signature(module.CoolPanDownEffect.execute).parameters) == [
        "self",
        "speed",
        "origin_x",
        "origin_y",
    ]


def test_pan_down_node_category_is_cool_effects():
    module = _load_module(NODE_PATH)

    assert module.CoolPanDownEffect.CATEGORY == "CoolEffects"


def test_package_registers_cool_pan_down_effect_node():
    package_module = _load_module(PACKAGE_INIT)

    assert "CoolPanDownEffect" in package_module.NODE_CLASS_MAPPINGS
    assert (
        package_module.NODE_DISPLAY_NAME_MAPPINGS["CoolPanDownEffect"]
        == "Cool Pan Down Effect"
    )
