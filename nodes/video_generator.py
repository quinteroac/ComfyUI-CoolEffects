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

_LUT_UTILS_PATH = Path(__file__).resolve().parent / "lut_utils.py"
_LUT_UTILS_SPEC = importlib.util.spec_from_file_location(
    "cool_effects_lut_utils_for_video_generator", _LUT_UTILS_PATH
)
if _LUT_UTILS_SPEC is None or _LUT_UTILS_SPEC.loader is None:
    raise ValueError(f"Missing LUT utils config at {_LUT_UTILS_PATH}")
_lut_utils_module = importlib.util.module_from_spec(_LUT_UTILS_SPEC)
_LUT_UTILS_SPEC.loader.exec_module(_lut_utils_module)
create_identity_lut_strip = _lut_utils_module.create_identity_lut_strip
parse_cube_lut_file = _lut_utils_module.parse_cube_lut_file

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

_SHARED_EGL_CTX = None


def _create_egl_context():
    """Create a moderngl standalone EGL context on the NVIDIA GPU.

    Strategy (in order):
    1. moderngl device_index enumeration — picks the first non-software EGL device.
    2. Force NVIDIA EGL vendor file via __EGL_VENDOR_LIBRARY_FILENAMES, then retry.
    3. Plain EGL fallback (may use Mesa/llvmpipe, but keeps the code running).
    """
    import moderngl

    print("[CoolEffects] _create_egl_context: starting EGL device enumeration")

    # Strategy 1: enumerate EGL devices and pick the first hardware one.
    # moderngl >= 5.4 supports `device_index` which calls eglQueryDevicesEXT.
    try:
        for idx in range(8):
            try:
                ctx = moderngl.create_standalone_context(backend="egl", device_index=idx)
                vendor = ctx.info.get("GL_VENDOR", "")
                renderer = ctx.info.get("GL_RENDERER", "")
                print(f"[CoolEffects] EGL device {idx}: vendor={vendor!r} renderer={renderer!r}")
                v, r = vendor.lower(), renderer.lower()
                if "nvidia" in v or "nvidia" in r:
                    print(f"[CoolEffects] Selected NVIDIA device at index {idx}")
                    return ctx
                if any(s in r for s in ("llvmpipe", "softpipe", "software", "virgl")):
                    ctx.release()
                    continue
                print(f"[CoolEffects] Selected hardware device at index {idx}")
                return ctx
            except Exception as e:
                print(f"[CoolEffects] EGL device {idx} failed: {e}")
                break
    except Exception as e:
        print(f"[CoolEffects] device_index enumeration not supported: {e}")

    # Strategy 2: force NVIDIA vendor file before EGL initialisation.
    _nvidia_vendor_files = [
        "/usr/share/glvnd/egl_vendor.d/10_nvidia.json",
        "/usr/share/egl/egl_external_platform.d/10_nvidia.json",
    ]
    for vendor_file in _nvidia_vendor_files:
        if Path(vendor_file).exists() and "__EGL_VENDOR_LIBRARY_FILENAMES" not in os.environ:
            os.environ["__EGL_VENDOR_LIBRARY_FILENAMES"] = vendor_file
            print(f"[CoolEffects] Forcing NVIDIA EGL vendor file: {vendor_file}")
            break

    try:
        ctx = moderngl.create_standalone_context(backend="egl")
        vendor = ctx.info.get("GL_VENDOR", "")
        renderer = ctx.info.get("GL_RENDERER", "")
        print(f"[CoolEffects] EGL context (no device_index): vendor={vendor!r} renderer={renderer!r}")
        return ctx
    except Exception as e:
        print(f"[CoolEffects] EGL backend failed: {e}")

    # Strategy 3: plain fallback (Mesa/CPU — slow but functional)
    print("[CoolEffects] WARNING: falling back to software rendering (GPU-Util will be 0%)")
    return moderngl.create_standalone_context()


def _get_shared_egl_context():
    # Cache the context across calls: EGL device enumeration costs ~1-2s and
    # chaining N effects previously paid that cost N times per workflow run.
    global _SHARED_EGL_CTX
    if _SHARED_EGL_CTX is None:
        _SHARED_EGL_CTX = _create_egl_context()
    return _SHARED_EGL_CTX


