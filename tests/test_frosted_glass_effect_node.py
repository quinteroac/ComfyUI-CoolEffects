import importlib.util
import inspect
import uuid
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent.parent
NODE_PATH = PACKAGE_ROOT / "nodes" / "frosted_glass_effect.py"
PACKAGE_INIT = PACKAGE_ROOT / "__init__.py"


def _load_module(module_path: Path):
    module_name = f"cool_effects_test_frosted_glass_module_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_frosted_glass_input_types_expose_all_numeric_controls_with_ranges():
    module = _load_module(NODE_PATH)
    required_inputs = module.CoolFrostedGlassEffect.INPUT_TYPES()["required"]

    assert required_inputs["frost_intensity"] == (
        "FLOAT",
        {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01},
    )
    assert required_inputs["blur_radius"] == (
        "FLOAT",
        {"default": 0.015, "min": 0.0, "max": 0.05, "step": 0.001},
    )
    assert required_inputs["uniformity"] == (
        "FLOAT",
        {"default": 0.6, "min": 0.0, "max": 1.0, "step": 0.01},
    )
    assert required_inputs["tint_temperature"] == (
        "FLOAT",
        {"default": 0.0, "min": -1.0, "max": 1.0, "step": 0.01},
    )
    assert required_inputs["condensation_rate"] == (
        "FLOAT",
        {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01},
    )


def test_frosted_glass_node_declares_effect_params_output_contract():
    module = _load_module(NODE_PATH)

    assert module.CoolFrostedGlassEffect.RETURN_TYPES == ("EFFECT_PARAMS",)
    assert module.CoolFrostedGlassEffect.RETURN_NAMES == ("EFFECT_PARAMS",)


def test_frosted_glass_execute_returns_frosted_glass_effect_params_bundle():
    module = _load_module(NODE_PATH)
    node = module.CoolFrostedGlassEffect()

    output, = node.execute(
        frost_intensity=1.0,
        blur_radius=0.05,
        uniformity=0.0,
        tint_temperature=-1.0,
        condensation_rate=1.0,
    )

    assert output == {
        "effect_name": "frosted_glass",
        "params": {
            "u_frost_intensity": 1.0,
            "u_blur_radius": 0.05,
            "u_uniformity": 0.0,
            "u_tint_temperature": -1.0,
            "u_condensation_rate": 1.0,
        },
    }


def test_frosted_glass_execute_signature_matches_all_controls():
    module = _load_module(NODE_PATH)

    assert list(inspect.signature(module.CoolFrostedGlassEffect.execute).parameters) == [
        "self",
        "frost_intensity",
        "blur_radius",
        "uniformity",
        "tint_temperature",
        "condensation_rate",
    ]


def test_frosted_glass_node_category_is_cool_effects():
    module = _load_module(NODE_PATH)

    assert module.CoolFrostedGlassEffect.CATEGORY == "CoolEffects"


def test_package_registers_cool_frosted_glass_effect_node():
    package_module = _load_module(PACKAGE_INIT)

    assert "CoolFrostedGlassEffect" in package_module.NODE_CLASS_MAPPINGS
    assert (
        package_module.NODE_DISPLAY_NAME_MAPPINGS["CoolFrostedGlassEffect"]
        == "Cool Frosted Glass Effect"
    )
