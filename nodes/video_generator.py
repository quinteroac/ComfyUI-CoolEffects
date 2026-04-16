"""ComfyUI Cool Video Generator node.

Unified node that combines:
- Frame rendering via GLSL shaders (moderngl/EGL)
- VIDEO assembly via ComfyUI's CreateVideo logic
- Canvas preview widget (same as CoolVideoPlayer)
"""

from __future__ import annotations

import importlib.util
import logging
import os
import tempfile
import uuid
from fractions import Fraction
from pathlib import Path
from urllib.parse import quote

import numpy as np
import torch


LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shader loader bootstrap
# ---------------------------------------------------------------------------

_LOADER_PATH = Path(__file__).resolve().parent.parent / "shaders" / "loader.py"
_LOADER_SPEC = importlib.util.spec_from_file_location(
    "cool_effects_shader_loader_for_video_generator", _LOADER_PATH
)
if _LOADER_SPEC is None or _LOADER_SPEC.loader is None:
    raise ValueError(f"Missing shader loader config at {_LOADER_PATH}")
_shader_loader_module = importlib.util.module_from_spec(_LOADER_SPEC)
_LOADER_SPEC.loader.exec_module(_shader_loader_module)
load_shader = _shader_loader_module.load_shader
load_vertex_shader = _shader_loader_module.load_vertex_shader

# ---------------------------------------------------------------------------
# Effect params bootstrap
# ---------------------------------------------------------------------------

_EFFECT_PARAMS_PATH = Path(__file__).resolve().parent / "effect_params.py"
_EFFECT_PARAMS_SPEC = importlib.util.spec_from_file_location(
    "cool_effects_effect_params_for_video_generator", _EFFECT_PARAMS_PATH
)
if _EFFECT_PARAMS_SPEC is None or _EFFECT_PARAMS_SPEC.loader is None:
    raise ValueError(f"Missing effect params config at {_EFFECT_PARAMS_PATH}")
_effect_params_module = importlib.util.module_from_spec(_EFFECT_PARAMS_SPEC)
_EFFECT_PARAMS_SPEC.loader.exec_module(_effect_params_module)
EFFECT_PARAMS = _effect_params_module.EFFECT_PARAMS
merge_params = _effect_params_module.merge_params

_AUDIO_UTILS_PATH = Path(__file__).resolve().parent / "audio_utils.py"
_AUDIO_UTILS_SPEC = importlib.util.spec_from_file_location(
    "cool_effects_audio_utils_for_video_generator", _AUDIO_UTILS_PATH
)
if _AUDIO_UTILS_SPEC is None or _AUDIO_UTILS_SPEC.loader is None:
    raise ValueError(f"Missing audio utils config at {_AUDIO_UTILS_PATH}")
_audio_utils_module = importlib.util.module_from_spec(_AUDIO_UTILS_SPEC)
_AUDIO_UTILS_SPEC.loader.exec_module(_audio_utils_module)
extract_audio_features = _audio_utils_module.extract_audio_features
WAVEFORM_SAMPLE_COUNT = _audio_utils_module.WAVEFORM_SAMPLE_COUNT

_FULLSCREEN_QUAD_VERTICES = np.array(
    [-1.0, -1.0, 1.0, -1.0, -1.0, 1.0, -1.0, 1.0, 1.0, -1.0, 1.0, 1.0],
    dtype="f4",
)

_TEXT_POSITION_ANCHORS: dict[str, tuple[float, float]] = {
    "top-left": (0.12, 0.88),
    "top-center": (0.5, 0.88),
    "top-right": (0.88, 0.88),
    "center": (0.5, 0.5),
    "bottom-left": (0.12, 0.12),
    "bottom-center": (0.5, 0.12),
    "bottom-right": (0.88, 0.12),
}

_TEXT_ANIMATION_MODES: dict[str, int] = {
    "none": 0,
    "fade_in": 1,
    "fade_in_out": 2,
    "slide_up": 3,
    "typewriter": 4,
}

# ---------------------------------------------------------------------------
# Frame-rendering helpers
# ---------------------------------------------------------------------------


