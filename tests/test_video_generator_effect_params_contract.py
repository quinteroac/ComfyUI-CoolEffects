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


def _get_module_tree() -> ast.Module:
    return ast.parse(NODE_PATH.read_text(encoding="utf-8"))


def _get_method(class_node: ast.ClassDef, method_name: str) -> ast.FunctionDef:
    for node in class_node.body:
        if isinstance(node, ast.FunctionDef) and node.name == method_name:
            return node
    raise AssertionError(f"{method_name} method not found")


def _get_module_function(module_tree: ast.Module, func_name: str) -> ast.FunctionDef:
    for node in module_tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            return node
    raise AssertionError(f"Module-level function '{func_name}' not found")


def _subscript_string_key(node: ast.Subscript) -> str | None:
    slice_node = node.slice
    if isinstance(slice_node, ast.Constant) and isinstance(slice_node.value, str):
        return slice_node.value
    return None


def _dict_value_for_key(dict_node: ast.Dict, key: str):
    for existing_key, value in zip(dict_node.keys, dict_node.values):
        if isinstance(existing_key, ast.Constant) and existing_key.value == key:
            return value
    raise AssertionError(f"Key '{key}' not found")


def test_video_generator_loads_effect_params_constant_from_effect_params_module():
    module_tree = _get_module_tree()

    assignments = [
        node for node in module_tree.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == "EFFECT_PARAMS"
    ]
    assert assignments, "EFFECT_PARAMS must be assigned at module scope"

    value = assignments[0].value
    assert isinstance(value, ast.Attribute)
    assert isinstance(value.value, ast.Name)
    assert value.value.id == "_effect_params_module"
    assert value.attr == "EFFECT_PARAMS"


def test_input_types_declares_effect_params_1_as_optional_effect_params_type():
    class_node = _get_cool_video_generator_class()
    input_types_method = _get_method(class_node, "INPUT_TYPES")
    return_statement = next(node for node in input_types_method.body if isinstance(node, ast.Return))
    input_types = return_statement.value
    assert isinstance(input_types, ast.Dict)
    optional_inputs = _dict_value_for_key(input_types, "optional")
    assert isinstance(optional_inputs, ast.Dict)
    effect_params_input = _dict_value_for_key(optional_inputs, "effect_params_1")
    assert isinstance(effect_params_input, ast.Tuple)
    assert len(effect_params_input.elts) == 1
    assert isinstance(effect_params_input.elts[0], ast.Name)
    assert effect_params_input.elts[0].id == "EFFECT_PARAMS"


def test_input_types_declares_effect_count_as_required_int():
    class_node = _get_cool_video_generator_class()
    input_types_method = _get_method(class_node, "INPUT_TYPES")
    return_statement = next(node for node in input_types_method.body if isinstance(node, ast.Return))
    input_types = return_statement.value
    assert isinstance(input_types, ast.Dict)
    required_inputs = _dict_value_for_key(input_types, "required")
    assert isinstance(required_inputs, ast.Dict)
    effect_count_input = _dict_value_for_key(required_inputs, "effect_count")
    assert isinstance(effect_count_input, ast.Tuple)
    assert len(effect_count_input.elts) >= 1
    assert isinstance(effect_count_input.elts[0], ast.Constant)
    assert effect_count_input.elts[0].value == "INT"


def test_input_types_does_not_include_effect_name_string_input():
    class_node = _get_cool_video_generator_class()
    input_types_method = _get_method(class_node, "INPUT_TYPES")
    return_statement = next(node for node in input_types_method.body if isinstance(node, ast.Return))
    input_types = return_statement.value
    assert isinstance(input_types, ast.Dict)
    required_inputs = _dict_value_for_key(input_types, "required")
    assert isinstance(required_inputs, ast.Dict)

    required_keys = {
        key.value for key in required_inputs.keys
        if isinstance(key, ast.Constant) and isinstance(key.value, str)
    }
    assert "effect_name" not in required_keys


def test_execute_signature_accepts_effect_count_and_kwargs():
    class_node = _get_cool_video_generator_class()
    execute_method = _get_method(class_node, "execute")
    execute_parameters = [arg.arg for arg in execute_method.args.args]
    assert "self" in execute_parameters
    assert "image" in execute_parameters
    assert "fps" in execute_parameters
    assert "duration" in execute_parameters
    assert "effect_count" in execute_parameters
    # **kwargs must be present to receive dynamic effect_params_N inputs
    assert execute_method.args.kwarg is not None, "execute must accept **kwargs"


