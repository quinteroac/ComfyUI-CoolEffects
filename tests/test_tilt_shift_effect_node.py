from pathlib import Path
import importlib.util

import torch


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_module(module_name: str, relative_path: str):
    module_path = REPO_ROOT / relative_path
    module_spec = importlib.util.spec_from_file_location(module_name, module_path)
    if module_spec is None or module_spec.loader is None:
        raise ValueError(f"Missing module config at {module_path}")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def test_tilt_shift_node_inputs_match_user_story_contract():
    module = _load_module("cool_effects_tilt_shift_effect_inputs_test", "nodes/tilt_shift_effect.py")

    required_inputs = module.CoolTiltShiftEffect.INPUT_TYPES()["required"]
    assert required_inputs["focus_center"] == (
        "FLOAT",
        {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01},
    )
    assert required_inputs["focus_width"] == (
        "FLOAT",
        {"default": 0.2, "min": 0.0, "max": 1.0, "step": 0.01},
    )
    assert required_inputs["blur_strength"] == (
        "FLOAT",
        {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01},
    )
    assert required_inputs["angle"] == (
        "FLOAT",
        {"default": 0.0, "min": 0.0, "max": 360.0, "step": 1.0},
    )


def test_tilt_shift_node_outputs_effect_params_payload():
    module = _load_module("cool_effects_tilt_shift_effect_execute_test", "nodes/tilt_shift_effect.py")
    node = module.CoolTiltShiftEffect()

    (effect_params,) = node.execute(
        focus_center=0.46,
        focus_width=0.31,
        blur_strength=0.74,
        angle=25.0,
    )

    assert module.CoolTiltShiftEffect.CATEGORY == "CoolEffects"
    assert module.CoolTiltShiftEffect.RETURN_TYPES == ("EFFECT_PARAMS",)
    assert effect_params == {
        "effect_name": "tilt_shift",
        "params": {
            "u_focus_center": 0.46,
            "u_focus_width": 0.31,
            "u_blur_strength": 0.74,
            "u_angle": 25.0,
        },
    }


def test_tilt_shift_shader_uses_gaussian_blur_scaled_by_distance_from_focus_band():
    shader_source = (REPO_ROOT / "shaders" / "glsl" / "tilt_shift.frag").read_text(encoding="utf-8")

    assert "uniform sampler2D u_image;" in shader_source
    assert "uniform float u_time;" in shader_source
    assert "uniform vec2 u_resolution;" in shader_source
    assert "uniform float u_focus_center;" in shader_source
    assert "uniform float u_focus_width;" in shader_source
    assert "uniform float u_blur_strength;" in shader_source
    assert "uniform float u_angle;" in shader_source
    assert "float distance_from_focus_band = abs(rotated_uv.y - focus_center) - focus_half_width;" in shader_source
    assert "float blur_factor = clamp(outside_distance / max_outside_distance, 0.0, 1.0);" in shader_source
    assert "sample_axis_blur" in shader_source
    assert "vec3 gaussian_blur = 0.5 * (blur_x + blur_y);" in shader_source
    assert "float blur_radius_px = blur_strength * blur_factor * 12.0;" in shader_source


def test_tilt_shift_node_is_registered_in_package_mappings():
    package_module = _load_module("cool_effects_package_tilt_shift_registration_test", "__init__.py")

    assert package_module.NODE_CLASS_MAPPINGS["CoolTiltShiftEffect"] is package_module.CoolTiltShiftEffect
    assert package_module.NODE_DISPLAY_NAME_MAPPINGS["CoolTiltShiftEffect"] == "Cool Tilt-Shift Effect"


def test_tilt_shift_effect_params_are_consumed_by_video_generator_pipeline():
    video_generator_module = _load_module(
        "cool_effects_video_generator_tilt_shift_pipeline_test",
        "nodes/video_generator.py",
    )
    tilt_shift_module = _load_module("cool_effects_tilt_shift_effect_pipeline_test", "nodes/tilt_shift_effect.py")

    node = tilt_shift_module.CoolTiltShiftEffect()
    (tilt_shift_params,) = node.execute(
        focus_center=0.5,
        focus_width=0.2,
        blur_strength=0.5,
        angle=0.0,
    )
    assert tilt_shift_params["effect_name"] == "tilt_shift"

    captured_effect_names: list[str] = []

    def _fake_render_frames(image, effect_params, fps, duration, audio_features=None):
        captured_effect_names.append(effect_params["effect_name"])
        frame_count = round(duration * fps)
        source = image if image.ndim == 4 else image.unsqueeze(0)
        tiled = source[[i % source.shape[0] for i in range(frame_count)]]
        return torch.clamp(tiled + 0.15, 0.0, 1.0)

    class _FakeVideo:
        def __init__(self, images):
            self.images = images

        def save_to(self, output_path: str) -> None:
            Path(output_path).write_bytes(b"fake-mp4")

        def get_dimensions(self) -> tuple[int, int]:
            return int(self.images.shape[2]), int(self.images.shape[1])

    class _FakeInputImpl:
        @staticmethod
        def VideoFromComponents(video_components):
            return _FakeVideo(video_components.images)

    class _FakeVideoComponents:
        def __init__(self, images, audio, frame_rate):
            self.images = images
            self.audio = audio
            self.frame_rate = frame_rate

    class _FakeTypes:
        VideoComponents = _FakeVideoComponents

    video_generator_module._render_frames = _fake_render_frames
    video_generator_module.extract_audio_features = lambda audio, fps, duration: []
    video_generator_module.InputImpl = _FakeInputImpl
    video_generator_module.Types = _FakeTypes

    import sys
    import types

    comfy_api_module = types.ModuleType("comfy_api")
    latest_module = types.ModuleType("comfy_api.latest")
    latest_module.InputImpl = _FakeInputImpl
    latest_module.Types = _FakeTypes
    comfy_api_module.latest = latest_module
    sys.modules["comfy_api"] = comfy_api_module
    sys.modules["comfy_api.latest"] = latest_module

    try:
        generator = video_generator_module.CoolVideoGenerator()
        input_image = torch.zeros((1, 8, 8, 3), dtype=torch.float32)
        output = generator.execute(
            image=input_image,
            fps=12,
            duration=1.0,
            effect_count=1,
            effect_params_1=tilt_shift_params,
        )
        generated_video = output["result"][0]

        assert captured_effect_names == ["tilt_shift"]
        assert generated_video.images.shape[0] == 12
        assert torch.mean(generated_video.images).item() > 0.0
    finally:
        sys.modules.pop("comfy_api.latest", None)
        sys.modules.pop("comfy_api", None)