def _extract_input_image(image: torch.Tensor) -> tuple[np.ndarray, int, int, int]:
    if image.ndim == 4:
        frame_batch = image
    elif image.ndim == 3:
        frame_batch = image.unsqueeze(0)
    else:
        raise ValueError("Expected image tensor with shape [N, H, W, C] or [H, W, C]")

    if frame_batch.shape[-1] != 3:
        raise ValueError("Expected RGB image input with 3 channels")

    frame_batch_cpu = frame_batch.detach().cpu().clamp(0.0, 1.0)
    _, height, width, _ = frame_batch_cpu.shape
    frame_batch_uint8 = (frame_batch_cpu.numpy() * 255.0).astype(np.uint8)
    return frame_batch_uint8, width, height, frame_batch_uint8.shape[0]


def _extract_effect_name(effect_params: dict) -> str:
    if not isinstance(effect_params, dict):
        raise ValueError("effect_params must be a dict")
    effect_name = effect_params.get("effect_name")
    if not isinstance(effect_name, str) or not effect_name:
        raise ValueError("effect_params.effect_name must be a non-empty string")
    return effect_name


def _resolve_audio_feature_frame(
    audio_features, frame_index: int
) -> tuple[float, float, float, float, float]:
    if frame_index < 0 or frame_index >= len(audio_features):
        return 0.0, 0.0, 0.0, 0.0, 0.0
    feature = audio_features[frame_index]
    if not isinstance(feature, dict):
        return 0.0, 0.0, 0.0, 0.0, 0.0

    beat_flag = feature.get("beat", False)
    beat_value = 1.0 if bool(beat_flag) else 0.0

    try:
        rms_value = float(feature.get("rms", 0.0))
    except (TypeError, ValueError):
        rms_value = 0.0

    try:
        bass_value = float(feature.get("bass", 0.0))
    except (TypeError, ValueError):
        bass_value = 0.0

    try:
        mid_value = float(feature.get("mid", 0.0))
    except (TypeError, ValueError):
        mid_value = 0.0

    try:
        treble_value = float(feature.get("treble", 0.0))
    except (TypeError, ValueError):
        treble_value = 0.0

    rms_value = float(np.clip(rms_value, 0.0, 1.0))
    bass_value = float(np.clip(bass_value, 0.0, 1.0))
    mid_value = float(np.clip(mid_value, 0.0, 1.0))
    treble_value = float(np.clip(treble_value, 0.0, 1.0))
    return beat_value, rms_value, bass_value, mid_value, treble_value


def _coerce_waveform_samples(waveform_values) -> list[float]:
    if waveform_values is None:
        return [0.0] * WAVEFORM_SAMPLE_COUNT

    if hasattr(waveform_values, "tolist"):
        waveform_values = waveform_values.tolist()

    if not isinstance(waveform_values, list):
        return [0.0] * WAVEFORM_SAMPLE_COUNT

    normalized_values: list[float] = []
    for value in waveform_values[:WAVEFORM_SAMPLE_COUNT]:
        try:
            normalized_values.append(float(np.clip(float(value), -1.0, 1.0)))
        except (TypeError, ValueError):
            normalized_values.append(0.0)

    if len(normalized_values) < WAVEFORM_SAMPLE_COUNT:
        normalized_values.extend([0.0] * (WAVEFORM_SAMPLE_COUNT - len(normalized_values)))
    return normalized_values


def _resolve_waveform_feature_frame(audio_features, frame_index: int) -> list[float]:
    if frame_index < 0 or frame_index >= len(audio_features):
        return [0.0] * WAVEFORM_SAMPLE_COUNT
    feature = audio_features[frame_index]
    if not isinstance(feature, dict):
        return [0.0] * WAVEFORM_SAMPLE_COUNT
    return _coerce_waveform_samples(feature.get("waveform"))


def _set_program_uniform(program, uniform_name: str, uniform_value) -> None:
    try:
        uniform = program[uniform_name]
    except KeyError:
        return

    if isinstance(uniform_value, (int, float, np.floating, np.integer)):
        uniform.value = float(uniform_value)
        return

    if isinstance(uniform_value, (list, tuple)):
        coerced_values = tuple(float(value) for value in uniform_value)
        uniform.value = coerced_values
        return

    raise ValueError(f"Unsupported uniform type for '{uniform_name}': {type(uniform_value).__name__}")


def _resolve_frame_time_seconds(frame_index: int, fps: int) -> float:
    if fps <= 0:
        raise ValueError("fps must be greater than zero")
    if frame_index < 0:
        raise ValueError("frame_index must be non-negative")
    return frame_index / fps


def _resolve_timing_uniforms(frame_index: int, fps: int, duration: float) -> dict[str, float]:
    return {"u_time": _resolve_frame_time_seconds(frame_index, fps), "u_duration": float(duration)}


