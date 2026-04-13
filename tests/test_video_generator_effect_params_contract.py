import ast
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent.parent
NODE_PATH = PACKAGE_ROOT / "nodes" / "video_generator.py"


def _get_cool_video_generator_class() -> ast.ClassDef:
    module_tree = ast.parse(NODE_PATH.read_text(encoding="utf-8"))
    for node in module_tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "CoolVideoGenerator":
            return node
    raise AssertionError("CoolVideoGenerator class not found")


def _get_method(class_node: ast.ClassDef, method_name: str) -> ast.FunctionDef:
    for node in class_node.body:
        if isinstance(node, ast.FunctionDef) and node.name == method_name:
            return node
    raise AssertionError(f"{method_name} method not found")


def test_input_types_declares_effect_params_as_required_effect_params_type():
    class_node = _get_cool_video_generator_class()
    input_types_method = _get_method(class_node, "INPUT_TYPES")
    return_statement = next(node for node in input_types_method.body if isinstance(node, ast.Return))
    input_types = ast.literal_eval(return_statement.value)
    required_inputs = input_types["required"]

    assert required_inputs["effect_params"] == ("EFFECT_PARAMS",)


def test_input_types_does_not_include_effect_name_string_input():
    class_node = _get_cool_video_generator_class()
    input_types_method = _get_method(class_node, "INPUT_TYPES")
    return_statement = next(node for node in input_types_method.body if isinstance(node, ast.Return))
    input_types = ast.literal_eval(return_statement.value)
    required_inputs = input_types["required"]

    assert "effect_name" not in required_inputs


def test_execute_signature_accepts_effect_params_input():
    class_node = _get_cool_video_generator_class()
    execute_method = _get_method(class_node, "execute")
    execute_parameters = [arg.arg for arg in execute_method.args.args]

    assert execute_parameters == ["self", "image", "effect_params", "fps", "duration"]