def test_render_frames_calls_merge_params_with_effect_params_bundle_fields():
    """_render_frames is the helper that owns the GL rendering loop."""
    module_tree = _get_module_tree()
    render_frames = _get_module_function(module_tree, "_render_frames")

    merge_calls = [
        node for node in ast.walk(render_frames)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "merge_params"
    ]
    assert merge_calls, "_render_frames must call merge_params(...)"

    found_effect_name_subscript = False
    found_params_subscript = False
    for call in merge_calls:
        for arg in call.args:
            if (
                isinstance(arg, ast.Subscript)
                and isinstance(arg.value, ast.Name)
                and arg.value.id == "effect_params"
            ):
                key = _subscript_string_key(arg)
                if key == "effect_name":
                    found_effect_name_subscript = True
                if key == "params":
                    found_params_subscript = True

    assert found_effect_name_subscript, "_render_frames must pass effect_params['effect_name'] to merge_params"
    assert found_params_subscript, "_render_frames must pass effect_params['params'] to merge_params"


def test_render_frames_sets_merged_uniforms_per_frame_with_float_cast_and_missing_skip():
    module_tree = _get_module_tree()
    render_frames = _get_module_function(module_tree, "_render_frames")

    frame_loops = [
        node for node in ast.walk(render_frames)
        if isinstance(node, ast.For)
        and isinstance(node.iter, ast.Call)
        and isinstance(node.iter.func, ast.Name)
        and node.iter.func.id == "range"
    ]
    assert frame_loops, "_render_frames must iterate over rendered frames"

    found_inner_uniform_loop = False
    found_float_assignment = False
    found_missing_uniform_skip = False

    for frame_loop in frame_loops:
        inner_loops = [node for node in frame_loop.body if isinstance(node, ast.For)]
        for inner_loop in inner_loops:
            if not (
                isinstance(inner_loop.iter, ast.Call)
                and isinstance(inner_loop.iter.func, ast.Attribute)
                and isinstance(inner_loop.iter.func.value, ast.Name)
                and inner_loop.iter.func.value.id == "final_uniform_params"
                and inner_loop.iter.func.attr == "items"
            ):
                continue
            found_inner_uniform_loop = True

            for node in ast.walk(inner_loop):
                if isinstance(node, ast.Assign):
                    if len(node.targets) != 1:
                        continue
                    target = node.targets[0]
                    if not (
                        isinstance(target, ast.Attribute)
                        and target.attr == "value"
                        and isinstance(target.value, ast.Subscript)
                        and isinstance(target.value.value, ast.Name)
                        and target.value.value.id == "program"
                    ):
                        continue
                    if (
                        isinstance(node.value, ast.Call)
                        and isinstance(node.value.func, ast.Name)
                        and node.value.func.id == "float"
                        and len(node.value.args) == 1
                        and isinstance(node.value.args[0], ast.Name)
                        and node.value.args[0].id == "uniform_value"
                    ):
                        found_float_assignment = True

                if isinstance(node, ast.ExceptHandler):
                    if isinstance(node.type, ast.Name) and node.type.id == "KeyError":
                        found_missing_uniform_skip = True

    assert found_inner_uniform_loop, "_render_frames must loop through final_uniform_params.items() inside frame loop"
    assert found_float_assignment, "_render_frames must assign float(uniform_value) to program[uniform_name].value"
    assert found_missing_uniform_skip, "_render_frames must skip missing uniforms via KeyError handling"


def test_render_frames_keeps_base_uniform_assignments():
    module_tree = _get_module_tree()
    render_frames = _get_module_function(module_tree, "_render_frames")

    has_u_image_assignment = False
    has_u_resolution_assignment = False
    has_u_time_assignment = False

    for node in ast.walk(render_frames):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not (
            isinstance(target, ast.Attribute)
            and target.attr == "value"
            and isinstance(target.value, ast.Subscript)
            and isinstance(target.value.value, ast.Name)
            and target.value.value.id == "program"
        ):
            continue
        key = _subscript_string_key(target.value)
        if key == "u_image":
            has_u_image_assignment = True
        elif key == "u_resolution":
            has_u_resolution_assignment = True
        elif key == "u_time":
            has_u_time_assignment = True

    assert has_u_image_assignment
    assert has_u_resolution_assignment
    assert has_u_time_assignment