def _resolve_text_animation_mode(animation: str) -> int:
    return _TEXT_ANIMATION_MODES.get(animation, _TEXT_ANIMATION_MODES["fade_in"])


def _resolve_text_animation_progress(time_seconds: float, animation_duration: float) -> float:
    if animation_duration <= 0.0:
        return 1.0
    return float(np.clip(time_seconds / animation_duration, 0.0, 1.0))


def _resolve_typewriter_visible_text(text: str, time_seconds: float, animation_duration: float) -> str:
    if not text:
        return ""
    if animation_duration <= 0.0:
        return text
    progress = _resolve_text_animation_progress(time_seconds, animation_duration)
    visible_count = int(np.ceil(progress * len(text)))
    return text[: int(np.clip(visible_count, 0, len(text)))]


def _resolve_text_overlay_anchor(position: str) -> tuple[float, float]:
    return _TEXT_POSITION_ANCHORS.get(position, _TEXT_POSITION_ANCHORS["bottom-center"])


def _load_text_overlay_font(font_name: str, font_size: int):
    try:
        from PIL import ImageFont
    except ImportError as error:
        raise ValueError("Pillow is required for the text_overlay effect.") from error

    font_path = Path(__file__).resolve().parent.parent / "assets" / "fonts" / font_name
    if not font_path.is_file():
        raise ValueError(f"Font not found for text_overlay effect: {font_name}")
    try:
        return ImageFont.truetype(str(font_path), font_size)
    except OSError as error:
        raise ValueError(f"Unable to load font for text_overlay effect: {font_name}") from error


def _render_text_overlay_texture_array(
    width: int,
    height: int,
    text: str,
    font,
    anchor: tuple[float, float],
    offset_x: float,
    offset_y: float,
) -> np.ndarray:
    try:
        from PIL import Image, ImageDraw
    except ImportError as error:
        raise ValueError("Pillow is required for the text_overlay effect.") from error

    text_canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    if text:
        draw = ImageDraw.Draw(text_canvas)
        text_box = draw.textbbox((0, 0), text, font=font)
        text_width = max(0, text_box[2] - text_box[0])
        text_height = max(0, text_box[3] - text_box[1])
        anchor_x_px = (anchor[0] + offset_x) * width
        anchor_y_px = (anchor[1] + offset_y) * height
        draw_x = int(round(anchor_x_px - (text_width * 0.5) - text_box[0]))
        draw_y = int(round(anchor_y_px - (text_height * 0.5) - text_box[1]))
        draw.text((draw_x, draw_y), text, font=font, fill=(255, 255, 255, 255))

    return np.asarray(text_canvas, dtype=np.uint8)


