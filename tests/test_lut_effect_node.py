from pathlib import Path
import importlib.util
import sys
import types

import torch


REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_LUT_RELATIVE_PATH = "tests/fixtures/sample_lut.cube"
SAMPLE_LUT_ABSOLUTE_PATH = str((REPO_ROOT / SAMPLE_LUT_RELATIVE_PATH).resolve())


def _load_module(module_name: str, relative_path: str):
    module_path = REPO_ROOT / relative_path
    module_spec = importlib.util.spec_from_file_location(module_name, module_path)
    if module_spec is None or module_spec.loader is None:
        raise ValueError(f"Missing module config at {module_path}")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def test_lut_node_inputs_match_user_story_contract():
    module = _load_module("cool_effects_lut_effect_inputs_test", "nodes/lut_effect.py")

    required_inputs = module.CoolLUTEffect.INPUT_TYPES()["required"]
    assert required_inputs["lut_path"] == ("STRING", {"default": ""})
    assert required_inputs["intensity"] == (
        "FLOAT",
        {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01},
    )


def test_lut_node_outputs_effect_params_payload():
    module = _load_module("cool_effects_lut_effect_execute_test", "nodes/lut_effect.py")
    node = module.CoolLUTEffect()

    (effect_params,) = node.execute(
        lut_path=SAMPLE_LUT_RELATIVE_PATH,
        intensity=0.35,
    )

    assert module.CoolLUTEffect.CATEGORY == "CoolEffects"
    assert module.CoolLUTEffect.RETURN_TYPES == ("EFFECT_PARAMS",)
    assert effect_params == {
        "effect_name": "lut",
        "params": {
            "lut_path": SAMPLE_LUT_ABSOLUTE_PATH,
            "u_intensity": 0.35,
        },
    }


def test_lut_utils_parse_cube_file_and_strip_layout():
    module = _load_module("cool_effects_lut_utils_parse_test", "nodes/lut_utils.py")
    parsed_lut = module.parse_cube_lut_file(SAMPLE_LUT_RELATIVE_PATH)

    assert parsed_lut["resolved_path"] == SAMPLE_LUT_ABSOLUTE_PATH
    assert parsed_lut["size"] == 2
    assert parsed_lut["domain_min"] == (0.0, 0.0, 0.0)
    assert parsed_lut["domain_max"] == (1.0, 1.0, 1.0)
    assert len(parsed_lut["values"]) == 8
    assert len(parsed_lut["strip"]) == 2
    assert len(parsed_lut["strip"][0]) == 4
    assert parsed_lut["strip"][0][0] == [0.0, 0.0, 0.0]
    assert parsed_lut["strip"][1][3] == [1.0, 1.0, 1.0]


def test_lut_shader_declares_uniform_contract_and_intensity_mix():
    shader_source = (REPO_ROOT / "shaders" / "glsl" / "lut.frag").read_text(encoding="utf-8")

    assert "uniform sampler2D u_image;" in shader_source
    assert "uniform sampler2D u_lut_texture;" in shader_source
    assert "uniform float u_time;" in shader_source
    assert "uniform vec2 u_resolution;" in shader_source
    assert "uniform float u_lut_size;" in shader_source
    assert "uniform vec3 u_domain_min;" in shader_source
    assert "uniform vec3 u_domain_max;" in shader_source
    assert "uniform float u_intensity;" in shader_source
    assert "vec3 output_color = mix(source_rgb, lut_color, intensity);" in shader_source


def test_lut_node_is_registered_in_package_mappings():
    package_module = _load_module("cool_effects_package_lut_registration_test", "__init__.py")

    assert (
        package_module.NODE_CLASS_MAPPINGS["CoolLUTEffect"]
        is package_module.CoolLUTEffect
    )
    assert (
        package_module.NODE_DISPLAY_NAME_MAPPINGS["CoolLUTEffect"]
        == "Cool LUT Effect"
    )


def test_lut_effect_params_are_consumed_by_video_generator_pipeline():
    video_generator_module = _load_module(
        "cool_effects_video_generator_lut_pipeline_test",
        "nodes/video_generator.py",
    )
    lut_effect_module = _load_module(
        "cool_effects_lut_effect_pipeline_test",
        "nodes/lut_effect.py",
    )

    node = lut_effect_module.CoolLUTEffect()
    (lut_params,) = node.execute(
        lut_path=SAMPLE_LUT_RELATIVE_PATH,
        intensity=1.0,
    )
    assert lut_params["effect_name"] == "lut"

    captured_effect_names: list[str] = []

    def _fake_render_frames(image, effect_params, fps, duration, audio_features=None):
        captured_effect_names.append(effect_params["effect_name"])
        frame_count = round(duration * fps)
        source = image if image.ndim == 4 else image.unsqueeze(0)
        tiled = source[[i % source.shape[0] for i in range(frame_count)]]
        return torch.clamp(tiled + 0.1, 0.0, 1.0)

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
            effect_params_1=lut_params,
        )
        generated_video = output["result"][0]

        assert captured_effect_names == ["lut"]
        assert generated_video.images.shape[0] == 12
        assert torch.mean(generated_video.images).item() > 0.0
    finally:
        sys.modules.pop("comfy_api.latest", None)
        sys.modules.pop("comfy_api", None)


def test_video_generator_lut_texture_upload_path_is_wired():
    video_generator_source = (REPO_ROOT / "nodes" / "video_generator.py").read_text(encoding="utf-8")

    assert 'if effect_name == "lut":' in video_generator_source
    assert "parse_cube_lut_file(lut_path)" in video_generator_source
    assert 'program["u_lut_texture"].value = 1' in video_generator_source
