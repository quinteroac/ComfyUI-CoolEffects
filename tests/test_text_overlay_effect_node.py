import importlib.util
import sys
import types
import uuid
from fractions import Fraction
from pathlib import Path

import pytest
from PIL import ImageFont

torch = pytest.importorskip("torch")


PACKAGE_ROOT = Path(__file__).resolve().parent.parent
NODE_PATH = PACKAGE_ROOT / "nodes" / "text_overlay_effect.py"
PACKAGE_INIT = PACKAGE_ROOT / "__init__.py"


def _load_module(module_path: Path):
    module_name = f"cool_effects_test_text_overlay_module_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _mock_comfy_api(monkeypatch):
    class _FakeVideoComponents:
        def __init__(self, images, audio, frame_rate):
            self.images = images
            self.audio = audio
            self.frame_rate = frame_rate

    class _FakeInputImpl:
        @staticmethod
        def VideoFromComponents(vc):
            return vc

    class _FakeTypes:
        VideoComponents = _FakeVideoComponents

    fake_latest = types.ModuleType("comfy_api.latest")
    fake_latest.InputImpl = _FakeInputImpl
    fake_latest.Types = _FakeTypes

    monkeypatch.setitem(sys.modules, "comfy_api", types.ModuleType("comfy_api"))
    monkeypatch.setitem(sys.modules, "comfy_api.latest", fake_latest)


class _FakeVideo:
    def __init__(self, images, frame_rate=Fraction(24, 1), audio=None):
        self.images = images
        self.frame_rate = frame_rate
        self.audio = audio


def _changed_pixels(output_images, input_images):
    diff = (output_images - input_images).abs().sum(dim=-1)
    return (diff > 0.001).nonzero(as_tuple=False)


def test_text_overlay_input_types_expose_required_controls():
    module = _load_module(NODE_PATH)
    input_types = module.CoolTextOverlay.INPUT_TYPES()
    required = input_types["required"]
    optional = input_types["optional"]

    assert required["video"] == ("VIDEO",)
    assert required["text"] == ("STRING", {"default": "Cool Text"})
    assert required["font_family"] == ("STRING", {"default": "arial"})
    assert required["font_size"] == ("INT", {"default": 48, "min": 24, "max": 256})
    assert required["color"] == ("STRING", {"default": "#ffffff"})
    assert required["font_weight"] == (["normal", "bold"], {"default": "normal"})
    assert required["pos_x"] == (
        "FLOAT",
        {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01},
    )
    assert required["pos_y"] == (
        "FLOAT",
        {"default": 0.1, "min": 0.0, "max": 1.0, "step": 0.01},
    )
    assert required["align"] == (["left", "center", "right"], {"default": "center"})
    assert required["opacity"] == (
        "FLOAT",
        {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01},
    )
    assert optional["fragments"] == ("STRING", {"default": "[]"})


def test_text_overlay_returns_video_with_preserved_shape_fps_and_audio(monkeypatch):
    module = _load_module(NODE_PATH)
    _mock_comfy_api(monkeypatch)
    monkeypatch.setattr(module, "_load_font_for_style", lambda *_args: ImageFont.load_default())
    node = module.CoolTextOverlay()

    input_images = torch.zeros((3, 24, 40, 3), dtype=torch.float32)
    source_video = _FakeVideo(input_images.clone(), frame_rate=Fraction(30000, 1001), audio="track")
    output_video, = node.execute(
        video=source_video,
        text="TITLE",
        font_family="arial",
        font_size=48,
        color="#ffffff",
        font_weight="normal",
        pos_x=0.5,
        pos_y=0.1,
        align="center",
        opacity=1.0,
    )

    assert output_video.images.shape == input_images.shape
    assert output_video.frame_rate == source_video.frame_rate
    assert output_video.audio == source_video.audio


def test_text_overlay_text_widget_is_used_when_fragments_are_empty(monkeypatch):
    module = _load_module(NODE_PATH)
    _mock_comfy_api(monkeypatch)
    monkeypatch.setattr(module, "_load_font_for_style", lambda *_args: ImageFont.load_default())
    node = module.CoolTextOverlay()

    input_images = torch.zeros((1, 24, 40, 3), dtype=torch.float32)
    source_video = _FakeVideo(input_images.clone())

    output_video, = node.execute(
        video=source_video,
        text="HELLO",
        font_family="arial",
        font_size=48,
        color="#ffffff",
        font_weight="normal",
        pos_x=0.5,
        pos_y=0.1,
        align="center",
        opacity=1.0,
        fragments="[]",
    )

    changed = _changed_pixels(output_video.images, input_images)
    assert changed.numel() > 0


