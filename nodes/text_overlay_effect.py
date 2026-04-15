"""ComfyUI text overlay node for VIDEO payloads."""

from __future__ import annotations

import json
import logging

import numpy as np
import torch
from PIL import Image, ImageColor, ImageDraw, ImageFont


LOGGER = logging.getLogger(__name__)


def _read_video_value(entry, key: str, default=None):
    if isinstance(entry, dict):
        return entry.get(key, default)
    return getattr(entry, key, default)


def _extract_video_components(video):
    images = _read_video_value(video, "images")
    if images is None:
        raise ValueError("VIDEO input must provide frame images")
    if not isinstance(images, torch.Tensor):
        raise ValueError("VIDEO images must be a torch.Tensor")

    if images.ndim == 3:
        images = images.unsqueeze(0)
    if images.ndim != 4 or images.shape[-1] != 3:
        raise ValueError("VIDEO images tensor must have shape [N, H, W, 3]")

    frame_rate = _read_video_value(video, "frame_rate")
    audio = _read_video_value(video, "audio")
    return images, frame_rate, audio


def _parse_fragments(fragments):
    if fragments is None:
        return []
    text_value = str(fragments).strip()
    if not text_value:
        return []
    parsed_value = json.loads(text_value)
    if not isinstance(parsed_value, list):
        raise ValueError("fragments must be a JSON array")
    return parsed_value


def _load_font_for_style(font_family, font_size, font_weight):
    font_candidates = [str(font_family)]
    if not str(font_family).lower().endswith(".ttf"):
        font_candidates.append(f"{font_family}.ttf")
    if font_weight == "bold":
        font_candidates = (
            [f"{font_family}-Bold.ttf", f"{font_family} Bold.ttf"] + font_candidates
        )

    for candidate in font_candidates:
        try:
            return ImageFont.truetype(candidate, size=int(font_size))
        except OSError:
            continue

    LOGGER.warning(
        "[CoolTextOverlay] failed to resolve font '%s' (%s), using Pillow default",
        font_family,
        font_weight,
    )
    return ImageFont.load_default()


def _measure_text(draw, text: str, font):
    left, _, right, _ = draw.textbbox((0, 0), text, font=font)
    return max(0.0, float(right - left))


def _resolve_text_origin(draw, text, font, width, height, pos_x, pos_y, align):
    text_width = _measure_text(draw, text, font)
    anchor_x = float(pos_x) * float(width)
    anchor_y = float(pos_y) * float(height)

    if align == "left":
        origin_x = anchor_x
    elif align == "right":
        origin_x = anchor_x - text_width
    else:
        origin_x = anchor_x - (text_width / 2.0)
    return origin_x, anchor_y


def _apply_text_overlay(frame, text, font, color, pos_x, pos_y, align, opacity):
    frame_cpu = frame.detach().cpu().clamp(0.0, 1.0)
    frame_uint8 = (frame_cpu.numpy() * 255.0).astype(np.uint8)
    base_image = Image.fromarray(frame_uint8, mode="RGB").convert("RGBA")
    text_layer = Image.new("RGBA", base_image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_layer)

    draw_position = _resolve_text_origin(
        draw=draw,
        text=text,
        font=font,
        width=base_image.size[0],
        height=base_image.size[1],
        pos_x=pos_x,
        pos_y=pos_y,
        align=align,
    )
    draw.text(draw_position, text, font=font, fill=(*color, 255))

    alpha_mask = text_layer.split()[-1].point(lambda alpha: int(alpha * float(opacity)))
    base_image.paste(text_layer, (0, 0), alpha_mask)

    output_rgb = np.asarray(base_image.convert("RGB"), dtype=np.float32) / np.float32(255.0)
    return torch.from_numpy(output_rgb)


class CoolTextOverlay:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "video": ("VIDEO",),
                "text": ("STRING", {"default": "Cool Text"}),
                "font_family": ("STRING", {"default": "arial"}),
                "font_size": ("INT", {"default": 48, "min": 24, "max": 256}),
                "color": ("STRING", {"default": "#ffffff"}),
                "font_weight": (["normal", "bold"], {"default": "normal"}),
                "pos_x": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
                "pos_y": ("FLOAT", {"default": 0.1, "min": 0.0, "max": 1.0, "step": 0.01}),
                "align": (["left", "center", "right"], {"default": "center"}),
                "opacity": ("FLOAT", {"default": 1.0, "min": 0.0, "max": 1.0, "step": 0.01}),
            },
            "optional": {
                "fragments": ("STRING", {"default": "[]"}),
            },
        }

    RETURN_TYPES = ("VIDEO",)
    RETURN_NAMES = ("video",)
    FUNCTION = "execute"
    CATEGORY = "CoolEffects"

    def execute(
        self,
        video,
        text,
        font_family,
        font_size,
        color,
        font_weight,
        pos_x,
        pos_y,
        align,
        opacity,
        fragments="[]",
    ):
        from comfy_api.latest import InputImpl, Types  # type: ignore

        video_images, frame_rate, audio = _extract_video_components(video)
        parsed_fragments = _parse_fragments(fragments)
        render_text = text
        if parsed_fragments:
            first_fragment = parsed_fragments[0]
            if isinstance(first_fragment, dict):
                render_text = str(first_fragment.get("text", text))
            else:
                render_text = str(first_fragment)
        render_text = str(render_text)

        font = _load_font_for_style(font_family, font_size, font_weight)
        rgb = ImageColor.getrgb(str(color))
        if len(rgb) < 3:
            raise ValueError("color must resolve to an RGB value")
        render_color = (int(rgb[0]), int(rgb[1]), int(rgb[2]))

        rendered_frames = []
        for frame in video_images:
            rendered_frames.append(
                _apply_text_overlay(
                    frame=frame,
                    text=render_text,
                    font=font,
                    color=render_color,
                    pos_x=pos_x,
                    pos_y=pos_y,
                    align=align,
                    opacity=opacity,
                )
            )

        output_images = torch.stack(rendered_frames, dim=0)
        output_video = InputImpl.VideoFromComponents(
            Types.VideoComponents(images=output_images, audio=audio, frame_rate=frame_rate)
        )
        return (output_video,)
