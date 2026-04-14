import importlib.util
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent.parent
LOADER_PATH = PACKAGE_ROOT / "shaders" / "loader.py"
SHADER_PATH = PACKAGE_ROOT / "shaders" / "glsl" / "frosted_glass.frag"


def _load_loader_module():
    spec = importlib.util.spec_from_file_location(
        "cool_effects_shader_loader_frosted_glass", LOADER_PATH
    )
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_frosted_glass_shader_file_exists():
    assert SHADER_PATH.exists()


def test_frosted_glass_shader_is_loadable_by_name():
    source = _load_loader_module().load_shader("frosted_glass")
    assert source == SHADER_PATH.read_text(encoding="utf-8")


def test_frosted_glass_shader_declares_required_uniform_contract():
    source = _load_loader_module().load_shader("frosted_glass")
    assert "uniform sampler2D u_image;" in source
    assert "uniform float u_time;" in source
    assert "uniform vec2 u_resolution;" in source
    assert "uniform float u_frost_intensity;" in source
    assert "uniform float u_blur_radius;" in source
    assert "uniform float u_uniformity;" in source
    assert "uniform float u_tint_temperature;" in source
    assert "uniform float u_condensation_rate;" in source


def test_frosted_glass_shader_noise_and_animation_depend_on_time():
    source = _load_loader_module().load_shader("frosted_glass")
    assert "time_phase = u_time * 0.22;" in source
    assert "frost_noise = fbm(uv * noise_frequency + vec2(time_phase * 0.28, -time_phase * 0.21));" in source
    assert "u_condensation_rate * u_time" in source