def _render_text_overlay_frames(
    image: torch.Tensor,
    effect_params: dict,
    fps: int,
    duration: float,
) -> torch.Tensor:
    if not isinstance(effect_params.get("params"), dict):
        raise ValueError("effect_params.params must be a dict")
    params = effect_params["params"]

    try:
        fragment_shader_source = load_shader("text_overlay")
    except FileNotFoundError as error:
        raise ValueError("Shader not found for effect_name 'text_overlay'.") from error
    try:
        vertex_shader_source = load_vertex_shader("fullscreen_quad")
    except FileNotFoundError as error:
        raise ValueError("Vertex shader not found for 'fullscreen_quad'.") from error

    import moderngl

    source_frames, width, height, source_frame_count = _extract_input_image(image)
    frame_count = round(duration * fps)

    text_value = str(params.get("text", ""))
    font_name = str(params.get("font", "")).strip()
    if not font_name:
        raise ValueError("text_overlay effect requires a font name")
    font_size = int(np.clip(int(params.get("font_size", 48)), 8, 256))
    anchor = _resolve_text_overlay_anchor(str(params.get("position", "bottom-center")))
    offset_x = float(params.get("offset_x", 0.0))
    offset_y = float(params.get("offset_y", 0.0))
    animation = str(params.get("animation", "fade_in"))
    animation_mode = _resolve_text_animation_mode(animation)
    animation_duration = float(np.clip(float(params.get("animation_duration", 0.5)), 0.0, 5.0))

    text_uniforms = {
        "u_anchor_x": anchor[0],
        "u_anchor_y": anchor[1],
        "u_offset_x": offset_x,
        "u_offset_y": offset_y,
        "u_color_r": float(params.get("color_r", 1.0)),
        "u_color_g": float(params.get("color_g", 1.0)),
        "u_color_b": float(params.get("color_b", 1.0)),
        "u_opacity": float(params.get("opacity", 1.0)),
        "u_font_size": float(font_size),
        "u_animation_mode": float(animation_mode),
        "u_animation_duration": animation_duration,
        "u_has_text_texture": 1.0,
    }

    font = _load_text_overlay_font(font_name, font_size)
    text_texture_array = _render_text_overlay_texture_array(
        width,
        height,
        text_value,
        font,
        anchor,
        offset_x,
        offset_y,
    )

    ctx = program = input_texture = text_texture = output_renderbuffer = fbo = vbo = vao = None
    rendered_frames = []
    active_source_frame_index = 0
    active_visible_text = text_value
    is_typewriter = animation_mode == _TEXT_ANIMATION_MODES["typewriter"]

    try:
        ctx = moderngl.create_standalone_context(backend="egl")
        program = ctx.program(
            vertex_shader=vertex_shader_source,
            fragment_shader=fragment_shader_source,
        )
        input_texture = ctx.texture((width, height), 3, source_frames[0][::-1].tobytes())
        text_texture = ctx.texture((width, height), 4, text_texture_array[::-1].tobytes())
        output_renderbuffer = ctx.renderbuffer((width, height), components=3)
        fbo = ctx.framebuffer(color_attachments=[output_renderbuffer])
        vbo = ctx.buffer(_FULLSCREEN_QUAD_VERTICES.tobytes())
        vao = ctx.simple_vertex_array(program, vbo, "in_pos")

        input_texture.use(location=0)
        text_texture.use(location=1)
        try:
            program["u_image"].value = 0
        except KeyError:
            pass
        try:
            program["u_text_texture"].value = 1
        except KeyError:
            pass
        _set_program_uniform(program, "u_resolution", (width, height))

        for frame_index in range(frame_count):
            source_frame_index = frame_index % source_frame_count
            if source_frame_index != active_source_frame_index:
                input_texture.write(source_frames[source_frame_index][::-1].tobytes())
                active_source_frame_index = source_frame_index

            time_seconds = _resolve_frame_time_seconds(frame_index, fps)
            if is_typewriter:
                visible_text = _resolve_typewriter_visible_text(
                    text_value,
                    time_seconds,
                    animation_duration,
                )
                if visible_text != active_visible_text:
                    updated_texture_array = _render_text_overlay_texture_array(
                        width,
                        height,
                        visible_text,
                        font,
                        anchor,
                        offset_x,
                        offset_y,
                    )
                    text_texture.write(updated_texture_array[::-1].tobytes())
                    active_visible_text = visible_text

            for uniform_name, uniform_value in text_uniforms.items():
                _set_program_uniform(program, uniform_name, uniform_value)
            for uniform_name, uniform_value in _resolve_timing_uniforms(frame_index, fps, duration).items():
                _set_program_uniform(program, uniform_name, uniform_value)

            fbo.use()
            vao.render(moderngl.TRIANGLES)
            frame_bytes = fbo.read(components=3)
            frame_array = np.frombuffer(frame_bytes, dtype=np.uint8).reshape(height, width, 3)[::-1].copy()
            frame_normalized = frame_array.astype(np.float32) / np.float32(255.0)
            rendered_frames.append(torch.from_numpy(frame_normalized))

        if rendered_frames:
            return torch.stack(rendered_frames, dim=0)
        return torch.empty((0, height, width, 3), dtype=torch.float32)
    finally:
        for resource in (vao, vbo, fbo, output_renderbuffer, text_texture, input_texture, program):
            if resource is not None:
                resource.release()
        if ctx is not None:
            ctx.release()


