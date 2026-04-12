"""ComfyUI Video Generator node."""

import importlib.util
from pathlib import Path

import numpy as np
import torch


_LOADER_PATH = Path(__file__).resolve().parent.parent / "shaders" / "loader.py"
_LOADER_SPEC = importlib.util.spec_from_file_location(
    "cool_effects_shader_loader_for_video_generator", _LOADER_PATH
)
if _LOADER_SPEC is None or _LOADER_SPEC.loader is None:
    raise ValueError(f"Missing shader loader config at {_LOADER_PATH}")
_shader_loader_module = importlib.util.module_from_spec(_LOADER_SPEC)
_LOADER_SPEC.loader.exec_module(_shader_loader_module)
load_shader = _shader_loader_module.load_shader


_VERTEX_SHADER_SOURCE = """
#version 330
in vec2 in_pos;
out vec2 v_uv;
void main() {
    v_uv = (in_pos + 1.0) * 0.5;
    gl_Position = vec4(in_pos, 0.0, 1.0);
}
"""

_FULLSCREEN_QUAD_VERTICES = np.array(
    [
        -1.0,
        -1.0,
        1.0,
        -1.0,
        -1.0,
        1.0,
        -1.0,
        1.0,
        1.0,
        -1.0,
        1.0,
        1.0,
    ],
    dtype="f4",
)


def _extract_input_image(image: torch.Tensor) -> tuple[np.ndarray, int, int]:
    if image.ndim == 4:
        frame = image[0]
    elif image.ndim == 3:
        frame = image
    else:
        raise ValueError("Expected image tensor with shape [N, H, W, C] or [H, W, C]")

    if frame.shape[-1] != 3:
        raise ValueError("Expected RGB image input with 3 channels")

    frame_cpu = frame.detach().cpu().clamp(0.0, 1.0)
    height, width, _ = frame_cpu.shape
    frame_uint8 = (frame_cpu.numpy() * 255.0).astype(np.uint8)
    return frame_uint8, width, height


class CoolVideoGenerator:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "effect_name": ("STRING", {"default": "glitch"}),
                "fps": ("INT", {"default": 30, "min": 1, "max": 60}),
                "duration": ("FLOAT", {"default": 3.0, "min": 0.5, "max": 60.0, "step": 0.5}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("IMAGE",)
    FUNCTION = "execute"
    CATEGORY = "CoolEffects"

    def execute(self, image, effect_name, fps, duration):
        try:
            fragment_shader_source = load_shader(effect_name)
        except FileNotFoundError as error:
            raise ValueError(f"Shader not found for effect_name '{effect_name}'.") from error

        import moderngl

        source_frame, width, height = _extract_input_image(image)
        frame_count = round(duration * fps)

        ctx = None
        program = None
        input_texture = None
        output_texture = None
        fbo = None
        vbo = None
        vao = None
        rendered_frames = []

        try:
            ctx = moderngl.create_standalone_context()
            program = ctx.program(
                vertex_shader=_VERTEX_SHADER_SOURCE,
                fragment_shader=fragment_shader_source,
            )
            input_texture = ctx.texture((width, height), 3, source_frame.tobytes())
            output_texture = ctx.texture((width, height), 3)
            fbo = ctx.framebuffer(color_attachments=[output_texture])
            vbo = ctx.buffer(_FULLSCREEN_QUAD_VERTICES.tobytes())
            vao = ctx.simple_vertex_array(program, vbo, "in_pos")

            input_texture.use(location=0)
            program["u_image"].value = 0
            program["u_resolution"].value = (width, height)

            for frame_index in range(frame_count):
                program["u_time"].value = frame_index / fps
                fbo.use()
                vao.render(moderngl.TRIANGLES)
                frame_bytes = fbo.read(components=3)
                frame_array = np.frombuffer(frame_bytes, dtype=np.uint8).reshape(height, width, 3)
                frame_normalized = frame_array.astype(np.float32) / np.float32(255.0)
                rendered_frames.append(torch.from_numpy(frame_normalized))

            if rendered_frames:
                output = torch.stack(rendered_frames, dim=0)
            else:
                output = torch.empty((0, height, width, 3), dtype=torch.float32)
            return (output,)
        finally:
            for resource in (vao, vbo, fbo, output_texture, input_texture, program):
                if resource is not None:
                    resource.release()
            if ctx is not None:
                ctx.release()
