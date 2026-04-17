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


def test_tone_mapping_node_inputs_match_user_story_contract():
    module = _load_module("cool_effects_tone_mapping_effect_inputs_test", "nodes/tone_mapping_effect.py")

    required_inputs = module.CoolToneMappingEffect.INPUT_TYPES()["required"]
    assert required_inputs["mode"] == (["none", "bw", "sepia", "duotone"], {"default": "none"})
    assert required_inputs["intensity"] == (
        "FLOAT",
        {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01},
    )
    assert required_inputs["shadow_r"] == (
        "FLOAT",
        {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01},
    )
    assert required_inputs["shadow_g"] == (
        "FLOAT",
        {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01},
    )
    assert required_inputs["shadow_b"] == (
        "FLOAT",
        {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01},
    )
    assert required_inputs["highlight_r"] == (
        "FLOAT",
        {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01},
    )
    assert required_inputs["highlight_g"] == (
        "FLOAT",
        {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01},
    )
    assert required_inputs["highlight_b"] == (
        "FLOAT",
        {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01},
    )


def test_tone_mapping_node_outputs_effect_params_payload():
    module = _load_module("cool_effects_tone_mapping_effect_execute_test", "nodes/tone_mapping_effect.py")
    node = module.CoolToneMappingEffect()

    (effect_params,) = node.execute(
        mode="duotone",
        intensity=0.65,
        shadow_r=0.05,
        shadow_g=0.1,
        shadow_b=0.2,
        highlight_r=0.9,
        highlight_g=0.8,
        highlight_b=0.7,
    )

    assert module.CoolToneMappingEffect.CATEGORY == "CoolEffects"
    assert module.CoolToneMappingEffect.RETURN_TYPES == ("EFFECT_PARAMS",)
    assert effect_params == {
        "effect_name": "tone_mapping",
        "params": {
            "u_mode": 3.0,
            "u_intensity": 0.65,
            "u_shadow_r": 0.05,
            "u_shadow_g": 0.1,
            "u_shadow_b": 0.2,
            "u_highlight_r": 0.9,
            "u_highlight_g": 0.8,
            "u_highlight_b": 0.7,
        },
    }


def test_tone_mapping_none_mode_is_identity_defaults():
    module = _load_module("cool_effects_tone_mapping_effect_defaults_test", "nodes/tone_mapping_effect.py")
    node = module.CoolToneMappingEffect()

    (effect_params,) = node.execute(
        mode="none",
        intensity=1.0,
        shadow_r=0.0,
        shadow_g=0.0,
        shadow_b=0.0,
        highlight_r=1.0,
        highlight_g=1.0,
        highlight_b=1.0,
    )

    assert effect_params["effect_name"] == "tone_mapping"
    assert effect_params["params"] == {
        "u_mode": 0.0,
        "u_intensity": 1.0,
        "u_shadow_r": 0.0,
        "u_shadow_g": 0.0,
        "u_shadow_b": 0.0,
        "u_highlight_r": 1.0,
        "u_highlight_g": 1.0,
        "u_highlight_b": 1.0,
    }


def test_tone_mapping_shader_declares_uniform_contract_and_identity_path():
    shader_source = (REPO_ROOT / "shaders" / "glsl" / "tone_mapping.frag").read_text(encoding="utf-8")

    assert "uniform sampler2D u_image;" in shader_source
    assert "uniform float u_time;" in shader_source
    assert "uniform vec2 u_resolution;" in shader_source
    assert "uniform float u_mode;" in shader_source
    assert "uniform float u_intensity;" in shader_source
    assert "uniform float u_shadow_r;" in shader_source
    assert "uniform float u_shadow_g;" in shader_source
    assert "uniform float u_shadow_b;" in shader_source
    assert "uniform float u_highlight_r;" in shader_source
    assert "uniform float u_highlight_g;" in shader_source
    assert "uniform float u_highlight_b;" in shader_source
    assert "vec3 target_color = source_rgb;" in shader_source
    assert "float intensity = clamp(u_intensity, 0.0, 1.0);" in shader_source
    assert "vec3 mapped_color = mix(source_rgb, target_color, intensity);" in shader_source


def test_tone_mapping_node_is_registered_in_package_mappings():
    package_module = _load_module("cool_effects_package_tone_mapping_registration_test", "__init__.py")

    assert (
        package_module.NODE_CLASS_MAPPINGS["CoolToneMappingEffect"]
        is package_module.CoolToneMappingEffect
    )
    assert (
        package_module.NODE_DISPLAY_NAME_MAPPINGS["CoolToneMappingEffect"]
        == "Cool Tone Mapping Effect"
    )


def test_tone_mapping_effect_params_are_consumed_by_video_generator_pipeline():
    video_generator_module = _load_module(
        "cool_effects_video_generator_tone_mapping_pipeline_test",
        "nodes/video_generator.py",
    )
    tone_mapping_module = _load_module(
        "cool_effects_tone_mapping_effect_pipeline_test",
        "nodes/tone_mapping_effect.py",
    )

    node = tone_mapping_module.CoolToneMappingEffect()
    (tone_mapping_params,) = node.execute(
        mode="sepia",
        intensity=0.5,
        shadow_r=0.0,
        shadow_g=0.0,
        shadow_b=0.0,
        highlight_r=1.0,
        highlight_g=1.0,
        highlight_b=1.0,
    )
    assert tone_mapping_params["effect_name"] == "tone_mapping"

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
            effect_params_1=tone_mapping_params,
        )
        generated_video = output["result"][0]

        assert captured_effect_names == ["tone_mapping"]
        assert generated_video.images.shape[0] == 12
        assert torch.mean(generated_video.images).item() > 0.0
    finally:
        sys.modules.pop("comfy_api.latest", None)
        sys.modules.pop("comfy_api", None)
