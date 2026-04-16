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


def test_timing_uniforms_are_second_based_across_frame_rates():
    module = _load_module("cool_effects_text_overlay_timing_test", "nodes/video_generator.py")
    uniforms_30fps = module._resolve_timing_uniforms(frame_index=30, fps=30, duration=3.0)
    uniforms_60fps = module._resolve_timing_uniforms(frame_index=60, fps=60, duration=3.0)

    assert uniforms_30fps["u_time"] == 1.0
    assert uniforms_60fps["u_time"] == 1.0
    assert uniforms_30fps["u_duration"] == 3.0
    assert uniforms_60fps["u_duration"] == 3.0


def test_typewriter_visible_text_is_progressive_by_animation_duration():
    module = _load_module("cool_effects_text_overlay_typewriter_test", "nodes/video_generator.py")

    assert module._resolve_typewriter_visible_text("Hello", 0.0, 1.0) == ""
    assert module._resolve_typewriter_visible_text("Hello", 0.2, 1.0) == "H"
    assert module._resolve_typewriter_visible_text("Hello", 0.6, 1.0) == "Hel"
    assert module._resolve_typewriter_visible_text("Hello", 1.0, 1.0) == "Hello"
    assert module._resolve_typewriter_visible_text("Hello", 2.0, 1.0) == "Hello"


def test_animation_mode_mapping_covers_supported_options():
    module = _load_module("cool_effects_text_overlay_modes_test", "nodes/video_generator.py")

    assert module._resolve_text_animation_mode("none") == 0
    assert module._resolve_text_animation_mode("fade_in") == 1
    assert module._resolve_text_animation_mode("fade_in_out") == 2
    assert module._resolve_text_animation_mode("slide_up") == 3
    assert module._resolve_text_animation_mode("typewriter") == 4
    assert module._resolve_text_animation_mode("unexpected") == 1


def test_text_overlay_shader_contains_animation_uniform_contract():
    shader_source = (REPO_ROOT / "shaders" / "glsl" / "text_overlay.frag").read_text(encoding="utf-8")

    assert "uniform float u_time;" in shader_source
    assert "uniform float u_duration;" in shader_source
    assert "uniform float u_animation_mode;" in shader_source
    assert "uniform float u_animation_duration;" in shader_source
    assert "float animation_alpha = 1.0;" in shader_source
    assert "if (animation_mode == 1.0)" in shader_source
    assert "if (animation_mode == 2.0)" in shader_source
    assert "if (animation_mode == 3.0)" in shader_source
    assert "(u_duration - u_time) / safe_animation_duration" in shader_source
