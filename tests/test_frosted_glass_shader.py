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


def test_frosted_glass_shader_samples_eight_perturbed_directions():
    source = _load_loader_module().load_shader("frosted_glass")
    assert "for (int i = 0; i < 8; i++)" in source
    assert "float dir_noise = hash12(noise_seed + vec2(float(i) * 17.0, time_phase * 13.0));" in source
    assert "float radial_noise = hash12(noise_seed.yx + vec2(float(i) * 11.0, -time_phase * 7.0));" in source
    assert "float angle_perturb = (dir_noise - 0.5) * 0.55;" in source
    assert "float radial_offset = blur_radius * (1.0 + base_jitter * 0.35 + (radial_noise - 0.5) * 0.8);" in source


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _shader_blur_mix(frost_intensity: float, condensation: float) -> float:
    return _clamp(frost_intensity * 0.7 + condensation * 0.25, 0.0, 1.0)


def _shader_frost_veil(frost_intensity: float, condensation: float) -> float:
    return _clamp(condensation * (0.2 + frost_intensity * 0.35), 0.0, 0.65)


def test_frosted_glass_shader_medium_settings_soften_detail_but_keep_shapes():
    blur_radius = 0.015
    frost_intensity = 0.5
    condensation = 0.5
    blur_mix = _shader_blur_mix(frost_intensity, condensation)
    frost_veil = _shader_frost_veil(frost_intensity, condensation)
    blur_radius_px = blur_radius * 512.0

    assert 0.4 <= blur_mix <= 0.6
    assert 0.12 <= frost_veil <= 0.25
    assert 4.0 <= blur_radius_px <= 10.0
    assert (1.0 - blur_mix) >= 0.4


def test_frosted_glass_shader_high_settings_heavily_obscure_image():
    source = _load_loader_module().load_shader("frosted_glass")
    blur_radius = 0.04
    frost_intensity = 1.0
    condensation = 1.0
    blur_mix = _shader_blur_mix(frost_intensity, condensation)
    frost_veil = _shader_frost_veil(frost_intensity, condensation)
    blur_radius_px = blur_radius * 512.0

    assert blur_mix >= 0.9
    assert frost_veil >= 0.5
    assert blur_radius_px >= 18.0
    assert (1.0 - blur_mix) <= 0.1
    assert "vec3 frosted_color = softened * tint + vec3(0.14) * patch_mask * condensation;" in source
    assert "vec3 final_color = mix(veiled_color, vec3(1.0), frost_veil * patch_mask);" in source
