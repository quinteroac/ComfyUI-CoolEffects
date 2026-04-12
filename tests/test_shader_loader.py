import importlib.util
from pathlib import Path

import pytest


PACKAGE_ROOT = Path(__file__).resolve().parent.parent
LOADER_PATH = PACKAGE_ROOT / "shaders" / "loader.py"
GLSL_DIR = PACKAGE_ROOT / "shaders" / "glsl"


def _load_loader_module():
    spec = importlib.util.spec_from_file_location("cool_effects_shader_loader", LOADER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_loader_exports_required_functions():
    module = _load_loader_module()
    assert hasattr(module, "load_shader")
    assert hasattr(module, "load_vertex_shader")
    assert hasattr(module, "list_shaders")
    assert callable(module.load_shader)
    assert callable(module.load_vertex_shader)
    assert callable(module.list_shaders)


def test_load_shader_returns_full_glitch_source():
    module = _load_loader_module()
    expected = (GLSL_DIR / "glitch.frag").read_text(encoding="utf-8")
    assert module.load_shader("glitch") == expected


def test_load_shader_nonexistent_raises_file_not_found_with_name():
    module = _load_loader_module()
    missing_name = "nonexistent"
    with pytest.raises(FileNotFoundError, match=missing_name):
        module.load_shader(missing_name)


def test_load_vertex_shader_returns_fullscreen_quad_source():
    module = _load_loader_module()
    expected = (GLSL_DIR / "fullscreen_quad.vert").read_text(encoding="utf-8")
    assert module.load_vertex_shader() == expected


def test_load_vertex_shader_nonexistent_raises_file_not_found_with_name():
    module = _load_loader_module()
    missing_name = "missing_quad"
    with pytest.raises(FileNotFoundError, match=missing_name):
        module.load_vertex_shader(missing_name)


def test_loader_path_resolution_is_independent_from_cwd(tmp_path, monkeypatch):
    module = _load_loader_module()
    monkeypatch.chdir(tmp_path)
    expected = (GLSL_DIR / "glitch.frag").read_text(encoding="utf-8")
    assert module.load_shader("glitch") == expected


def test_list_shaders_returns_sorted_names_without_extension():
    module = _load_loader_module()
    result = module.list_shaders()
    assert result == sorted(result)
    assert all("." not in shader_name for shader_name in result)
    assert {"glitch", "vhs", "zoom_pulse"}.issubset(set(result))
