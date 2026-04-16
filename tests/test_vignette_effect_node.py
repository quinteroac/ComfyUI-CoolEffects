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


def test_vignette_node_inputs_match_user_story_contract():
    module = _load_module("cool_effects_vignette_effect_inputs_test", "nodes/vignette_effect.py")

    required_inputs = module.CoolVignetteEffect.INPUT_TYPES()["required"]
    assert required_inputs["strength"] == (
        "FLOAT",
        {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01},
    )
    assert required_inputs["radius"] == (
        "FLOAT",
        {"default": 0.75, "min": 0.1, "max": 1.5, "step": 0.01},
    )
    assert required_inputs["softness"] == (
        "FLOAT",
        {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01},
    )


def test_vignette_node_outputs_effect_params_payload():
    module = _load_module("cool_effects_vignette_effect_execute_test", "nodes/vignette_effect.py")
    node = module.CoolVignetteEffect()

    (effect_params,) = node.execute(strength=0.78, radius=0.63, softness=0.41)

    assert module.CoolVignetteEffect.CATEGORY == "CoolEffects"
    assert module.CoolVignetteEffect.RETURN_TYPES == ("EFFECT_PARAMS",)
    assert effect_params == {
        "effect_name": "vignette",
        "params": {
            "u_strength": 0.78,
            "u_radius": 0.63,
            "u_softness": 0.41,
        },
    }


def test_vignette_shader_uses_radial_distance_with_smooth_falloff():
    shader_source = (REPO_ROOT / "shaders" / "glsl" / "vignette.frag").read_text(
        encoding="utf-8"
    )

    assert "uniform sampler2D u_image;" in shader_source
    assert "uniform float u_time;" in shader_source
    assert "uniform vec2 u_resolution;" in shader_source
    assert "uniform float u_strength;" in shader_source
    assert "uniform float u_radius;" in shader_source
    assert "uniform float u_softness;" in shader_source
    assert "distance(uv, vec2(0.5, 0.5))" in shader_source
    assert "smoothstep(radius, soft_edge, radial_distance)" in shader_source
    assert "source_color * (1.0 - strength * vignette_factor)" in shader_source


def test_vignette_node_is_registered_in_package_mappings():
    package_module = _load_module("cool_effects_package_vignette_registration_test", "__init__.py")

    assert package_module.NODE_CLASS_MAPPINGS["CoolVignetteEffect"] is package_module.CoolVignetteEffect
    assert package_module.NODE_DISPLAY_NAME_MAPPINGS["CoolVignetteEffect"] == "Cool Vignette Effect"


def test_vignette_effect_params_are_consumed_by_video_generator_pipeline():
    video_generator_module = _load_module(
        "cool_effects_video_generator_vignette_pipeline_test",
        "nodes/video_generator.py",
    )
    vignette_module = _load_module("cool_effects_vignette_effect_pipeline_test", "nodes/vignette_effect.py")

    node = vignette_module.CoolVignetteEffect()
    (vignette_params,) = node.execute(strength=0.7, radius=0.8, softness=0.4)
    assert vignette_params["effect_name"] == "vignette"

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
            effect_params_1=vignette_params,
        )
        generated_video = output["result"][0]

        assert captured_effect_names == ["vignette"]
        assert generated_video.images.shape[0] == 12
        assert torch.mean(generated_video.images).item() > 0.0
    finally:
        sys.modules.pop("comfy_api.latest", None)
        sys.modules.pop("comfy_api", None)