def _resolve_static_uniforms(program, static_uniforms: dict) -> None:
    for uniform_name, uniform_value in static_uniforms.items():
        _set_program_uniform(program, uniform_name, uniform_value)


def _prefetch_uniform_handles(program, uniform_names) -> dict:
    handles: dict = {}
    for name in uniform_names:
        try:
            handles[name] = program[name]
        except KeyError:
            continue
    return handles


def _run_shader_render_loop(
    ctx,
    fbo,
    vao,
    width: int,
    height: int,
    frame_count: int,
    source_frames: list[bytes],
    input_texture,
    per_frame_callback,
    frame_sink,
) -> None:
    """Execute the render loop with double-buffered async PBO readback.

    per_frame_callback(frame_index) is invoked just before each draw; it must
    update any dynamic uniforms and, if needed, reupload textures.

    frame_sink(frame_index, flipped_uint8_view) is invoked once per drained
    frame. `flipped_uint8_view` is a numpy [H, W, 3] uint8 view into the PBO
    data with the vertical flip already applied; the caller must copy or
    consume it before returning (the underlying buffer is reused).
    """
    import moderngl  # noqa: F401  (ensures module loaded; vao.render uses moderngl.TRIANGLES)

    if frame_count == 0:
        return

    source_frame_count = len(source_frames)
    active_source_frame_index = 0

    frame_byte_size = width * height * 3
    pbo_a = ctx.buffer(reserve=frame_byte_size)
    pbo_b = ctx.buffer(reserve=frame_byte_size)
    pbos = (pbo_a, pbo_b)
    # Pre-allocated readback buffer: reused every drain to avoid per-frame
    # heap allocation of a Python bytes object.
    readback_buf = np.empty(frame_byte_size, dtype=np.uint8)

    try:
        in_flight_frame = -1
        for frame_index in range(frame_count):
            source_frame_index = frame_index % source_frame_count
            if source_frame_index != active_source_frame_index:
                input_texture.write(source_frames[source_frame_index])
                active_source_frame_index = source_frame_index

            per_frame_callback(frame_index)

            fbo.use()
            vao.render(moderngl.TRIANGLES)
            # Async GPU -> PBO copy for the frame just rendered.
            fbo.read_into(pbos[frame_index % 2], components=3)

            # Drain the previous frame's PBO while the GPU works on the next one.
            if in_flight_frame >= 0:
                pbos[in_flight_frame % 2].read_into(readback_buf)
                frame_view = readback_buf.reshape(height, width, 3)
                frame_sink(in_flight_frame, frame_view[::-1])
            in_flight_frame = frame_index

        # Drain the final queued frame.
        if in_flight_frame >= 0:
            pbos[in_flight_frame % 2].read_into(readback_buf)
            frame_view = readback_buf.reshape(height, width, 3)
            frame_sink(in_flight_frame, frame_view[::-1])
    finally:
        pbo_a.release()
        pbo_b.release()


def _build_tensor_frame_sink(width: int, height: int, frame_count: int):
    """Return (sink_callable, finalize_callable).

    finalize_callable() returns the completed [N, H, W, 3] float32 torch tensor.

    Frames are accumulated as uint8 into a pinned (page-locked) tensor so that
    the PCIe DMA and the final uint8->float32 conversion are faster.  Falls
    back to regular memory when CUDA is unavailable.
    """
    try:
        output_uint8 = torch.empty(
            (frame_count, height, width, 3), dtype=torch.uint8
        ).pin_memory()
    except RuntimeError:
        output_uint8 = torch.empty((frame_count, height, width, 3), dtype=torch.uint8)

    output_np = output_uint8.numpy()  # zero-copy view into the pinned buffer

    def _sink(frame_index: int, flipped_view: np.ndarray) -> None:
        np.copyto(output_np[frame_index], flipped_view)

    def _finalize() -> torch.Tensor:
        # Single vectorised uint8->float32 pass over the whole batch.
        return output_uint8.float().div_(255.0)

    return _sink, _finalize


