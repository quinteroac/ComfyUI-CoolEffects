import importlib.util
import inspect
import uuid
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent.parent
NODE_PATH = PACKAGE_ROOT / "nodes" / "effect_selector.py"
PACKAGE_INIT = PACKAGE_ROOT / "__init__.py"


def _load_module(module_path: Path):
    module_name = f"cool_effects_test_module_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_input_types_exposes_dropdown_with_all_shaders(monkeypatch):
    module = _load_module(NODE_PATH)
    monkeypatch.setattr(module, "list_shaders", lambda: ["glitch", "vhs", "zoom_pulse"])

    input_types = module.CoolEffectSelector.INPUT_TYPES()
    effect_name_input = input_types["required"]["effect_name"]

    assert effect_name_input[0] == ["glitch", "vhs", "zoom_pulse"]
    assert effect_name_input[1]["default"] == "glitch"


def test_execute_returns_effect_name_as_string_output():
    module = _load_module(NODE_PATH)
    selector = module.CoolEffectSelector()

    effect_name, = selector.execute("vhs")

    assert effect_name == "vhs"
    assert isinstance(effect_name, str)


def test_node_declares_only_effect_name_input_and_string_output(monkeypatch):
    module = _load_module(NODE_PATH)
    monkeypatch.setattr(module, "list_shaders", lambda: ["glitch"])

    input_types = module.CoolEffectSelector.INPUT_TYPES()

    required_inputs = input_types.get("required", {})
    optional_inputs = input_types.get("optional", {})

    assert "image" not in required_inputs
    assert "image" not in optional_inputs
    assert required_inputs["effect_name"] == (["glitch"], {"default": "glitch"})
    assert module.CoolEffectSelector.RETURN_TYPES == ("STRING",)
    assert module.CoolEffectSelector.RETURN_NAMES == ("EFFECT_NAME",)


def test_execute_signature_accepts_only_effect_name():
    module = _load_module(NODE_PATH)
    execute_parameters = list(inspect.signature(module.CoolEffectSelector.execute).parameters)

    assert execute_parameters == ["self", "effect_name"]


def test_node_category_is_cool_effects():
    module = _load_module(NODE_PATH)

    assert module.CoolEffectSelector.CATEGORY == "CoolEffects"


def test_package_registers_cool_effect_selector_node():
    package_module = _load_module(PACKAGE_INIT)

    assert "CoolEffectSelector" in package_module.NODE_CLASS_MAPPINGS
    assert package_module.NODE_DISPLAY_NAME_MAPPINGS["CoolEffectSelector"] == "Cool Effect Selector"
