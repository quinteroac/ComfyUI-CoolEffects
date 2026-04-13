import importlib.util
from pathlib import Path

import pytest


PACKAGE_ROOT = Path(__file__).resolve().parent.parent
LOADER_PATH = PACKAGE_ROOT / "shaders" / "loader.py"
GLSL_DIR = PACKAGE_ROOT / "shaders" / "glsl"
README_PATH = PACKAGE_ROOT / "shaders" / "README.md"
EXPECTED_SHADERS = ("glitch", "vhs", "zoom_pulse", "pan_left", "pan_right")

VERTEX_SHADER_SOURCE = """
#version 330
in vec2 in_pos;
void main() {
    gl_Position = vec4(in_pos, 0.0, 1.0);
}
"""


def _load_loader_module():
    spec = importlib.util.spec_from_file_location("cool_effects_shader_loader", LOADER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_required_shader_files_exist():
    for shader_name in EXPECTED_SHADERS:
        assert (GLSL_DIR / f"{shader_name}.frag").exists()


def test_shaders_declare_required_uniforms():
    loader_module = _load_loader_module()
    for shader_name in EXPECTED_SHADERS:
        source = loader_module.load_shader(shader_name)
        assert "uniform sampler2D u_image;" in source
        assert "uniform float u_time;" in source
        assert "uniform vec2 u_resolution;" in source


def test_glitch_shader_declares_per_effect_uniforms():
    source = _load_loader_module().load_shader("glitch")

    assert "uniform float u_wave_freq;" in source
    assert "uniform float u_wave_amp;" in source
    assert "uniform float u_speed;" in source


def test_glitch_shader_wave_formula_uses_per_effect_uniforms():
    source = _load_loader_module().load_shader("glitch")

    assert "sin(uv.y * u_wave_freq + u_time * u_speed) * u_wave_amp" in source


def test_glitch_shader_has_no_hardcoded_wave_constants():
    source = _load_loader_module().load_shader("glitch")

    assert "uv.y * 120.0" not in source
    assert "u_time * 10.0" not in source
    assert "* 0.0025" not in source


def test_vhs_shader_declares_per_effect_uniforms():
    source = _load_loader_module().load_shader("vhs")

    assert "uniform float u_scanline_intensity;" in source
    assert "uniform float u_jitter_amount;" in source
    assert "uniform float u_chroma_shift;" in source


def test_vhs_shader_uses_uniforms_for_default_equivalent_behavior():
    source = _load_loader_module().load_shader("vhs")

    assert "sin(uv.y * u_resolution.y * 0.75) * u_scanline_intensity" in source
    assert "sin((uv.y + u_time * 2.0) * 90.0) * u_jitter_amount" in source
    assert "vec2(u_chroma_shift + jitter, 0.0)" in source
    assert "vec2(-u_chroma_shift + jitter, 0.0)" in source


def test_vhs_shader_has_no_hardcoded_per_effect_constants():
    source = _load_loader_module().load_shader("vhs")

    assert "* 0.04" not in source
    assert "* 0.0018" not in source
    assert "0.002 + jitter" not in source
    assert "-0.002 + jitter" not in source


def test_zoom_pulse_shader_declares_per_effect_uniforms():
    source = _load_loader_module().load_shader("zoom_pulse")

    assert "uniform float u_pulse_amp;" in source
    assert "uniform float u_pulse_speed;" in source


def test_zoom_pulse_shader_uses_uniforms_for_default_equivalent_behavior():
    source = _load_loader_module().load_shader("zoom_pulse")

    assert "u_pulse_amp * sin(u_time * u_pulse_speed)" in source


def test_zoom_pulse_shader_has_no_hardcoded_per_effect_constants():
    source = _load_loader_module().load_shader("zoom_pulse")

    assert "0.06 * sin(" not in source
    assert "u_time * 3.0" not in source


def test_pan_left_shader_declares_per_effect_uniforms():
    source = _load_loader_module().load_shader("pan_left")

    assert "uniform float u_speed;" in source
    assert "uniform float u_origin_x;" in source
    assert "uniform float u_origin_y;" in source


def test_pan_left_shader_starts_at_origin_and_scrolls_left_with_wrapped_uv():
    source = _load_loader_module().load_shader("pan_left")

    assert "vec2 origin_uv = uv + vec2(u_origin_x, u_origin_y);" in source
    assert "vec2 scroll_offset = vec2(-u_speed * u_time, 0.0);" in source
    assert "vec2 wrapped_uv = fract(origin_uv + scroll_offset);" in source


def test_pan_right_shader_declares_per_effect_uniforms():
    source = _load_loader_module().load_shader("pan_right")

    assert "uniform float u_speed;" in source
    assert "uniform float u_origin_x;" in source
    assert "uniform float u_origin_y;" in source


def test_pan_right_shader_starts_at_origin_and_scrolls_right_with_wrapped_uv():
    source = _load_loader_module().load_shader("pan_right")

    assert "vec2 origin_uv = uv + vec2(u_origin_x, u_origin_y);" in source
    assert "vec2 scroll_offset = vec2(u_speed * u_time, 0.0);" in source
    assert "vec2 wrapped_uv = fract(origin_uv + scroll_offset);" in source


def test_shaders_compile_in_moderngl():
    moderngl = pytest.importorskip("moderngl")
    loader_module = _load_loader_module()
    ctx = None
    try:
        try:
            ctx = moderngl.create_standalone_context()
        except Exception as error:  # pragma: no cover - environment-specific backend availability
            pytest.skip(f"ModernGL standalone context unavailable: {error}")

        for shader_name in EXPECTED_SHADERS:
            fragment_source = loader_module.load_shader(shader_name)
            program = ctx.program(
                vertex_shader=VERTEX_SHADER_SOURCE,
                fragment_shader=fragment_source,
            )
            program.release()
    finally:
        if ctx is not None:
            ctx.release()


def test_shader_readme_documents_uniform_contract():
    assert README_PATH.exists()
    content = README_PATH.read_text(encoding="utf-8")
    assert "Required uniforms" in content
    assert "`uniform sampler2D u_image`" in content
    assert "`uniform float u_time`" in content
    assert "`uniform vec2 u_resolution`" in content
    assert "Per-effect uniforms and defaults" in content
    assert "### `glitch.frag`" in content
    assert "`uniform float u_wave_freq` — default: `120.0`" in content
    assert "`uniform float u_wave_amp` — default: `0.0025`" in content
    assert "`uniform float u_speed` — default: `10.0`" in content
    assert "### `vhs.frag`" in content
    assert (
        "`uniform float u_scanline_intensity` — default: `0.04`" in content
    )
    assert "`uniform float u_jitter_amount` — default: `0.0018`" in content
    assert "`uniform float u_chroma_shift` — default: `0.002`" in content
    assert "### `zoom_pulse.frag`" in content
    assert "`uniform float u_pulse_amp` — default: `0.06`" in content
    assert "`uniform float u_pulse_speed` — default: `3.0`" in content
    assert "### `pan_left.frag`" in content
    assert "`uniform float u_speed` — default: `0.1`" in content
    assert "`uniform float u_origin_x` — default: `0.0`" in content
    assert "`uniform float u_origin_y` — default: `0.0`" in content
    assert "### `pan_right.frag`" in content
