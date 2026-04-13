import importlib.util
import inspect
import uuid
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent.parent
NODE_PATH = PACKAGE_ROOT / "nodes" / "vhs_effect.py"
PACKAGE_INIT = PACKAGE_ROOT / "__init__.py"


def _load_module(module_path: Path):
    module_name = f"cool_effects_test_vhs_module_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_vhs_input_types_expose_native_float_controls():
    module = _load_module(NODE_PATH)
    required_inputs = module.CoolVHSEffect.INPUT_TYPES()["required"]

    assert required_inputs["scanline_intensity"] == (
        "FLOAT",
        {"default": 0.04, "min": 0.0, "max": 0.5, "step": 0.005},
    )
    assert required_inputs["jitter_amount"] == (
        "FLOAT",
        {"default": 0.0018, "min": 0.0, "max": 0.02, "step": 0.0002},
    )
    assert required_inputs["chroma_shift"] == (
        "FLOAT",
        {"default": 0.002, "min": 0.0, "max": 0.02, "step": 0.0002},
    )


def test_vhs_node_declares_effect_params_output_contract():
    module = _load_module(NODE_PATH)

    assert module.CoolVHSEffect.RETURN_TYPES == ("EFFECT_PARAMS",)
    assert module.CoolVHSEffect.RETURN_NAMES == ("EFFECT_PARAMS",)


def test_vhs_execute_returns_vhs_effect_params_bundle():
    module = _load_module(NODE_PATH)
    node = module.CoolVHSEffect()

    output, = node.execute(
        scanline_intensity=0.1,
        jitter_amount=0.01,
        chroma_shift=0.004,
    )

    assert output == {
        "effect_name": "vhs",
        "params": {
            "u_scanline_intensity": 0.1,
            "u_jitter_amount": 0.01,
            "u_chroma_shift": 0.004,
        },
    }


def test_vhs_execute_signature_matches_vhs_controls():
    module = _load_module(NODE_PATH)

    assert list(inspect.signature(module.CoolVHSEffect.execute).parameters) == [
        "self",
        "scanline_intensity",
        "jitter_amount",
        "chroma_shift",
    ]


def test_vhs_node_category_is_cool_effects():
    module = _load_module(NODE_PATH)

    assert module.CoolVHSEffect.CATEGORY == "CoolEffects"


def test_package_registers_cool_vhs_effect_node():
    package_module = _load_module(PACKAGE_INIT)

    assert "CoolVHSEffect" in package_module.NODE_CLASS_MAPPINGS
    assert package_module.NODE_DISPLAY_NAME_MAPPINGS["CoolVHSEffect"] == "Cool VHS Effect"
