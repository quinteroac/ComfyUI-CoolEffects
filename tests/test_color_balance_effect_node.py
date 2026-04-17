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


def test_color_balance_node_inputs_match_user_story_contract():
    module = _load_module("cool_effects_color_balance_effect_inputs_test", "nodes/color_balance_effect.py")

    required_inputs = module.CoolColorBalanceEffect.INPUT_TYPES()["required"]
    expected_spec = ("FLOAT", {"default": 0.0, "min": -1.0, "max": 1.0, "step": 0.01})
    for input_name in (
        "shadows_r",
        "shadows_g",
        "shadows_b",
        "midtones_r",
        "midtones_g",
        "midtones_b",
        "highlights_r",
        "highlights_g",
        "highlights_b",
    ):
        assert required_inputs[input_name] == expected_spec


def test_color_balance_node_outputs_effect_params_payload():
    module = _load_module("cool_effects_color_balance_effect_execute_test", "nodes/color_balance_effect.py")
    node = module.CoolColorBalanceEffect()

    (effect_params,) = node.execute(
        shadows_r=-0.4,
        shadows_g=0.2,
        shadows_b=0.1,
        midtones_r=0.3,
        midtones_g=-0.2,
        midtones_b=0.5,
        highlights_r=0.6,
        highlights_g=0.1,
        highlights_b=-0.3,
    )

    assert module.CoolColorBalanceEffect.CATEGORY == "CoolEffects"
    assert module.CoolColorBalanceEffect.RETURN_TYPES == ("EFFECT_PARAMS",)
    assert effect_params == {
        "effect_name": "color_balance",
        "params": {
            "u_shadows_r": -0.4,
            "u_shadows_g": 0.2,
            "u_shadows_b": 0.1,
            "u_midtones_r": 0.3,
            "u_midtones_g": -0.2,
            "u_midtones_b": 0.5,
            "u_highlights_r": 0.6,
            "u_highlights_g": 0.1,
            "u_highlights_b": -0.3,
        },
    }


def test_color_balance_node_default_effect_params_are_identity_values():
    module = _load_module("cool_effects_color_balance_effect_defaults_test", "nodes/color_balance_effect.py")
    node = module.CoolColorBalanceEffect()

    (effect_params,) = node.execute(
        shadows_r=0.0,
        shadows_g=0.0,
        shadows_b=0.0,
        midtones_r=0.0,
        midtones_g=0.0,
        midtones_b=0.0,
        highlights_r=0.0,
        highlights_g=0.0,
        highlights_b=0.0,
    )

    assert effect_params["effect_name"] == "color_balance"
    assert effect_params["params"] == {
        "u_shadows_r": 0.0,
        "u_shadows_g": 0.0,
        "u_shadows_b": 0.0,
        "u_midtones_r": 0.0,
        "u_midtones_g": 0.0,
        "u_midtones_b": 0.0,
        "u_highlights_r": 0.0,
        "u_highlights_g": 0.0,
        "u_highlights_b": 0.0,
    }


def test_color_balance_shader_declares_uniform_contract_and_identity_path():
    shader_source = (REPO_ROOT / "shaders" / "glsl" / "color_balance.frag").read_text(encoding="utf-8")

    assert "uniform sampler2D u_image;" in shader_source
    assert "uniform float u_time;" in shader_source
    assert "uniform vec2 u_resolution;" in shader_source
    assert "uniform float u_shadows_r;" in shader_source
    assert "uniform float u_shadows_g;" in shader_source
    assert "uniform float u_shadows_b;" in shader_source
    assert "uniform float u_midtones_r;" in shader_source
    assert "uniform float u_midtones_g;" in shader_source
    assert "uniform float u_midtones_b;" in shader_source
    assert "uniform float u_highlights_r;" in shader_source
    assert "uniform float u_highlights_g;" in shader_source
    assert "uniform float u_highlights_b;" in shader_source
    assert "vec3 adjusted_color = source_color.rgb;" in shader_source
    assert "adjusted_color += shadows_tint * shadows_weight;" in shader_source
    assert "adjusted_color += midtones_tint * midtones_weight;" in shader_source
    assert "adjusted_color += highlights_tint * highlights_weight;" in shader_source


def test_color_balance_node_is_registered_in_package_mappings():
    package_module = _load_module("cool_effects_package_color_balance_registration_test", "__init__.py")

    assert (
        package_module.NODE_CLASS_MAPPINGS["CoolColorBalanceEffect"]
        is package_module.CoolColorBalanceEffect
    )
    assert (
        package_module.NODE_DISPLAY_NAME_MAPPINGS["CoolColorBalanceEffect"]
        == "Cool Color Balance Effect"
    )


def test_color_balance_effect_params_are_consumed_by_video_generator_pipeline():
    video_generator_module = _load_module(
        "cool_effects_video_generator_color_balance_pipeline_test",
        "nodes/video_generator.py",
    )
    color_balance_module = _load_module(
        "cool_effects_color_balance_effect_pipeline_test",
        "nodes/color_balance_effect.py",
    )

    node = color_balance_module.CoolColorBalanceEffect()
    (color_balance_params,) = node.execute(
        shadows_r=0.1,
        shadows_g=0.0,
        shadows_b=-0.1,
        midtones_r=0.0,
        midtones_g=0.2,
        midtones_b=0.0,
        highlights_r=-0.1,
        highlights_g=0.0,
        highlights_b=0.2,
    )
    assert color_balance_params["effect_name"] == "color_balance"

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
            effect_params_1=color_balance_params,
        )
        generated_video = output["result"][0]

        assert captured_effect_names == ["color_balance"]
        assert generated_video.images.shape[0] == 12
        assert torch.mean(generated_video.images).item() > 0.0
    finally:
        sys.modules.pop("comfy_api.latest", None)
        sys.modules.pop("comfy_api", None)
