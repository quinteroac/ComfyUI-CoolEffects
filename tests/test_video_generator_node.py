import importlib.util
import sys
import uuid
from pathlib import Path

import pytest
import torch


PACKAGE_ROOT = Path(__file__).resolve().parent.parent
NODE_PATH = PACKAGE_ROOT / "nodes" / "video_generator.py"


def _load_module(module_path: Path):
    module_name = f"cool_effects_video_generator_test_module_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class _FakeUniform:
    def __init__(self):
        self._value = None

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        self._value = new_value


class _FakeProgram:
    def __init__(self):
        self.uniforms = {
            "u_image": _FakeUniform(),
            "u_time": _FakeUniform(),
            "u_resolution": _FakeUniform(),
        }
        self.released = False

    def __getitem__(self, key):
        return self.uniforms[key]

    def release(self):
        self.released = True


class _FakeTexture:
    def __init__(self, size, components, data):
        self.size = size
        self.components = components
        self.data = data
        self.used_locations = []
        self.released = False

    def use(self, location):
        self.used_locations.append(location)

    def release(self):
        self.released = True


class _FakeFramebuffer:
    def __init__(self, texture):
        self.texture = texture
        self.released = False
        self.use_calls = 0
        self.read_components = []
        self.read_count = 0

    def use(self):
        self.use_calls += 1

    def read(self, components):
        self.read_components.append(components)
        width, height = self.texture.size
        frame_value = self.read_count % 256
        self.read_count += 1
        return bytes([frame_value]) * (width * height * components)

    def release(self):
        self.released = True


class _FakeBuffer:
    def __init__(self, data):
        self.data = data
        self.released = False

    def release(self):
        self.released = True


class _FakeVertexArray:
    def __init__(self, program):
        self.program = program
        self.released = False
        self.rendered_times = []

    def render(self, _mode):
        self.rendered_times.append(self.program["u_time"].value)

    def release(self):
        self.released = True


class _FakeContext:
    def __init__(self):
        self.released = False
        self.program_object = None
        self.framebuffer_object = None
        self.buffer_object = None
        self.vertex_array_object = None
        self.texture_objects = []

    def program(self, *, vertex_shader, fragment_shader):
        self.vertex_shader = vertex_shader
        self.fragment_shader = fragment_shader
        self.program_object = _FakeProgram()
        return self.program_object

    def texture(self, size, components, data=None):
        texture = _FakeTexture(size=size, components=components, data=data)
        self.texture_objects.append(texture)
        return texture

    def framebuffer(self, *, color_attachments):
        self.framebuffer_object = _FakeFramebuffer(color_attachments[0])
        return self.framebuffer_object

    def buffer(self, data):
        self.buffer_object = _FakeBuffer(data)
        return self.buffer_object

    def simple_vertex_array(self, program, buffer, _attribute):
        self.vertex_array_object = _FakeVertexArray(program)
        self._buffer_ref = buffer
        return self.vertex_array_object

    def release(self):
        self.released = True


class _FakeModerngl:
    TRIANGLES = 4

    def __init__(self):
        self.create_calls = 0
        self.latest_context = None

    def create_standalone_context(self):
        self.create_calls += 1
        self.latest_context = _FakeContext()
        return self.latest_context


def test_video_generator_uses_standalone_context_and_frame_time(monkeypatch):
    module = _load_module(NODE_PATH)
    fake_moderngl = _FakeModerngl()
    monkeypatch.setitem(sys.modules, "moderngl", fake_moderngl)
    monkeypatch.setattr(module, "load_shader", lambda _name: "shader-source")

    node = module.CoolVideoGenerator()
    image = torch.ones((1, 2, 3, 3), dtype=torch.float32)

    output, = node.execute(image=image, effect_name="glitch", fps=4, duration=1.0)

    assert fake_moderngl.create_calls == 1
    assert fake_moderngl.latest_context.vertex_array_object.rendered_times == [0.0, 0.25, 0.5, 0.75]
    assert output.shape == (4, 2, 3, 3)


def test_video_generator_reads_rgb_bytes_per_frame(monkeypatch):
    module = _load_module(NODE_PATH)
    fake_moderngl = _FakeModerngl()
    monkeypatch.setitem(sys.modules, "moderngl", fake_moderngl)
    monkeypatch.setattr(module, "load_shader", lambda _name: "shader-source")

    node = module.CoolVideoGenerator()
    image = torch.ones((1, 2, 3, 3), dtype=torch.float32)
    node.execute(image=image, effect_name="glitch", fps=3, duration=1.0)

    framebuffer = fake_moderngl.latest_context.framebuffer_object
    assert framebuffer.read_components == [3, 3, 3]


