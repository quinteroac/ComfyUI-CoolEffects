import importlib.util
import inspect
import uuid
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent.parent
NODE_PATH = PACKAGE_ROOT / "nodes" / "zoom_pulse_effect.py"
PACKAGE_INIT = PACKAGE_ROOT / "__init__.py"


def _load_module(module_path: Path):
    module_name = f"cool_effects_test_zoom_pulse_module_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_zoom_pulse_input_types_expose_native_float_controls():
    module = _load_module(NODE_PATH)
    required_inputs = module.CoolZoomPulseEffect.INPUT_TYPES()["required"]

    assert required_inputs["pulse_amp"] == (
        "FLOAT",
        {"default": 0.06, "min": 0.0, "max": 0.5, "step": 0.005},
    )
    assert required_inputs["pulse_speed"] == (
        "FLOAT",
        {"default": 3.0, "min": 0.1, "max": 20.0, "step": 0.1},
    )


def test_zoom_pulse_node_declares_effect_params_output_contract():
    module = _load_module(NODE_PATH)

    assert module.CoolZoomPulseEffect.RETURN_TYPES == ("EFFECT_PARAMS",)
    assert module.CoolZoomPulseEffect.RETURN_NAMES == ("EFFECT_PARAMS",)


def test_zoom_pulse_execute_returns_zoom_pulse_effect_params_bundle():
    module = _load_module(NODE_PATH)
    node = module.CoolZoomPulseEffect()

    output, = node.execute(pulse_amp=0.12, pulse_speed=6.5)

    assert output == {
        "effect_name": "zoom_pulse",
        "params": {"u_pulse_amp": 0.12, "u_pulse_speed": 6.5},
    }


def test_zoom_pulse_execute_signature_matches_pulse_controls():
    module = _load_module(NODE_PATH)

    assert list(inspect.signature(module.CoolZoomPulseEffect.execute).parameters) == [
        "self",
        "pulse_amp",
        "pulse_speed",
    ]


def test_zoom_pulse_node_category_is_cool_effects():
    module = _load_module(NODE_PATH)

    assert module.CoolZoomPulseEffect.CATEGORY == "CoolEffects"


def test_package_registers_cool_zoom_pulse_effect_node():
    package_module = _load_module(PACKAGE_INIT)

    assert "CoolZoomPulseEffect" in package_module.NODE_CLASS_MAPPINGS
    assert (
        package_module.NODE_DISPLAY_NAME_MAPPINGS["CoolZoomPulseEffect"]
        == "Cool Zoom Pulse Effect"
    )
