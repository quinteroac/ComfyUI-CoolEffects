import importlib.util
import inspect
import uuid
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent.parent
NODE_PATH = PACKAGE_ROOT / "nodes" / "glitch_effect.py"
PACKAGE_INIT = PACKAGE_ROOT / "__init__.py"


def _load_module(module_path: Path):
    module_name = f"cool_effects_test_glitch_module_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_glitch_input_types_expose_native_float_controls():
    module = _load_module(NODE_PATH)
    required_inputs = module.CoolGlitchEffect.INPUT_TYPES()["required"]

    assert required_inputs["wave_freq"] == (
        "FLOAT",
        {"default": 120.0, "min": 1.0, "max": 500.0, "step": 1.0},
    )
    assert required_inputs["wave_amp"] == (
        "FLOAT",
        {"default": 0.0025, "min": 0.0, "max": 0.05, "step": 0.0005},
    )
    assert required_inputs["speed"] == (
        "FLOAT",
        {"default": 10.0, "min": 0.0, "max": 100.0, "step": 0.5},
    )


def test_glitch_node_declares_effect_params_output_contract():
    module = _load_module(NODE_PATH)

    assert module.CoolGlitchEffect.RETURN_TYPES == ("EFFECT_PARAMS",)
    assert module.CoolGlitchEffect.RETURN_NAMES == ("EFFECT_PARAMS",)


def test_glitch_execute_returns_glitch_effect_params_bundle():
    module = _load_module(NODE_PATH)
    node = module.CoolGlitchEffect()

    output, = node.execute(wave_freq=90.0, wave_amp=0.01, speed=8.5)

    assert output == {
        "effect_name": "glitch",
        "params": {"u_wave_freq": 90.0, "u_wave_amp": 0.01, "u_speed": 8.5},
    }


def test_glitch_execute_signature_matches_wave_controls():
    module = _load_module(NODE_PATH)

    assert list(inspect.signature(module.CoolGlitchEffect.execute).parameters) == [
        "self",
        "wave_freq",
        "wave_amp",
        "speed",
    ]


def test_glitch_node_category_is_cool_effects():
    module = _load_module(NODE_PATH)

    assert module.CoolGlitchEffect.CATEGORY == "CoolEffects"


def test_package_registers_cool_glitch_effect_node():
    package_module = _load_module(PACKAGE_INIT)

    assert "CoolGlitchEffect" in package_module.NODE_CLASS_MAPPINGS
    assert package_module.NODE_DISPLAY_NAME_MAPPINGS["CoolGlitchEffect"] == "Cool Glitch Effect"