def _render_frames(
    image: torch.Tensor,
    effect_params: dict,
    fps: int,
    duration: float,
    audio_features: list[dict] | None = None,
) -> torch.Tensor:
    """Render all animation frames via OpenGL/GLSL and return a [N, H, W, 3] float32 tensor."""
    effect_name = _extract_effect_name(effect_params)
    if effect_name == "text_overlay":
        return _render_text_overlay_frames(image, effect_params, fps, duration)

    if not isinstance(effect_params.get("params"), dict):
        raise ValueError("effect_params.params must be a dict")
    try:
        final_uniform_params = merge_params(effect_params["effect_name"], effect_params["params"])
    except KeyError as error:
        raise ValueError(f"Unknown effect in effect_params: '{effect_name}'") from error

    try:
        fragment_shader_source = load_shader(effect_name)
    except FileNotFoundError as error:
        raise ValueError(f"Shader not found for effect_name '{effect_name}'.") from error
    try:
        vertex_shader_source = load_vertex_shader("fullscreen_quad")
    except FileNotFoundError as error:
        raise ValueError("Vertex shader not found for 'fullscreen_quad'.") from error

    import moderngl

    source_frames, width, height, source_frame_count = _extract_input_image(image)
    frame_count = round(duration * fps)
    resolved_audio_features = audio_features or []

    ctx = program = input_texture = output_renderbuffer = fbo = vbo = vao = None
    rendered_frames = []

    try:
        ctx = moderngl.create_standalone_context(backend="egl")
        program = ctx.program(
            vertex_shader=vertex_shader_source,
            fragment_shader=fragment_shader_source,
        )
        # Flip frames vertically before uploading: OpenGL's texture origin is bottom-left,
        # so flipping here makes GL top = image top, which matches the WebGL preview Y axis.
        input_texture = ctx.texture((width, height), 3, source_frames[0][::-1].tobytes())
        output_renderbuffer = ctx.renderbuffer((width, height), components=3)
        fbo = ctx.framebuffer(color_attachments=[output_renderbuffer])
        vbo = ctx.buffer(_FULLSCREEN_QUAD_VERTICES.tobytes())
        vao = ctx.simple_vertex_array(program, vbo, "in_pos")

        input_texture.use(location=0)
        try:
            program["u_image"].value = 0
        except KeyError:
            pass
        try:
            program["u_resolution"].value = (width, height)
        except KeyError:
            pass
        active_source_frame_index = 0

        for frame_index in range(frame_count):
            source_frame_index = frame_index % source_frame_count
            if source_frame_index != active_source_frame_index:
                input_texture.write(source_frames[source_frame_index][::-1].tobytes())
                active_source_frame_index = source_frame_index
            for uniform_name, uniform_value in final_uniform_params.items():
                _set_program_uniform(program, uniform_name, uniform_value)
            beat_value, rms_value, bass_value, mid_value, treble_value = _resolve_audio_feature_frame(
                resolved_audio_features, frame_index
            )
            try:
                program["u_beat"].value = beat_value
            except KeyError:
                pass
            try:
                program["u_rms"].value = rms_value
            except KeyError:
                pass
            try:
                program["u_bass"].value = bass_value
            except KeyError:
                pass
            try:
                program["u_mid"].value = mid_value
            except KeyError:
                pass
            try:
                program["u_treble"].value = treble_value
            except KeyError:
                pass
            waveform_samples = _resolve_waveform_feature_frame(resolved_audio_features, frame_index)
            features = resolved_audio_features
            i = frame_index
            if 0 <= i < len(features) and isinstance(features[i], dict) and "waveform" in features[i]:
                waveform_samples = _coerce_waveform_samples(features[i]["waveform"])
            try:
                program['u_waveform'].value = features[i]['waveform']
            except (KeyError, IndexError, TypeError, ValueError):
                try:
                    program["u_waveform"].value = waveform_samples
                except KeyError:
                    pass
            for uniform_name, uniform_value in _resolve_timing_uniforms(frame_index, fps, duration).items():
                _set_program_uniform(program, uniform_name, uniform_value)
            fbo.use()
            vao.render(moderngl.TRIANGLES)
            frame_bytes = fbo.read(components=3)
            # fbo.read() returns rows bottom-to-top (OpenGL convention). Flip vertically
            # so row 0 = top of image, matching ComfyUI's expected tensor layout and
            # making GL Y coordinates consistent with the WebGL preview.
            frame_array = np.frombuffer(frame_bytes, dtype=np.uint8).reshape(height, width, 3)[::-1].copy()
            frame_normalized = frame_array.astype(np.float32) / np.float32(255.0)
            rendered_frames.append(torch.from_numpy(frame_normalized))

        if rendered_frames:
            return torch.stack(rendered_frames, dim=0)
        return torch.empty((0, height, width, 3), dtype=torch.float32)
    finally:
        for resource in (vao, vbo, fbo, output_renderbuffer, input_texture, program):
            if resource is not None:
                resource.release()
        if ctx is not None:
            ctx.release()


# ---------------------------------------------------------------------------
# Video preview helpers
# ---------------------------------------------------------------------------


