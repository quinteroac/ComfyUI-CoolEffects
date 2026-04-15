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
    try:
        parsed_value = json.loads(text_value)
    except json.JSONDecodeError as error:
        raise ValueError(f"fragments must be valid JSON: {error.msg}") from error
    if not isinstance(parsed_value, list):
        raise ValueError("fragments must be a JSON array")
    return parsed_value


def _normalize_font_weight(font_weight, fallback_weight):
    if font_weight is None:
        return str(fallback_weight)
    normalized_value = str(font_weight).lower().strip()
    if normalized_value in {"normal", "bold"}:
        return normalized_value
    return str(fallback_weight)


def _resolve_color(color_value):
    rgb = ImageColor.getrgb(str(color_value))
    if len(rgb) < 3:
        raise ValueError("color must resolve to an RGB value")
    return (int(rgb[0]), int(rgb[1]), int(rgb[2]))


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


def _resolve_font_cached(font_cache, font_family, font_size, font_weight):
    cache_key = (str(font_family), int(font_size), str(font_weight))
    if cache_key not in font_cache:
        font_cache[cache_key] = _load_font_for_style(cache_key[0], cache_key[1], cache_key[2])
    return font_cache[cache_key]


def _measure_text(draw, text: str, font):
    left, _, right, _ = draw.textbbox((0, 0), text, font=font)
    return max(0.0, float(right - left))


def _resolve_text_origin(text_width, width, height, pos_x, pos_y, align):
    anchor_x = float(pos_x) * float(width)
    anchor_y = float(pos_y) * float(height)

    if align == "left":
        origin_x = anchor_x
    elif align == "right":
        origin_x = anchor_x - text_width
    else:
        origin_x = anchor_x - (text_width / 2.0)
    return origin_x, anchor_y


def _resolve_fragment_layout(draw, fragments, width, height, pos_x, pos_y, align):
    fragment_widths = []
    fragment_ascents = []
    for fragment in fragments:
        fragment_widths.append(_measure_text(draw, fragment["text"], fragment["font"]))
        try:
            ascent, _descent = fragment["font"].getmetrics()
        except AttributeError:
            _, top, _, _ = draw.textbbox((0, 0), fragment["text"], font=fragment["font"])
            ascent = -top
        fragment_ascents.append(float(ascent))

    line_width = float(sum(fragment_widths))
    origin_x, baseline_y = _resolve_text_origin(
        text_width=line_width,
        width=width,
        height=height,
        pos_x=pos_x,
        pos_y=pos_y,
        align=align,
    )
    return origin_x, baseline_y, fragment_widths, fragment_ascents


def _normalize_fragments(
    parsed_fragments,
    default_font_family,
    default_font_size,
    default_color,
    default_font_weight,
    font_cache=None,
):
    if font_cache is None:
        font_cache = {}
    normalized_fragments = []
    for fragment_index, fragment in enumerate(parsed_fragments):
        if not isinstance(fragment, dict):
            raise ValueError(f"fragments[{fragment_index}] must be an object")
        if "text" not in fragment:
            raise ValueError(f"fragments[{fragment_index}] is missing required key 'text'")

        fragment_text = str(fragment["text"])
        fragment_font_family = str(fragment.get("font_family", default_font_family))
        fragment_font_size = int(fragment.get("font_size", default_font_size))
        fragment_color = _resolve_color(fragment.get("color", default_color))
        fragment_font_weight = _normalize_font_weight(
            fragment.get("font_weight"),
            default_font_weight,
        )
        fragment_font = _resolve_font_cached(
            font_cache,
            fragment_font_family,
            fragment_font_size,
            fragment_font_weight,
        )
        normalized_fragments.append(
            {
                "text": fragment_text,
                "font": fragment_font,
                "color": fragment_color,
            }
        )
    return normalized_fragments


def _apply_text_overlay(frame, fragments, pos_x, pos_y, align, opacity):
    frame_cpu = frame.detach().cpu().clamp(0.0, 1.0)
    frame_uint8 = (frame_cpu.numpy() * 255.0).astype(np.uint8)
    base_image = Image.fromarray(frame_uint8, mode="RGB").convert("RGBA")
    text_layer = Image.new("RGBA", base_image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_layer)

    origin_x, baseline_y, fragment_widths, fragment_ascents = _resolve_fragment_layout(
        draw=draw,
        fragments=fragments,
        width=base_image.size[0],
        height=base_image.size[1],
        pos_x=pos_x,
        pos_y=pos_y,
        align=align,
    )

    cursor_x = origin_x
    for fragment, fragment_width, fragment_ascent in zip(
        fragments,
        fragment_widths,
        fragment_ascents,
    ):
        draw.text(
            (cursor_x, baseline_y - fragment_ascent),
            fragment["text"],
            font=fragment["font"],
            fill=(*fragment["color"], 255),
        )
        cursor_x += fragment_width

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
        default_color = _resolve_color(color)
        font_cache = {}
        if parsed_fragments:
            render_fragments = _normalize_fragments(
                parsed_fragments=parsed_fragments,
                default_font_family=font_family,
                default_font_size=font_size,
                default_color=color,
                default_font_weight=font_weight,
                font_cache=font_cache,
            )
        else:
            render_fragments = [
                {
                    "text": str(text),
                    "font": _resolve_font_cached(font_cache, font_family, font_size, font_weight),
                    "color": default_color,
                }
            ]

        rendered_frames = []
        for frame in video_images:
            rendered_frames.append(
                _apply_text_overlay(
                    frame=frame,
                    fragments=render_fragments,
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
