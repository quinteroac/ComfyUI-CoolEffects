import importlib.util
from pathlib import Path

import pytest


PACKAGE_ROOT = Path(__file__).resolve().parent.parent
EFFECT_PARAMS_PATH = PACKAGE_ROOT / "nodes" / "effect_params.py"


def _load_effect_params_module():
    spec = importlib.util.spec_from_file_location("cool_effects_effect_params", EFFECT_PARAMS_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_exports_effect_params_type_string():
    module = _load_effect_params_module()

    assert module.EFFECT_PARAMS == "EFFECT_PARAMS"


def test_build_effect_params_returns_contract_shape():
    module = _load_effect_params_module()

    payload = module.build_effect_params(
        "glitch",
        {"u_wave_freq": 120.0, "u_wave_amp": 0.0025, "u_speed": 10.0},
    )

    assert payload == {
        "effect_name": "glitch",
        "params": {"u_wave_freq": 120.0, "u_wave_amp": 0.0025, "u_speed": 10.0},
    }


def test_build_effect_params_raises_value_error_for_empty_effect_name():
    module = _load_effect_params_module()

    with pytest.raises(ValueError, match="effect_name"):
        module.build_effect_params("", {})


def test_build_effect_params_raises_value_error_for_non_dict_params():
    module = _load_effect_params_module()

    with pytest.raises(ValueError, match="params"):
        module.build_effect_params("glitch", [1, 2, 3])


def test_default_params_contains_original_defaults_for_all_effects():
    module = _load_effect_params_module()

    assert module.DEFAULT_PARAMS["glitch"] == {
        "u_wave_freq": 120.0,
        "u_wave_amp": 0.0025,
        "u_speed": 10.0,
    }
    assert module.DEFAULT_PARAMS["vhs"] == {
        "u_scanline_intensity": 0.04,
        "u_jitter_amount": 0.0018,
        "u_chroma_shift": 0.002,
    }
    assert module.DEFAULT_PARAMS["zoom_pulse"] == {
        "u_pulse_amp": 0.06,
        "u_pulse_speed": 3.0,
    }


def test_merge_params_overrides_defaults_with_incoming_params():
    module = _load_effect_params_module()

    merged = module.merge_params(
        "glitch",
        {"u_wave_amp": 0.02, "u_speed": 7.5},
    )

    assert merged == {
        "u_wave_freq": 120.0,
        "u_wave_amp": 0.02,
        "u_speed": 7.5,
    }


def test_merge_params_raises_key_error_for_unknown_effect():
    module = _load_effect_params_module()

    with pytest.raises(KeyError, match="unknown_effect"):
        module.merge_params("unknown_effect", {})
