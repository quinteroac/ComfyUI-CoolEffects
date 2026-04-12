import importlib.util
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
    image = object()

    returned_image, effect_name = selector.execute(image, "vhs")

    assert returned_image is image
    assert effect_name == "vhs"
    assert isinstance(effect_name, str)


def test_package_registers_cool_effect_selector_node():
    package_module = _load_module(PACKAGE_INIT)

    assert "CoolEffectSelector" in package_module.NODE_CLASS_MAPPINGS
    assert package_module.NODE_DISPLAY_NAME_MAPPINGS["CoolEffectSelector"] == "Cool Effect Selector"