def _extract_input_image(image: torch.Tensor) -> tuple[list[bytes], int, int, int]:
    """Convert image tensor to pre-flipped bytes per source frame for GL upload."""
    if image.ndim == 4:
        frame_batch = image
    elif image.ndim == 3:
        frame_batch = image.unsqueeze(0)
    else:
        raise ValueError("Expected image tensor with shape [N, H, W, C] or [H, W, C]")

    if frame_batch.shape[-1] != 3:
        raise ValueError("Expected RGB image input with 3 channels")

    # Cast float32 [0,1] -> uint8 [0,255] in torch so the intermediate float32 copy
    # never materialises as a separate CPU allocation. For an N=300 frames 1080p
    # input this cuts CPU peak memory from ~22GB to ~1.9GB in this function alone.
    frame_batch_uint8_tensor = (
        frame_batch.detach().clamp(0.0, 1.0).mul(255.0).to(torch.uint8).cpu().contiguous()
    )
    frame_batch_uint8 = frame_batch_uint8_tensor.numpy()
    _, height, width, _ = frame_batch_uint8.shape
    # Pre-flip vertically once (OpenGL origin = bottom-left) and pre-serialise to bytes.
    # This avoids repeating [::-1].tobytes() inside the render loop.
    source_frames_bytes = [
        frame_batch_uint8[i, ::-1].tobytes() for i in range(frame_batch_uint8.shape[0])
    ]
    return source_frames_bytes, width, height, len(source_frames_bytes)


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

    source_frames, width, height, _ = _extract_input_image(image)
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

    program = input_texture = text_texture = output_renderbuffer = fbo = vbo = vao = None
    active_visible_text = [text_value]
    is_typewriter = animation_mode == _TEXT_ANIMATION_MODES["typewriter"]
    ctx = _get_shared_egl_context()

    try:
        program = ctx.program(
            vertex_shader=vertex_shader_source,
            fragment_shader=fragment_shader_source,
        )
        input_texture = ctx.texture((width, height), 3, source_frames[0])
        text_texture = ctx.texture((width, height), 4, text_texture_array[::-1].tobytes())
        output_renderbuffer = ctx.renderbuffer((width, height), components=3)
        fbo = ctx.framebuffer(color_attachments=[output_renderbuffer])
        vbo = ctx.buffer(_FULLSCREEN_QUAD_VERTICES.tobytes())
        vao = ctx.simple_vertex_array(program, vbo, "in_pos")

        input_texture.use(location=0)
        text_texture.use(location=1)

        # Static uniforms (including resolution, duration, text params) set once.
        static_uniforms: dict = dict(text_uniforms)
        static_uniforms["u_resolution"] = (float(width), float(height))
        static_uniforms["u_duration"] = float(duration)
        _resolve_static_uniforms(program, static_uniforms)
        try:
            program["u_image"].value = 0
        except KeyError:
            pass
        try:
            program["u_text_texture"].value = 1
        except KeyError:
            pass

        dynamic_handles = _prefetch_uniform_handles(program, ("u_time",))
        u_time_handle = dynamic_handles.get("u_time")
        inv_fps = 1.0 / float(fps)

        def _update_dynamic_uniforms(frame_index: int) -> None:
            if u_time_handle is not None:
                u_time_handle.value = frame_index * inv_fps
            if is_typewriter:
                time_seconds = frame_index * inv_fps
                visible_text = _resolve_typewriter_visible_text(
                    text_value, time_seconds, animation_duration
                )
                if visible_text != active_visible_text[0]:
                    updated_texture_array = _render_text_overlay_texture_array(
                        width, height, visible_text, font, anchor, offset_x, offset_y,
                    )
                    text_texture.write(updated_texture_array[::-1].tobytes())
                    active_visible_text[0] = visible_text

        frame_sink, finalize_tensor = _build_tensor_frame_sink(width, height, frame_count)
        _run_shader_render_loop(
            ctx=ctx,
            fbo=fbo,
            vao=vao,
            width=width,
            height=height,
            frame_count=frame_count,
            source_frames=source_frames,
            input_texture=input_texture,
            per_frame_callback=_update_dynamic_uniforms,
            frame_sink=frame_sink,
        )
        return finalize_tensor()
    finally:
        for resource in (vao, vbo, fbo, output_renderbuffer, text_texture, input_texture, program):
            if resource is not None:
                resource.release()


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

    source_frames, width, height, _ = _extract_input_image(image)
    frame_count = round(duration * fps)
    resolved_audio_features = audio_features or []

    lut_payload = None
    if effect_name == "lut":
        lut_path = str(effect_params["params"].get("lut_path", "")).strip()
        if lut_path:
            lut_payload = parse_cube_lut_file(lut_path)
        else:
            lut_strip = create_identity_lut_strip(16)
            lut_payload = {
                "size": 16,
                "domain_min": (0.0, 0.0, 0.0),
                "domain_max": (1.0, 1.0, 1.0),
                "strip": lut_strip,
            }

    program = input_texture = lut_texture = output_renderbuffer = fbo = vbo = vao = None
    ctx = _get_shared_egl_context()

    try:
        program = ctx.program(
            vertex_shader=vertex_shader_source,
            fragment_shader=fragment_shader_source,
        )
        # source_frames already pre-flipped (OpenGL origin = bottom-left)
        input_texture = ctx.texture((width, height), 3, source_frames[0])
        if lut_payload is not None:
            lut_strip = np.asarray(lut_payload["strip"], dtype="f4")
            lut_texture = ctx.texture(
                (int(lut_strip.shape[1]), int(lut_strip.shape[0])),
                3,
                lut_strip.tobytes(),
                dtype="f4",
            )
            lut_texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
            lut_texture.repeat_x = False
            lut_texture.repeat_y = False
        output_renderbuffer = ctx.renderbuffer((width, height), components=3)
        fbo = ctx.framebuffer(color_attachments=[output_renderbuffer])
        vbo = ctx.buffer(_FULLSCREEN_QUAD_VERTICES.tobytes())
        vao = ctx.simple_vertex_array(program, vbo, "in_pos")

        input_texture.use(location=0)
        if lut_texture is not None:
            lut_texture.use(location=1)

        # Static uniforms: set once before the render loop. Only audio and timing
        # change per frame; everything else can be uploaded exactly once.
        static_uniforms: dict = dict(final_uniform_params)
        static_uniforms["u_resolution"] = (float(width), float(height))
        static_uniforms["u_duration"] = float(duration)
        _resolve_static_uniforms(program, static_uniforms)
        try:
            program["u_image"].value = 0
        except KeyError:
            pass
        if lut_texture is not None:
            try:
                program["u_lut_texture"].value = 1
            except KeyError:
                pass
            _set_program_uniform(program, "u_lut_size", float(lut_payload["size"]))
            _set_program_uniform(program, "u_domain_min", tuple(lut_payload["domain_min"]))
            _set_program_uniform(program, "u_domain_max", tuple(lut_payload["domain_max"]))

        # Per-frame handles: resolve once, skip try/except KeyError per frame.
        dynamic_handles = _prefetch_uniform_handles(
            program,
            ("u_time", "u_beat", "u_rms", "u_bass", "u_mid", "u_treble", "u_waveform"),
        )
        u_time_handle = dynamic_handles.get("u_time")
        u_beat_handle = dynamic_handles.get("u_beat")
        u_rms_handle = dynamic_handles.get("u_rms")
        u_bass_handle = dynamic_handles.get("u_bass")
        u_mid_handle = dynamic_handles.get("u_mid")
        u_treble_handle = dynamic_handles.get("u_treble")
        u_waveform_handle = dynamic_handles.get("u_waveform")
        inv_fps = 1.0 / float(fps)

        def _update_dynamic_uniforms(frame_index: int) -> None:
            if u_time_handle is not None:
                u_time_handle.value = frame_index * inv_fps
            beat_value, rms_value, bass_value, mid_value, treble_value = _resolve_audio_feature_frame(
                resolved_audio_features, frame_index
            )
            if u_beat_handle is not None:
                u_beat_handle.value = beat_value
            if u_rms_handle is not None:
                u_rms_handle.value = rms_value
            if u_bass_handle is not None:
                u_bass_handle.value = bass_value
            if u_mid_handle is not None:
                u_mid_handle.value = mid_value
            if u_treble_handle is not None:
                u_treble_handle.value = treble_value
            if u_waveform_handle is not None:
                u_waveform_handle.value = _resolve_waveform_feature_frame(
                    resolved_audio_features, frame_index
                )

        frame_sink, finalize_tensor = _build_tensor_frame_sink(width, height, frame_count)
        _run_shader_render_loop(
            ctx=ctx,
            fbo=fbo,
            vao=vao,
            width=width,
            height=height,
            frame_count=frame_count,
            source_frames=source_frames,
            input_texture=input_texture,
            per_frame_callback=_update_dynamic_uniforms,
            frame_sink=frame_sink,
        )
        return finalize_tensor()
    finally:
        # Keep the shared EGL context alive; only release per-effect resources.
        for resource in (vao, vbo, fbo, output_renderbuffer, lut_texture, input_texture, program):
            if resource is not None:
                resource.release()


