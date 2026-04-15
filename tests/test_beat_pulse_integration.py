import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

import torch

import nodes.video_generator as video_generator


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_entrypoint_module():
    module_path = REPO_ROOT / "__init__.py"
    module_spec = importlib.util.spec_from_file_location(
        "cool_effects_entrypoint_for_tests", module_path
    )
    if module_spec is None or module_spec.loader is None:
        raise ValueError(f"Missing module config at {module_path}")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


class _FakeVideo:
    def get_dimensions(self):
        return (0, 0)

    def save_to(self, _output_path):
        return None


class _FakeInputImpl:
    @staticmethod
    def VideoFromComponents(_components):
        return _FakeVideo()


class _FakeVideoComponents:
    def __init__(self, images, audio, frame_rate):
        self.images = images
        self.audio = audio
        self.frame_rate = frame_rate


class _FakeTypes:
    VideoComponents = _FakeVideoComponents


class TestBeatPulseIntegration(unittest.TestCase):
    def setUp(self):
        self._module_overrides = {
            "comfy_api": sys.modules.get("comfy_api"),
            "comfy_api.latest": sys.modules.get("comfy_api.latest"),
        }
        comfy_api_module = types.ModuleType("comfy_api")
        comfy_api_latest_module = types.ModuleType("comfy_api.latest")
        comfy_api_latest_module.InputImpl = _FakeInputImpl
        comfy_api_latest_module.Types = _FakeTypes
        comfy_api_module.latest = comfy_api_latest_module
        sys.modules["comfy_api"] = comfy_api_module
        sys.modules["comfy_api.latest"] = comfy_api_latest_module

    def tearDown(self):
        for module_name, module in self._module_overrides.items():
            if module is None:
                sys.modules.pop(module_name, None)
            else:
                sys.modules[module_name] = module

    def test_entrypoint_registers_beat_pulse_node(self):
        entrypoint = _load_entrypoint_module()
        self.assertIn("CoolBeatPulseEffect", entrypoint.NODE_CLASS_MAPPINGS)
        self.assertEqual(
            entrypoint.NODE_DISPLAY_NAME_MAPPINGS.get("CoolBeatPulseEffect"),
            "Cool Beat Pulse Effect",
        )

    def test_video_generator_uses_extract_audio_features_for_rendering(self):
        node = video_generator.CoolVideoGenerator()
        image = torch.zeros((1, 2, 2, 3), dtype=torch.float32)
        effect_params = {"effect_name": "beat_pulse", "params": {}}
        audio = {"samples": [0.0, 0.2, 0.4]}
        extracted_features = [{"beat": True, "rms": 0.8}]
        received_audio_features = []

        def fake_render_frames(_image, _effect_params, _fps, _duration, audio_features=None):
            received_audio_features.append(audio_features)
            return _image

        with (
            mock.patch.object(
                video_generator,
                "extract_audio_features",
                return_value=extracted_features,
            ) as extract_mock,
            mock.patch.object(
                video_generator,
                "_render_frames",
                side_effect=fake_render_frames,
            ),
            mock.patch.object(
                video_generator,
                "_save_video_preview_to_temp",
                return_value=[],
            ),
        ):
            result = node.execute(
                image=image,
                fps=1,
                duration=1.0,
                effect_count=1,
                audio=audio,
                effect_params_1=effect_params,
            )

        extract_mock.assert_called_once_with(audio, fps=1, duration=1.0)
        self.assertEqual(received_audio_features, [extracted_features])
        self.assertIn("result", result)
        self.assertIn("ui", result)

    def test_video_generator_sets_beat_uniforms_in_render_loop(self):
        source = (REPO_ROOT / "nodes" / "video_generator.py").read_text(encoding="utf-8")
        self.assertIn('program["u_beat"].value', source)
        self.assertIn('program["u_rms"].value', source)
        self.assertIn("extract_audio_features(audio, fps=fps, duration=duration)", source)


if __name__ == "__main__":
    unittest.main()