def test_text_overlay_pos_x_and_pos_y_move_overlay_anchor(monkeypatch):
    module = _load_module(NODE_PATH)
    _mock_comfy_api(monkeypatch)
    monkeypatch.setattr(module, "_load_font_for_style", lambda *_args: ImageFont.load_default())
    node = module.CoolTextOverlay()
    source_video = _FakeVideo(torch.zeros((1, 80, 120, 3), dtype=torch.float32))

    left_top_video, = node.execute(
        video=source_video,
        text="ANCHOR",
        font_family="arial",
        font_size=48,
        color="#ffffff",
        font_weight="normal",
        pos_x=0.2,
        pos_y=0.2,
        align="center",
        opacity=1.0,
    )
    right_bottom_video, = node.execute(
        video=source_video,
        text="ANCHOR",
        font_family="arial",
        font_size=48,
        color="#ffffff",
        font_weight="normal",
        pos_x=0.8,
        pos_y=0.8,
        align="center",
        opacity=1.0,
    )

    left_top_changed = _changed_pixels(left_top_video.images, source_video.images)
    right_bottom_changed = _changed_pixels(right_bottom_video.images, source_video.images)
    assert float(right_bottom_changed[:, 2].float().mean()) > float(left_top_changed[:, 2].float().mean())
    assert float(right_bottom_changed[:, 1].float().mean()) > float(left_top_changed[:, 1].float().mean())


def test_text_overlay_align_controls_horizontal_anchor(monkeypatch):
    module = _load_module(NODE_PATH)
    _mock_comfy_api(monkeypatch)
    monkeypatch.setattr(module, "_load_font_for_style", lambda *_args: ImageFont.load_default())
    node = module.CoolTextOverlay()
    source_video = _FakeVideo(torch.zeros((1, 50, 160, 3), dtype=torch.float32))

    right_video, = node.execute(
        video=source_video,
        text="ALIGNMENT",
        font_family="arial",
        font_size=48,
        color="#ffffff",
        font_weight="normal",
        pos_x=0.5,
        pos_y=0.2,
        align="right",
        opacity=1.0,
    )
    center_video, = node.execute(
        video=source_video,
        text="ALIGNMENT",
        font_family="arial",
        font_size=48,
        color="#ffffff",
        font_weight="normal",
        pos_x=0.5,
        pos_y=0.2,
        align="center",
        opacity=1.0,
    )
    left_video, = node.execute(
        video=source_video,
        text="ALIGNMENT",
        font_family="arial",
        font_size=48,
        color="#ffffff",
        font_weight="normal",
        pos_x=0.5,
        pos_y=0.2,
        align="left",
        opacity=1.0,
    )

    right_x = float(_changed_pixels(right_video.images, source_video.images)[:, 2].float().mean())
    center_x = float(_changed_pixels(center_video.images, source_video.images)[:, 2].float().mean())
    left_x = float(_changed_pixels(left_video.images, source_video.images)[:, 2].float().mean())
    assert right_x < center_x < left_x


def test_text_overlay_opacity_blends_into_frame(monkeypatch):
    module = _load_module(NODE_PATH)
    _mock_comfy_api(monkeypatch)
    monkeypatch.setattr(module, "_load_font_for_style", lambda *_args: ImageFont.load_default())
    node = module.CoolTextOverlay()

    input_images = torch.zeros((1, 24, 80, 3), dtype=torch.float32)
    source_video = _FakeVideo(input_images.clone())

    high_opacity_video, = node.execute(
        video=source_video,
        text="OPAQUE",
        font_family="arial",
        font_size=48,
        color="#ffffff",
        font_weight="normal",
        pos_x=0.5,
        pos_y=0.1,
        align="center",
        opacity=1.0,
    )
    low_opacity_video, = node.execute(
        video=source_video,
        text="OPAQUE",
        font_family="arial",
        font_size=48,
        color="#ffffff",
        font_weight="normal",
        pos_x=0.5,
        pos_y=0.1,
        align="center",
        opacity=0.2,
    )

    full_delta = float((high_opacity_video.images - input_images).abs().sum())
    low_delta = float((low_opacity_video.images - input_images).abs().sum())
    assert full_delta > low_delta
    assert low_delta > 0.0


def test_text_overlay_renders_text_on_all_frames_for_three_frame_video(monkeypatch):
    module = _load_module(NODE_PATH)
    _mock_comfy_api(monkeypatch)
    monkeypatch.setattr(module, "_load_font_for_style", lambda *_args: ImageFont.load_default())
    node = module.CoolTextOverlay()

    input_images = torch.zeros((3, 60, 100, 3), dtype=torch.float32)
    source_video = _FakeVideo(input_images.clone(), frame_rate=Fraction(15, 1))
    output_video, = node.execute(
        video=source_video,
        text="THREE",
        font_family="arial",
        font_size=48,
        color="#ffffff",
        font_weight="normal",
        pos_x=0.5,
        pos_y=0.3,
        align="center",
        opacity=1.0,
    )

    for frame_index in range(3):
        frame_diff = (output_video.images[frame_index] - input_images[frame_index]).abs().sum(dim=-1)
        changed = (frame_diff > 0.001).nonzero(as_tuple=False)
        assert changed.numel() > 0
        centroid_x = float(changed[:, 1].float().mean())
        centroid_y = float(changed[:, 0].float().mean())
        assert abs(centroid_x - (0.5 * 100.0)) < 20.0
        assert abs(centroid_y - (0.3 * 60.0)) < 20.0


def test_package_registers_cool_text_overlay_node():
    package_module = _load_module(PACKAGE_INIT)
    assert "CoolTextOverlay" in package_module.NODE_CLASS_MAPPINGS
    assert package_module.NODE_DISPLAY_NAME_MAPPINGS["CoolTextOverlay"] == "Cool Text Overlay"