# ---------------------------------------------------------------------------
# Streaming render (avoids materialising the full [N, H, W, 3] float32 tensor)
# ---------------------------------------------------------------------------


def _build_pyav_encoding_sink(video_stream, output_container, width: int, height: int):
    """Return a frame_sink that encodes each frame into the container.

    Uses a single persistent contiguous uint8 buffer to avoid per-frame
    allocations for `av.VideoFrame.from_ndarray` (which requires contiguous
    input, while our PBO-derived views are a reversed slice).
    """
    import av  # local import to keep module import cost low

    contig_frame = np.empty((height, width, 3), dtype=np.uint8)

    def _sink(frame_index: int, flipped_view: np.ndarray) -> None:
        np.copyto(contig_frame, flipped_view)
        av_frame = av.VideoFrame.from_ndarray(contig_frame, format="rgb24")
        av_frame = av_frame.reformat(format="yuv420p")
        for packet in video_stream.encode(av_frame):
            output_container.mux(packet)

    return _sink


def _add_audio_stream(output_container, audio):
    """Create the AAC audio stream on the container BEFORE any encoding starts.

    Must be called before the first mux() so the stream is included in the
    container header.  Returns the stream, or None if there is no audio.
    """
    if not audio:
        return None
    audio_sample_rate = int(audio["sample_rate"])
    waveform = audio["waveform"]
    layout = {1: "mono", 2: "stereo", 6: "5.1"}.get(int(waveform.shape[1]), "stereo")
    audio_stream = output_container.add_stream("aac", rate=audio_sample_rate, layout=layout)
    return audio_stream


