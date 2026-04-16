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


def test_fisheye_node_inputs_match_user_story_contract():
    module = _load_module("cool_effects_fisheye_effect_inputs_test", "nodes/fisheye_effect.py")

    required_inputs = module.CoolFisheyeEffect.INPUT_TYPES()["required"]
    assert required_inputs["strength"] == (
        "FLOAT",
        {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01},
    )
    assert required_inputs["zoom"] == (
        "FLOAT",
        {"default": 1.0, "min": 0.5, "max": 2.0, "step": 0.01},
    )


def test_fisheye_node_outputs_effect_params_payload():
    module = _load_module("cool_effects_fisheye_effect_execute_test", "nodes/fisheye_effect.py")
    node = module.CoolFisheyeEffect()

    (effect_params,) = node.execute(strength=0.72, zoom=1.35)

    assert module.CoolFisheyeEffect.CATEGORY == "CoolEffects"
    assert module.CoolFisheyeEffect.RETURN_TYPES == ("EFFECT_PARAMS",)
    assert effect_params == {
        "effect_name": "fisheye",
        "params": {
            "u_strength": 0.72,
            "u_zoom": 1.35,
        },
    }


def test_fisheye_shader_uses_polar_coordinate_uv_remapping():
    shader_source = (REPO_ROOT / "shaders" / "glsl" / "fisheye.frag").read_text(encoding="utf-8")

    assert "uniform sampler2D u_image;" in shader_source
    assert "uniform float u_time;" in shader_source
    assert "uniform vec2 u_resolution;" in shader_source
    assert "uniform float u_strength;" in shader_source
    assert "uniform float u_zoom;" in shader_source
    assert "length(centered_uv)" in shader_source
    assert "atan(centered_uv.y, centered_uv.x)" in shader_source
    assert "vec2(cos(theta), sin(theta))" in shader_source


def test_fisheye_node_is_registered_in_package_mappings():
    package_module = _load_module("cool_effects_package_fisheye_registration_test", "__init__.py")

    assert package_module.NODE_CLASS_MAPPINGS["CoolFisheyeEffect"] is package_module.CoolFisheyeEffect
    assert package_module.NODE_DISPLAY_NAME_MAPPINGS["CoolFisheyeEffect"] == "Cool Fisheye Effect"


def test_fisheye_effect_params_are_consumed_by_video_generator_pipeline():
    video_generator_module = _load_module(
        "cool_effects_video_generator_fisheye_pipeline_test",
        "nodes/video_generator.py",
    )
    fisheye_module = _load_module("cool_effects_fisheye_effect_pipeline_test", "nodes/fisheye_effect.py")

    node = fisheye_module.CoolFisheyeEffect()
    (fisheye_params,) = node.execute(strength=0.6, zoom=1.2)
    assert fisheye_params["effect_name"] == "fisheye"

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
            effect_params_1=fisheye_params,
        )
        generated_video = output["result"][0]

        assert captured_effect_names == ["fisheye"]
        assert generated_video.images.shape[0] == 12
        assert torch.mean(generated_video.images).item() > 0.0
    finally:
        sys.modules.pop("comfy_api.latest", None)
        sys.modules.pop("comfy_api", None)
