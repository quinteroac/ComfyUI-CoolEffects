import importlib.util
from pathlib import Path

import pytest


PACKAGE_ROOT = Path(__file__).resolve().parent.parent
LOADER_PATH = PACKAGE_ROOT / "shaders" / "loader.py"
GLSL_DIR = PACKAGE_ROOT / "shaders" / "glsl"
README_PATH = PACKAGE_ROOT / "shaders" / "README.md"
EXPECTED_SHADERS = ("glitch", "vhs", "zoom_pulse")

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
