import importlib.util
import inspect
import uuid
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent.parent
NODE_PATH = PACKAGE_ROOT / "nodes" / "water_drops_effect.py"
PACKAGE_INIT = PACKAGE_ROOT / "__init__.py"


def _load_module(module_path: Path):
    module_name = f"cool_effects_test_water_drops_module_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_water_drops_input_types_expose_all_numeric_controls_with_ranges():
    module = _load_module(NODE_PATH)
    required_inputs = module.CoolWaterDropsEffect.INPUT_TYPES()["required"]

    assert required_inputs["drop_density"] == (
        "INT",
        {"default": 60, "min": 1, "max": 200, "step": 1},
    )
    assert required_inputs["drop_size"] == (
        "FLOAT",
        {"default": 0.08, "min": 0.01, "max": 0.5, "step": 0.01},
    )
    assert required_inputs["fall_speed"] == (
        "FLOAT",
        {"default": 1.0, "min": 0.1, "max": 5.0, "step": 0.1},
    )
    assert required_inputs["refraction_strength"] == (
        "FLOAT",
        {"default": 0.3, "min": 0.0, "max": 1.0, "step": 0.01},
    )
    assert required_inputs["gravity"] == (
        "FLOAT",
        {"default": 1.0, "min": 0.1, "max": 5.0, "step": 0.1},
    )
    assert required_inputs["wind"] == (
        "FLOAT",
        {"default": 0.0, "min": -2.0, "max": 2.0, "step": 0.1},
    )
    assert required_inputs["blur"] == (
        "FLOAT",
        {"default": 1.0, "min": 0.0, "max": 2.0, "step": 0.1},
    )


def test_water_drops_node_declares_effect_params_output_contract():
    module = _load_module(NODE_PATH)

    assert module.CoolWaterDropsEffect.RETURN_TYPES == ("EFFECT_PARAMS",)
    assert module.CoolWaterDropsEffect.RETURN_NAMES == ("EFFECT_PARAMS",)


def test_water_drops_execute_returns_water_drops_effect_params_bundle():
    module = _load_module(NODE_PATH)
    node = module.CoolWaterDropsEffect()

    output, = node.execute(
        drop_density=120,
        drop_size=0.12,
        fall_speed=2.5,
        refraction_strength=0.5,
        gravity=1.4,
        wind=-0.6,
        blur=1.2,
    )

    assert output == {
        "effect_name": "water_drops",
        "params": {
            "u_drop_density": 120,
            "u_drop_size": 0.12,
            "u_fall_speed": 2.5,
            "u_refraction_strength": 0.5,
            "u_gravity": 1.4,
            "u_wind": -0.6,
            "u_blur": 1.2,
        },
    }


def test_water_drops_execute_signature_matches_all_controls():
    module = _load_module(NODE_PATH)

    assert list(inspect.signature(module.CoolWaterDropsEffect.execute).parameters) == [
        "self",
        "drop_density",
        "drop_size",
        "fall_speed",
        "refraction_strength",
        "gravity",
        "wind",
        "blur",
    ]


def test_water_drops_node_category_is_cool_effects():
    module = _load_module(NODE_PATH)

    assert module.CoolWaterDropsEffect.CATEGORY == "CoolEffects"


def test_package_registers_cool_water_drops_effect_node():
    package_module = _load_module(PACKAGE_INIT)

    assert "CoolWaterDropsEffect" in package_module.NODE_CLASS_MAPPINGS
    assert (
        package_module.NODE_DISPLAY_NAME_MAPPINGS["CoolWaterDropsEffect"]
        == "Cool Water Drops Effect"
    )
