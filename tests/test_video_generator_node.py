from __future__ import annotations

from dataclasses import dataclass
import importlib.util
from pathlib import Path
import sys
import types

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


@dataclass
class _FakeVideo:
    images: torch.Tensor
    audio: object
    frame_rate: object

    def save_to(self, output_path: str) -> None:
        Path(output_path).write_bytes(b"fake-mp4")

    def get_dimensions(self) -> tuple[int, int]:
        if self.images.ndim < 3:
            return (0, 0)
        return (int(self.images.shape[2]), int(self.images.shape[1]))


def _install_fake_comfy_api():
    comfy_api_module = types.ModuleType("comfy_api")
    latest_module = types.ModuleType("comfy_api.latest")

    class _FakeInputImpl:
        @staticmethod
        def VideoFromComponents(video_components):
            return _FakeVideo(
                images=video_components.images,
                audio=video_components.audio,
                frame_rate=video_components.frame_rate,
            )

    @dataclass
    class _FakeVideoComponents:
        images: torch.Tensor
        audio: object
        frame_rate: object

    class _FakeTypes:
        VideoComponents = _FakeVideoComponents

    latest_module.InputImpl = _FakeInputImpl
    latest_module.Types = _FakeTypes
    comfy_api_module.latest = latest_module
    sys.modules["comfy_api"] = comfy_api_module
    sys.modules["comfy_api.latest"] = latest_module


def _cleanup_fake_comfy_api():
    sys.modules.pop("comfy_api.latest", None)
    sys.modules.pop("comfy_api", None)


def test_effect_params_4_connects_and_renders_frames():
    _install_fake_comfy_api()
    try:
        video_generator_module = _load_module(
            "cool_effects_video_generator_slot4_test",
            "nodes/video_generator.py",
        )
        calls: list[str] = []

        def _fake_render_frames(image, effect_params, fps, duration, audio_features=None):
            calls.append(effect_params["effect_name"])
            return image

        video_generator_module._render_frames = _fake_render_frames
        video_generator_module.extract_audio_features = lambda audio, fps, duration: []

        input_image = torch.zeros((1, 4, 4, 3), dtype=torch.float32)
        node = video_generator_module.CoolVideoGenerator()
        output = node.execute(
            image=input_image,
            fps=24,
            duration=1.0,
            effect_count=4,
            effect_params_4={"effect_name": "zoom_out", "params": {}},
        )

        result_video = output["result"][0]
        assert isinstance(result_video, _FakeVideo)
        assert calls == ["zoom_out"]
    finally:
        _cleanup_fake_comfy_api()


def test_zoom_and_dolly_sequence_runs_without_exceptions():
    _install_fake_comfy_api()
    try:
        video_generator_module = _load_module(
            "cool_effects_video_generator_sequence_test",
            "nodes/video_generator.py",
        )
        calls: list[str] = []

        def _fake_render_frames(image, effect_params, fps, duration, audio_features=None):
            calls.append(effect_params["effect_name"])
            return image + 0.0

        video_generator_module._render_frames = _fake_render_frames
        video_generator_module.extract_audio_features = lambda audio, fps, duration: []

        input_image = torch.ones((1, 8, 8, 3), dtype=torch.float32) * 0.5
        node = video_generator_module.CoolVideoGenerator()
        output = node.execute(
            image=input_image,
            fps=30,
            duration=1.5,
            effect_count=2,
            effect_params_1={"effect_name": "zoom_in", "params": {}},
            effect_params_2={"effect_name": "dolly_out", "params": {}},
        )

        result_video = output["result"][0]
        assert isinstance(result_video, _FakeVideo)
        assert calls == ["zoom_in", "dolly_out"]
    finally:
        _cleanup_fake_comfy_api()


def test_video_generator_output_stays_compatible_with_video_player():
    _install_fake_comfy_api()
    try:
        video_generator_module = _load_module(
            "cool_effects_video_generator_player_compat_test",
            "nodes/video_generator.py",
        )
        video_player_module = _load_module(
            "cool_effects_video_player_compat_test",
            "nodes/video_player.py",
        )

        video_generator_module._render_frames = lambda image, effect_params, fps, duration, audio_features=None: (
            image
        )
        video_generator_module.extract_audio_features = lambda audio, fps, duration: []

        input_image = torch.zeros((1, 6, 6, 3), dtype=torch.float32)
        generator = video_generator_module.CoolVideoGenerator()
        generated = generator.execute(
            image=input_image,
            fps=12,
            duration=1.0,
            effect_count=1,
            effect_params_1={"effect_name": "dolly_in", "params": {}},
        )

        generated_video = generated["result"][0]
        player = video_player_module.CoolVideoPlayer()
        player_payload = player.execute(generated_video)

        assert isinstance(generated_video, _FakeVideo)
        assert "ui" in generated
        assert "video" in generated["ui"]
        assert isinstance(player_payload["ui"]["video"], list)
        assert len(player_payload["ui"]["video"]) >= 1
        assert "source_url" in player_payload["ui"]["video"][0]
    finally:
        _cleanup_fake_comfy_api()


def test_text_overlay_effect_params_workflow_renders_animated_video_frames():
    _install_fake_comfy_api()
    try:
        text_overlay_module = _load_module(
            "cool_effects_text_overlay_workflow_test",
            "nodes/text_overlay_effect.py",
        )
        video_generator_module = _load_module(
            "cool_effects_video_generator_text_overlay_workflow_test",
            "nodes/video_generator.py",
        )

        node = text_overlay_module.CoolTextOverlayEffect()
        (text_overlay_params,) = node.execute(
            text="Animated",
            font="dejavu_sans.ttf",
            font_size=48,
            color_r=1.0,
            color_g=1.0,
            color_b=1.0,
            opacity=1.0,
            position="bottom-center",
            offset_x=0.0,
            offset_y=0.0,
            animation="fade_in_out",
            animation_duration=0.5,
        )

        called_effect_names: list[str] = []

        def _fake_render_text_overlay_frames(image, effect_params, fps, duration):
            called_effect_names.append(effect_params["effect_name"])
            _, height, width, _ = image.shape
            frame_count = round(duration * fps)
            return torch.full((frame_count, height, width, 3), 0.8, dtype=torch.float32)

        video_generator_module._render_text_overlay_frames = _fake_render_text_overlay_frames
        video_generator_module.extract_audio_features = lambda audio, fps, duration: []

        input_image = torch.zeros((1, 8, 8, 3), dtype=torch.float32)
        generator = video_generator_module.CoolVideoGenerator()
        generated = generator.execute(
            image=input_image,
            fps=12,
            duration=1.0,
            effect_count=1,
            effect_params_1=text_overlay_params,
        )

        generated_video = generated["result"][0]
        assert isinstance(generated_video, _FakeVideo)
        assert called_effect_names == ["text_overlay"]
        assert generated_video.images.shape[0] == 12
        assert torch.mean(generated_video.images).item() > 0.0
    finally:
        _cleanup_fake_comfy_api()
