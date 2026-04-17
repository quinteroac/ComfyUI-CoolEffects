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


def test_curves_node_inputs_match_user_story_contract():
    module = _load_module("cool_effects_curves_effect_inputs_test", "nodes/curves_effect.py")

    required_inputs = module.CoolCurvesEffect.INPUT_TYPES()["required"]
    assert required_inputs["lift"] == (
        "FLOAT",
        {"default": 0.0, "min": 0.0, "max": 1.0, "step": 0.01},
    )
    assert required_inputs["gamma"] == (
        "FLOAT",
        {"default": 1.0, "min": 0.1, "max": 4.0, "step": 0.01},
    )
    assert required_inputs["gain"] == (
        "FLOAT",
        {"default": 1.0, "min": 0.0, "max": 4.0, "step": 0.01},
    )


def test_curves_node_outputs_effect_params_payload():
    module = _load_module("cool_effects_curves_effect_execute_test", "nodes/curves_effect.py")
    node = module.CoolCurvesEffect()

    (effect_params,) = node.execute(lift=0.25, gamma=1.6, gain=1.2)

    assert module.CoolCurvesEffect.CATEGORY == "CoolEffects"
    assert module.CoolCurvesEffect.RETURN_TYPES == ("EFFECT_PARAMS",)
    assert effect_params == {
        "effect_name": "curves",
        "params": {
            "u_lift": 0.25,
            "u_gamma": 1.6,
            "u_gain": 1.2,
        },
    }


def test_curves_node_default_effect_params_are_identity_values():
    module = _load_module("cool_effects_curves_effect_defaults_test", "nodes/curves_effect.py")
    node = module.CoolCurvesEffect()

    (effect_params,) = node.execute(lift=0.0, gamma=1.0, gain=1.0)

    assert effect_params["effect_name"] == "curves"
    assert effect_params["params"] == {
        "u_lift": 0.0,
        "u_gamma": 1.0,
        "u_gain": 1.0,
    }


def test_curves_shader_declares_uniform_contract_and_identity_path():
    shader_source = (REPO_ROOT / "shaders" / "glsl" / "curves.frag").read_text(encoding="utf-8")

    assert "uniform sampler2D u_image;" in shader_source
    assert "uniform float u_time;" in shader_source
    assert "uniform vec2 u_resolution;" in shader_source
    assert "uniform float u_lift;" in shader_source
    assert "uniform float u_gamma;" in shader_source
    assert "uniform float u_gain;" in shader_source
    assert "float lift = clamp(u_lift, 0.0, 1.0);" in shader_source
    assert "float gamma = clamp(u_gamma, 0.1, 4.0);" in shader_source
    assert "float gain = clamp(u_gain, 0.0, 4.0);" in shader_source
    assert "adjusted_color = pow(adjusted_color, vec3(1.0 / gamma));" in shader_source
    assert "adjusted_color *= vec3(gain);" in shader_source


def test_curves_node_is_registered_in_package_mappings():
    package_module = _load_module("cool_effects_package_curves_registration_test", "__init__.py")

    assert package_module.NODE_CLASS_MAPPINGS["CoolCurvesEffect"] is package_module.CoolCurvesEffect
    assert (
        package_module.NODE_DISPLAY_NAME_MAPPINGS["CoolCurvesEffect"]
        == "Cool Curves (Lift / Gamma / Gain) Effect"
    )


def test_curves_effect_params_are_consumed_by_video_generator_pipeline():
    video_generator_module = _load_module(
        "cool_effects_video_generator_curves_pipeline_test",
        "nodes/video_generator.py",
    )
    curves_module = _load_module("cool_effects_curves_effect_pipeline_test", "nodes/curves_effect.py")

    node = curves_module.CoolCurvesEffect()
    (curves_params,) = node.execute(lift=0.1, gamma=1.3, gain=1.1)
    assert curves_params["effect_name"] == "curves"

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
            effect_params_1=curves_params,
        )
        generated_video = output["result"][0]

        assert captured_effect_names == ["curves"]
        assert generated_video.images.shape[0] == 12
        assert torch.mean(generated_video.images).item() > 0.0
    finally:
        sys.modules.pop("comfy_api.latest", None)
        sys.modules.pop("comfy_api", None)
