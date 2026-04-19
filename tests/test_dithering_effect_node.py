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


def test_dithering_node_inputs_match_user_story_contract():
    module = _load_module("cool_effects_dithering_effect_inputs_test", "nodes/dithering_effect.py")

    required_inputs = module.CoolDitheringEffect.INPUT_TYPES()["required"]
    assert required_inputs["dither_scale"] == (
        "FLOAT",
        {"default": 1.0, "min": 0.5, "max": 8.0, "step": 0.01},
    )
    assert required_inputs["threshold"] == (
        "FLOAT",
        {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01},
    )
    assert required_inputs["palette_size"] == (
        "INT",
        {"default": 2, "min": 2, "max": 16, "step": 1},
    )


def test_dithering_node_outputs_effect_params_payload():
    module = _load_module("cool_effects_dithering_effect_execute_test", "nodes/dithering_effect.py")
    node = module.CoolDitheringEffect()

    (effect_params,) = node.execute(dither_scale=2.5, threshold=0.62, palette_size=4)

    assert module.CoolDitheringEffect.CATEGORY == "CoolEffects"
    assert module.CoolDitheringEffect.RETURN_TYPES == ("EFFECT_PARAMS",)
    assert effect_params == {
        "effect_name": "dithering",
        "params": {
            "u_dither_scale": 2.5,
            "u_threshold": 0.62,
            "u_palette_size": 4,
        },
    }


def test_dithering_defaults_are_present_in_effect_params_registry():
    effect_params_module = _load_module(
        "cool_effects_dithering_effect_defaults_test",
        "nodes/effect_params.py",
    )

    assert effect_params_module.DEFAULT_PARAMS["dithering"] == {
        "u_dither_scale": 1.0,
        "u_threshold": 0.5,
        "u_palette_size": 2.0,
    }


def test_dithering_shader_declares_uniform_contract_and_bayer_matrix_logic():
    shader_source = (REPO_ROOT / "shaders" / "glsl" / "dithering.frag").read_text(encoding="utf-8")

    assert "uniform sampler2D u_image;" in shader_source
    assert "uniform float u_time;" in shader_source
    assert "uniform vec2 u_resolution;" in shader_source
    assert "uniform float u_dither_scale;" in shader_source
    assert "uniform float u_threshold;" in shader_source
    assert "uniform float u_palette_size;" in shader_source
    assert "const float BAYER_8X8[64] = float[](" in shader_source
    assert "ivec2 matrix_coord = ivec2(mod(floor(gl_FragCoord.xy / safe_scale), 8.0));" in shader_source
    assert "float dither_offset = (bayer_value - 0.5) / palette_steps;" in shader_source


def test_dithering_node_is_registered_in_package_mappings():
    package_module = _load_module("cool_effects_package_dithering_registration_test", "__init__.py")

    assert package_module.NODE_CLASS_MAPPINGS["CoolDitheringEffect"] is package_module.CoolDitheringEffect
    assert package_module.NODE_DISPLAY_NAME_MAPPINGS["CoolDitheringEffect"] == "Cool Dithering Effect"


def test_dithering_effect_params_are_consumed_by_video_generator_pipeline():
    video_generator_module = _load_module(
        "cool_effects_video_generator_dithering_pipeline_test",
        "nodes/video_generator.py",
    )
    dithering_module = _load_module(
        "cool_effects_dithering_effect_pipeline_test",
        "nodes/dithering_effect.py",
    )

    node = dithering_module.CoolDitheringEffect()
    (dithering_params,) = node.execute(dither_scale=0.75, threshold=0.5, palette_size=2)
    assert dithering_params["effect_name"] == "dithering"

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
            effect_params_1=dithering_params,
        )
        generated_video = output["result"][0]

        assert captured_effect_names == ["dithering"]
        assert captured_uniforms == [
            {"u_dither_scale": 0.75, "u_threshold": 0.5, "u_palette_size": 2}
        ]
        assert generated_video.images.shape[0] == 12
        assert torch.mean(generated_video.images).item() > 0.0
    finally:
        sys.modules.pop("comfy_api.latest", None)
        sys.modules.pop("comfy_api", None)
