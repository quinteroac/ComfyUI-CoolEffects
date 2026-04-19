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


def test_pixelate_node_inputs_match_user_story_contract():
    module = _load_module("cool_effects_pixelate_effect_inputs_test", "nodes/pixelate_effect.py")

    required_inputs = module.CoolPixelateEffect.INPUT_TYPES()["required"]
    assert required_inputs["pixel_size"] == (
        "INT",
        {"default": 8, "min": 1, "max": 128, "step": 1},
    )
    assert required_inputs["aspect_ratio"] == (
        "FLOAT",
        {"default": 1.0, "min": 0.25, "max": 4.0, "step": 0.01},
    )


def test_pixelate_node_outputs_effect_params_payload():
    module = _load_module("cool_effects_pixelate_effect_execute_test", "nodes/pixelate_effect.py")
    node = module.CoolPixelateEffect()

    (effect_params,) = node.execute(pixel_size=32, aspect_ratio=2.0)

    assert module.CoolPixelateEffect.CATEGORY == "CoolEffects"
    assert module.CoolPixelateEffect.RETURN_TYPES == ("EFFECT_PARAMS",)
    assert effect_params == {
        "effect_name": "pixelate",
        "params": {
            "u_pixel_size": 32,
            "u_aspect_ratio": 2.0,
        },
    }


def test_pixelate_defaults_are_present_in_effect_params_registry():
    effect_params_module = _load_module(
        "cool_effects_pixelate_effect_defaults_test",
        "nodes/effect_params.py",
    )

    assert effect_params_module.DEFAULT_PARAMS["pixelate"] == {
        "u_pixel_size": 8.0,
        "u_aspect_ratio": 1.0,
    }


def test_pixelate_shader_declares_uniform_contract_and_block_sampling_logic():
    shader_source = (REPO_ROOT / "shaders" / "glsl" / "pixelate.frag").read_text(encoding="utf-8")

    assert "uniform sampler2D u_image;" in shader_source
    assert "uniform float u_time;" in shader_source
    assert "uniform vec2 u_resolution;" in shader_source
    assert "uniform float u_pixel_size;" in shader_source
    assert "uniform float u_aspect_ratio;" in shader_source
    assert "vec2 block_origin = floor(gl_FragCoord.xy / block_size) * block_size;" in shader_source
    assert "vec2 sample_coord = block_origin + 0.5 * block_size;" in shader_source
    assert "vec2 sample_uv = clamp(sample_coord / u_resolution, vec2(0.0), vec2(1.0));" in shader_source


def test_pixelate_node_is_registered_in_package_mappings():
    package_module = _load_module("cool_effects_package_pixelate_registration_test", "__init__.py")

    assert package_module.NODE_CLASS_MAPPINGS["CoolPixelateEffect"] is package_module.CoolPixelateEffect
    assert package_module.NODE_DISPLAY_NAME_MAPPINGS["CoolPixelateEffect"] == "Cool Pixelate Effect"


def test_pixelate_effect_params_are_consumed_by_video_generator_pipeline():
    video_generator_module = _load_module(
        "cool_effects_video_generator_pixelate_pipeline_test",
        "nodes/video_generator.py",
    )
    pixelate_module = _load_module("cool_effects_pixelate_effect_pipeline_test", "nodes/pixelate_effect.py")

    node = pixelate_module.CoolPixelateEffect()
    (pixelate_params,) = node.execute(pixel_size=1, aspect_ratio=1.0)
    assert pixelate_params["effect_name"] == "pixelate"

    captured_effect_names: list[str] = []
    captured_uniforms: list[dict] = []

    def _fake_render_frames(image, effect_params, fps, duration, audio_features=None):
        captured_effect_names.append(effect_params["effect_name"])
        captured_uniforms.append(effect_params["params"])
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
            effect_params_1=pixelate_params,
        )
        generated_video = output["result"][0]

        assert captured_effect_names == ["pixelate"]
        assert captured_uniforms == [{"u_pixel_size": 1, "u_aspect_ratio": 1.0}]
        assert generated_video.images.shape[0] == 12
        assert torch.mean(generated_video.images).item() > 0.0
    finally:
        sys.modules.pop("comfy_api.latest", None)
        sys.modules.pop("comfy_api", None)
