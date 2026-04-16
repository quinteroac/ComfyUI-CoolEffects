from pathlib import Path
import importlib.util


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_module(module_name: str, relative_path: str):
    module_path = REPO_ROOT / relative_path
    module_spec = importlib.util.spec_from_file_location(module_name, module_path)
    if module_spec is None or module_spec.loader is None:
        raise ValueError(f"Missing module config at {module_path}")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def test_video_generator_declares_all_effect_param_slots():
    video_generator_module = _load_module(
        "cool_effects_video_generator_contract_test",
        "nodes/video_generator.py",
    )
    input_types = video_generator_module.CoolVideoGenerator.INPUT_TYPES()
    optional_inputs = input_types["optional"]

    assert optional_inputs["audio"] == ("AUDIO",)
    for slot_index in range(1, 9):
        assert optional_inputs[f"effect_params_{slot_index}"] == (
            video_generator_module.EFFECT_PARAMS,
        )