def _build_view_url(video_entry: dict) -> str:
    filename = str(video_entry.get("filename", "")).strip()
    if not filename:
        return ""
    file_type = str(video_entry.get("type", "input")).strip() or "input"
    subfolder = str(video_entry.get("subfolder", "")).strip()
    query_parts = [
        f"filename={quote(filename)}",
        f"type={quote(file_type)}",
    ]
    if subfolder:
        query_parts.append(f"subfolder={quote(subfolder)}")
    return f"/view?{'&'.join(query_parts)}"


def _save_video_preview_to_temp(video) -> list[dict]:
    if not hasattr(video, "save_to"):
        return []

    try:
        width, height = video.get_dimensions()
    except Exception:
        width, height = 0, 0

    try:
        import folder_paths  # type: ignore

        full_output_folder, filename, counter, subfolder, _ = folder_paths.get_save_image_path(
            "cool-effects-preview",
            folder_paths.get_temp_directory(),
            width,
            height,
        )
        file = f"{filename}_{counter:05}_.mp4"
        output_path = os.path.join(full_output_folder, file)
    except ImportError:
        temp_dir = Path(tempfile.gettempdir()) / "comfyui-cool-effects"
        temp_dir.mkdir(parents=True, exist_ok=True)
        subfolder = ""
        file = f"cool-effects-preview-{uuid.uuid4().hex}.mp4"
        output_path = str(temp_dir / file)

    video.save_to(output_path)
    return [
        {
            "source_url": _build_view_url(
                {"filename": file, "subfolder": subfolder, "type": "temp"}
            ),
            "filename": file,
            "type": "temp",
            "subfolder": subfolder,
            "format": "video/mp4",
        }
    ]


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------


class CoolVideoGenerator:
    """Generates effect frames, assembles a VIDEO, and previews it in the canvas widget.

    - effect_count controls how many effect_params_N inputs are active (1-8).
    - Effects are applied sequentially: the output of each becomes the input of the next.
    - audio optional: adds an audio track to the output VIDEO.
    - Outputs VIDEO so it can be piped into SaveVideo if needed.
    """

    @classmethod
    def INPUT_TYPES(cls):
        optional_effect_inputs = {
            f"effect_params_{slot_index}": (EFFECT_PARAMS,)
            for slot_index in range(1, 9)
        }
        return {
            "required": {
                "image": ("IMAGE",),
                "fps": ("INT", {"default": 30, "min": 1, "max": 60}),
                "duration": ("FLOAT", {"default": 3.0, "min": 0.5, "max": 300.0, "step": 0.5}),
                "effect_count": ("INT", {"default": 1, "min": 1, "max": 8}),
            },
            "optional": {
                "audio": ("AUDIO",),
                **optional_effect_inputs,
            },
        }

    RETURN_TYPES = ("VIDEO",)
    RETURN_NAMES = ("video",)
    FUNCTION = "execute"
    OUTPUT_NODE = True
    CATEGORY = "CoolEffects"

    def execute(self, image, fps, duration, effect_count=1, audio=None, **kwargs):
        from comfy_api.latest import InputImpl, Types  # type: ignore

        audio_features = extract_audio_features(audio, fps=fps, duration=duration)

        # 1. Collect effect_params_1 … effect_params_N in order (up to effect_count)
        effect_params_list = []
        for i in range(1, effect_count + 1):
            param = kwargs.get(f"effect_params_{i}")
            if param is not None:
                effect_params_list.append(param)

        # 2. Render frames: apply effects sequentially, or repeat input if none connected
        if effect_params_list:
            frames = image
            for effect_params in effect_params_list:
                frames = _render_frames(
                    frames,
                    effect_params,
                    fps,
                    duration,
                    audio_features=audio_features,
                )
        else:
            frame_count = round(duration * fps)
            source = image if image.ndim == 4 else image.unsqueeze(0)
            source_count = source.shape[0]
            indices = [i % source_count for i in range(frame_count)]
            frames = source[indices]

        # 3. Pack frames (+ optional audio) into a VIDEO object
        video = InputImpl.VideoFromComponents(
            Types.VideoComponents(images=frames, audio=audio, frame_rate=Fraction(fps))
        )

        # 4. Save to temp and expose the preview URL for the canvas widget
        normalized_entries: list[dict] = []
        try:
            normalized_entries = _save_video_preview_to_temp(video)
        except Exception as error:
            LOGGER.warning("[CoolVideoGenerator] failed to save video preview: %s", error)

        return {
            "ui": {
                "video": normalized_entries,
                "video_entries": normalized_entries,
            },
            "result": (video,),
        }