def _encode_audio_track(output_container, audio_stream, audio, frames_count: int, frame_rate: Fraction) -> None:
    """Encode and mux the audio data into an already-registered stream.

    Must be called AFTER all video packets have been muxed so that the
    container header has already been written (avformat_write_header).
    """
    import av
    import math as _math

    if not audio or audio_stream is None:
        return
    audio_sample_rate = int(audio["sample_rate"])
    waveform = audio["waveform"]
    sample_limit = _math.ceil((audio_sample_rate / frame_rate) * frames_count)
    # waveform shape: (batch, channels, samples) — take first batch item
    waveform = waveform[0, :, :sample_limit]
    layout = {1: "mono", 2: "stereo", 6: "5.1"}.get(int(waveform.shape[0]), "stereo")
    audio_frame = av.AudioFrame.from_ndarray(
        waveform.float().cpu().contiguous().numpy(), format="fltp", layout=layout,
    )
    audio_frame.sample_rate = audio_sample_rate
    audio_frame.pts = 0
    for packet in audio_stream.encode(audio_frame):
        output_container.mux(packet)
    for packet in audio_stream.encode(None):
        output_container.mux(packet)


def _render_single_effect_to_mp4(
    image: torch.Tensor,
    effect_params: dict,
    fps: int,
    duration: float,
    audio,
    audio_features,
    output_path: str,
) -> tuple[int, int, int]:
    """Render a single effect straight into an MP4 file (no full-tensor materialisation).

    Supports both text_overlay and non-text effects. Returns (width, height, frame_count).
    """
    import av
    import moderngl

    effect_name = _extract_effect_name(effect_params)
    frame_rate = Fraction(round(float(fps) * 1000), 1000)
    resolved_audio_features = audio_features or []

    source_frames, width, height, _ = _extract_input_image(image)
    frame_count = round(duration * fps)

    if effect_name == "text_overlay":
        shader_setup_kind = "text_overlay"
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
            width, height, text_value, font, anchor, offset_x, offset_y,
        )
        is_typewriter = animation_mode == _TEXT_ANIMATION_MODES["typewriter"]
    else:
        shader_setup_kind = "default"
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
        lut_payload = None
        if effect_name == "lut":
            lut_path = str(effect_params["params"].get("lut_path", "")).strip()
            if lut_path:
                lut_payload = parse_cube_lut_file(lut_path)
            else:
                lut_strip = create_identity_lut_strip(16)
                lut_payload = {
                    "size": 16,
                    "domain_min": (0.0, 0.0, 0.0),
                    "domain_max": (1.0, 1.0, 1.0),
                    "strip": lut_strip,
                }

    program = input_texture = lut_texture = text_texture = output_renderbuffer = fbo = vbo = vao = None
    ctx = _get_shared_egl_context()

    try:
        program = ctx.program(
            vertex_shader=vertex_shader_source,
            fragment_shader=fragment_shader_source,
        )
        input_texture = ctx.texture((width, height), 3, source_frames[0])
        output_renderbuffer = ctx.renderbuffer((width, height), components=3)
        fbo = ctx.framebuffer(color_attachments=[output_renderbuffer])
        vbo = ctx.buffer(_FULLSCREEN_QUAD_VERTICES.tobytes())
        vao = ctx.simple_vertex_array(program, vbo, "in_pos")

        input_texture.use(location=0)

        if shader_setup_kind == "text_overlay":
            text_texture = ctx.texture((width, height), 4, text_texture_array[::-1].tobytes())
            text_texture.use(location=1)
            static_uniforms: dict = dict(text_uniforms)
            static_uniforms["u_resolution"] = (float(width), float(height))
            static_uniforms["u_duration"] = float(duration)
            _resolve_static_uniforms(program, static_uniforms)
            try:
                program["u_image"].value = 0
            except KeyError:
                pass
            try:
                program["u_text_texture"].value = 1
            except KeyError:
                pass
            dynamic_handles = _prefetch_uniform_handles(program, ("u_time",))
            u_time_handle = dynamic_handles.get("u_time")
            inv_fps = 1.0 / float(fps)
            active_visible_text = [text_value]

            def _update_dynamic_uniforms(frame_index: int) -> None:
                if u_time_handle is not None:
                    u_time_handle.value = frame_index * inv_fps
                if is_typewriter:
                    time_seconds = frame_index * inv_fps
                    visible_text = _resolve_typewriter_visible_text(
                        text_value, time_seconds, animation_duration,
                    )
                    if visible_text != active_visible_text[0]:
                        updated_texture_array = _render_text_overlay_texture_array(
                            width, height, visible_text, font, anchor, offset_x, offset_y,
                        )
                        text_texture.write(updated_texture_array[::-1].tobytes())
                        active_visible_text[0] = visible_text
        else:
            if lut_payload is not None:
                lut_strip = np.asarray(lut_payload["strip"], dtype="f4")
                lut_texture = ctx.texture(
                    (int(lut_strip.shape[1]), int(lut_strip.shape[0])),
                    3,
                    lut_strip.tobytes(),
                    dtype="f4",
                )
                lut_texture.filter = (moderngl.LINEAR, moderngl.LINEAR)
                lut_texture.repeat_x = False
                lut_texture.repeat_y = False
                lut_texture.use(location=1)

            static_uniforms = dict(final_uniform_params)
            static_uniforms["u_resolution"] = (float(width), float(height))
            static_uniforms["u_duration"] = float(duration)
            _resolve_static_uniforms(program, static_uniforms)
            try:
                program["u_image"].value = 0
            except KeyError:
                pass
            if lut_texture is not None:
                try:
                    program["u_lut_texture"].value = 1
                except KeyError:
                    pass
                _set_program_uniform(program, "u_lut_size", float(lut_payload["size"]))
                _set_program_uniform(program, "u_domain_min", tuple(lut_payload["domain_min"]))
                _set_program_uniform(program, "u_domain_max", tuple(lut_payload["domain_max"]))

            dynamic_handles = _prefetch_uniform_handles(
                program,
                ("u_time", "u_beat", "u_rms", "u_bass", "u_mid", "u_treble", "u_waveform"),
            )
            u_time_handle = dynamic_handles.get("u_time")
            u_beat_handle = dynamic_handles.get("u_beat")
            u_rms_handle = dynamic_handles.get("u_rms")
            u_bass_handle = dynamic_handles.get("u_bass")
            u_mid_handle = dynamic_handles.get("u_mid")
            u_treble_handle = dynamic_handles.get("u_treble")
            u_waveform_handle = dynamic_handles.get("u_waveform")
            inv_fps = 1.0 / float(fps)

            def _update_dynamic_uniforms(frame_index: int) -> None:
                if u_time_handle is not None:
                    u_time_handle.value = frame_index * inv_fps
                beat, rms, bass, mid, treble = _resolve_audio_feature_frame(
                    resolved_audio_features, frame_index,
                )
                if u_beat_handle is not None:
                    u_beat_handle.value = beat
                if u_rms_handle is not None:
                    u_rms_handle.value = rms
                if u_bass_handle is not None:
                    u_bass_handle.value = bass
                if u_mid_handle is not None:
                    u_mid_handle.value = mid
                if u_treble_handle is not None:
                    u_treble_handle.value = treble
                if u_waveform_handle is not None:
                    u_waveform_handle.value = _resolve_waveform_feature_frame(
                        resolved_audio_features, frame_index,
                    )

        with av.open(
            output_path,
            mode="w",
            options={"movflags": "use_metadata_tags"},
        ) as output_container:
            video_stream = output_container.add_stream("h264", rate=frame_rate)
            video_stream.width = width
            video_stream.height = height
            video_stream.pix_fmt = "yuv420p"

            # Audio stream must be registered BEFORE any mux() call so it is
            # included in the container header written on the first packet.
            audio_stream = _add_audio_stream(output_container, audio)

            encode_sink = _build_pyav_encoding_sink(
                video_stream, output_container, width, height,
            )

            _run_shader_render_loop(
                ctx=ctx,
                fbo=fbo,
                vao=vao,
                width=width,
                height=height,
                frame_count=frame_count,
                source_frames=source_frames,
                input_texture=input_texture,
                per_frame_callback=_update_dynamic_uniforms,
                frame_sink=encode_sink,
            )

            # Flush the h264 encoder.
            for packet in video_stream.encode(None):
                output_container.mux(packet)

            # Encode and mux audio after video is fully written.
            _encode_audio_track(output_container, audio_stream, audio, frame_count, frame_rate)

        return width, height, frame_count
    finally:
        for resource in (
            vao, vbo, fbo, output_renderbuffer, lut_texture, text_texture, input_texture, program,
        ):
            if resource is not None:
                resource.release()


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

    # Render straight to MP4 instead of materialising a [N, H, W, 3] float32 tensor
    # once it would exceed this many bytes. For a 4800-frame 1024x1024 workflow the
    # tensor is ~60GB; on typical systems anything past ~4GB risks OOM.
    _STREAMING_TENSOR_BYTES_THRESHOLD = 4 * 1024 ** 3

    def execute(self, image, fps, duration, effect_count=1, audio=None, **kwargs):
        from comfy_api.latest import InputImpl, Types  # type: ignore

        audio_features = extract_audio_features(audio, fps=fps, duration=duration)

        # 1. Collect effect_params_1 … effect_params_N in order (up to effect_count)
        effect_params_list = []
        for i in range(1, effect_count + 1):
            param = kwargs.get(f"effect_params_{i}")
            if param is not None:
                effect_params_list.append(param)

        # 2. Decide between streaming-to-MP4 and the tensor path. Streaming applies
        # when we have exactly one effect and the would-be tensor exceeds the
        # threshold; chained effects still need an intermediate tensor between steps.
        height, width = self._peek_image_hw(image)
        frame_count = round(duration * fps)
        tensor_bytes = int(frame_count) * int(height) * int(width) * 3 * 4

        if (
            len(effect_params_list) == 1
            and tensor_bytes > self._STREAMING_TENSOR_BYTES_THRESHOLD
        ):
            return self._execute_streaming(
                image=image,
                fps=fps,
                duration=duration,
                audio=audio,
                audio_features=audio_features,
                effect_params=effect_params_list[0],
                width=width,
                height=height,
                tensor_bytes=tensor_bytes,
            )

        # 3. Render frames: apply effects sequentially, or repeat input if none connected
        if effect_params_list:
            frames = image
            for effect_params in effect_params_list:
                next_frames = _render_frames(
                    frames,
                    effect_params,
                    fps,
                    duration,
                    audio_features=audio_features,
                )
                # Release the previous effect's tensor before keeping the next one
                # so peak RAM stays at ~1x tensor size across the chain instead of 2x.
                del frames
                frames = next_frames
                del next_frames
        else:
            source = image if image.ndim == 4 else image.unsqueeze(0)
            source_count = source.shape[0]
            indices = [i % source_count for i in range(frame_count)]
            frames = source[indices]

        # 4. Pack frames (+ optional audio) into a VIDEO object
        video = InputImpl.VideoFromComponents(
            Types.VideoComponents(images=frames, audio=audio, frame_rate=Fraction(fps))
        )

        # 5. Save to temp and expose the preview URL for the canvas widget
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

    @staticmethod
    def _peek_image_hw(image: torch.Tensor) -> tuple[int, int]:
        if image.ndim == 4:
            return int(image.shape[1]), int(image.shape[2])
        if image.ndim == 3:
            return int(image.shape[0]), int(image.shape[1])
        raise ValueError("Expected image tensor with shape [N, H, W, C] or [H, W, C]")

    def _execute_streaming(
        self,
        image: torch.Tensor,
        fps: int,
        duration: float,
        audio,
        audio_features,
        effect_params: dict,
        width: int,
        height: int,
        tensor_bytes: int,
    ) -> dict:
        """Render a single effect directly into the preview MP4, skipping the full tensor.

        Returns a VideoFromFile so downstream SaveVideo nodes can still copy it.
        """
        from comfy_api.latest import InputImpl  # type: ignore

        output_path, file_name, subfolder = self._allocate_preview_output_path(width, height)
        LOGGER.info(
            "[CoolVideoGenerator] tensor would be %.2f GB (%dx%d x %d frames); streaming to %s",
            tensor_bytes / (1024 ** 3),
            width,
            height,
            round(duration * fps),
            output_path,
        )

        _render_single_effect_to_mp4(
            image=image,
            effect_params=effect_params,
            fps=fps,
            duration=duration,
            audio=audio,
            audio_features=audio_features,
            output_path=output_path,
        )

        video = InputImpl.VideoFromFile(output_path)
        preview_entry = {
            "source_url": _build_view_url(
                {"filename": file_name, "subfolder": subfolder, "type": "temp"}
            ),
            "filename": file_name,
            "type": "temp",
            "subfolder": subfolder,
            "format": "video/mp4",
        }
        return {
            "ui": {
                "video": [preview_entry],
                "video_entries": [preview_entry],
            },
            "result": (video,),
        }

    @staticmethod
    def _allocate_preview_output_path(width: int, height: int) -> tuple[str, str, str]:
        """Pick the same temp location the preview saver would, so the streamed MP4
        serves as both the node output and the canvas preview."""
        try:
            import folder_paths  # type: ignore

            full_output_folder, filename, counter, subfolder, _ = folder_paths.get_save_image_path(
                "cool-effects-preview",
                folder_paths.get_temp_directory(),
                width,
                height,
            )
            file_name = f"{filename}_{counter:05}_.mp4"
            return os.path.join(full_output_folder, file_name), file_name, subfolder
        except ImportError:
            temp_dir = Path(tempfile.gettempdir()) / "comfyui-cool-effects"
            temp_dir.mkdir(parents=True, exist_ok=True)
            file_name = f"cool-effects-preview-{uuid.uuid4().hex}.mp4"
            return str(temp_dir / file_name), file_name, ""