def test_video_generator_returns_float32_image_batch_tensor(monkeypatch):
    module = _load_module(NODE_PATH)
    fake_moderngl = _FakeModerngl()
    monkeypatch.setitem(sys.modules, "moderngl", fake_moderngl)
    monkeypatch.setattr(module, "load_shader", lambda _name: "shader-source")

    node = module.CoolVideoGenerator()
    image = torch.ones((1, 2, 3, 3), dtype=torch.float32)
    output, = node.execute(image=image, effect_name="glitch", fps=2, duration=1.0)

    assert output.shape == (2, 2, 3, 3)
    assert output.dtype == torch.float32
    assert output.min().item() >= 0.0
    assert output.max().item() <= 1.0


def test_video_generator_returns_image_output(monkeypatch):
    module = _load_module(NODE_PATH)
    fake_moderngl = _FakeModerngl()
    monkeypatch.setitem(sys.modules, "moderngl", fake_moderngl)
    monkeypatch.setattr(module, "load_shader", lambda _name: "shader-source")

    node = module.CoolVideoGenerator()
    image = torch.ones((1, 2, 3, 3), dtype=torch.float32)
    result = node.execute(image=image, effect_name="glitch", fps=1, duration=1.0)

    assert module.CoolVideoGenerator.RETURN_TYPES == ("IMAGE",)
    assert isinstance(result, tuple)
    assert len(result) == 1
    assert isinstance(result[0], torch.Tensor)


def test_video_generator_outputs_90_frames_for_3s_at_30fps(monkeypatch):
    module = _load_module(NODE_PATH)
    fake_moderngl = _FakeModerngl()
    monkeypatch.setitem(sys.modules, "moderngl", fake_moderngl)
    monkeypatch.setattr(module, "load_shader", lambda _name: "shader-source")

    node = module.CoolVideoGenerator()
    image = torch.ones((1, 4, 5, 3), dtype=torch.float32)
    output, = node.execute(image=image, effect_name="glitch", fps=30, duration=3.0)

    assert output.shape == (90, 4, 5, 3)


def test_video_generator_output_is_preview_image_compatible(monkeypatch):
    module = _load_module(NODE_PATH)
    fake_moderngl = _FakeModerngl()
    monkeypatch.setitem(sys.modules, "moderngl", fake_moderngl)
    monkeypatch.setattr(module, "load_shader", lambda _name: "shader-source")

    node = module.CoolVideoGenerator()
    image = torch.ones((1, 2, 2, 3), dtype=torch.float32)
    output, = node.execute(image=image, effect_name="glitch", fps=3, duration=1.0)

    preview_frames = [output[frame_index] for frame_index in range(output.shape[0])]
    assert len(preview_frames) == 3
    assert all(frame.shape == (2, 2, 3) for frame in preview_frames)


def test_video_generator_binds_u_image_texture_and_resolution(monkeypatch):
    module = _load_module(NODE_PATH)
    fake_moderngl = _FakeModerngl()
    monkeypatch.setitem(sys.modules, "moderngl", fake_moderngl)
    monkeypatch.setattr(module, "load_shader", lambda _name: "shader-source")

    node = module.CoolVideoGenerator()
    image = torch.ones((1, 2, 3, 3), dtype=torch.float32)
    node.execute(image=image, effect_name="glitch", fps=1, duration=1.0)

    context = fake_moderngl.latest_context
    input_texture = context.texture_objects[0]
    program = context.program_object

    assert input_texture.used_locations == [0]
    assert program["u_image"].value == 0
    assert program["u_resolution"].value == (3, 2)


def test_video_generator_raises_value_error_when_shader_missing(monkeypatch):
    module = _load_module(NODE_PATH)
    monkeypatch.setattr(module, "load_shader", lambda _name: (_ for _ in ()).throw(FileNotFoundError("missing_effect")))

    node = module.CoolVideoGenerator()
    image = torch.ones((1, 2, 2, 3), dtype=torch.float32)

    with pytest.raises(ValueError, match="effect_name 'missing_effect'"):
        node.execute(image=image, effect_name="missing_effect", fps=1, duration=1.0)


def test_video_generator_releases_gl_resources(monkeypatch):
    module = _load_module(NODE_PATH)
    fake_moderngl = _FakeModerngl()
    monkeypatch.setitem(sys.modules, "moderngl", fake_moderngl)
    monkeypatch.setattr(module, "load_shader", lambda _name: "shader-source")

    node = module.CoolVideoGenerator()
    image = torch.ones((1, 2, 2, 3), dtype=torch.float32)
    node.execute(image=image, effect_name="glitch", fps=1, duration=1.0)

    context = fake_moderngl.latest_context
    assert context.program_object.released is True
    assert context.framebuffer_object.released is True
    assert context.buffer_object.released is True
    assert context.vertex_array_object.released is True
    assert all(texture.released for texture in context.texture_objects)
    assert context.released is True
