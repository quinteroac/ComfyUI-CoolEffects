import importlib.util
import inspect
import sys
import time
import uuid
from pathlib import Path

import pytest
torch = pytest.importorskip("torch")


PACKAGE_ROOT = Path(__file__).resolve().parent.parent
NODE_PATH = PACKAGE_ROOT / "nodes" / "video_generator.py"
EFFECT_PARAMS_PATH = PACKAGE_ROOT / "nodes" / "effect_params.py"
PACKAGE_INIT = PACKAGE_ROOT / "__init__.py"


def _load_module(module_path: Path):
    module_name = f"cool_effects_video_generator_test_module_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _build_effect_params(effect_name: str, params: dict | None = None) -> dict:
    effect_params_module = _load_module(EFFECT_PARAMS_PATH)
    return effect_params_module.build_effect_params(effect_name, params or {})


class _FakeUniform:
    def __init__(self):
        self._value = None
        self.values = []

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        self._value = new_value
        self.values.append(new_value)


class _FakeProgram:
    def __init__(self, available_uniforms: set[str] | None = None, strict_missing: bool = False):
        self.uniforms = {
            "u_image": _FakeUniform(),
            "u_time": _FakeUniform(),
            "u_resolution": _FakeUniform(),
        }
        if available_uniforms:
            for uniform_name in available_uniforms:
                if uniform_name not in self.uniforms:
                    self.uniforms[uniform_name] = _FakeUniform()
        self.strict_missing = strict_missing
        self.released = False

    def __getitem__(self, key):
        if key not in self.uniforms:
            if self.strict_missing:
                raise KeyError(key)
            self.uniforms[key] = _FakeUniform()
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
    def __init__(self, available_uniforms: set[str] | None = None, strict_missing: bool = False):
        self.released = False
        self.program_object = None
        self.framebuffer_object = None
        self.buffer_object = None
        self.vertex_array_object = None
        self.texture_objects = []
        self.available_uniforms = available_uniforms
        self.strict_missing = strict_missing

    def program(self, *, vertex_shader, fragment_shader):
        self.vertex_shader = vertex_shader
        self.fragment_shader = fragment_shader
        self.program_object = _FakeProgram(
            available_uniforms=self.available_uniforms,
            strict_missing=self.strict_missing,
        )
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

    def __init__(self, available_uniforms: set[str] | None = None, strict_missing: bool = False):
        self.create_calls = 0
        self.latest_context = None
        self.available_uniforms = available_uniforms
        self.strict_missing = strict_missing

    def create_standalone_context(self, **_kwargs):
        self.create_calls += 1
        self.latest_context = _FakeContext(
            available_uniforms=self.available_uniforms,
            strict_missing=self.strict_missing,
        )
        return self.latest_context


def test_effect_params_payload_connects_to_video_generator_effect_input(monkeypatch):
    video_module = _load_module(NODE_PATH)
    fake_moderngl = _FakeModerngl()
    monkeypatch.setitem(sys.modules, "moderngl", fake_moderngl)
    monkeypatch.setattr(video_module, "load_shader", lambda _name: "shader-source")
    monkeypatch.setattr(video_module, "load_vertex_shader", lambda _name: "vertex-source")

    generator = video_module.CoolVideoGenerator()
    image = torch.ones((1, 2, 2, 3), dtype=torch.float32)
    effect_params = _build_effect_params("vhs")
    output, = generator.execute(image=image, effect_params=effect_params, fps=1, duration=1.0)

    assert video_module.CoolVideoGenerator.INPUT_TYPES()["required"]["effect_params"] == ("EFFECT_PARAMS",)
    assert "effect_name" not in video_module.CoolVideoGenerator.INPUT_TYPES()["required"]
    assert effect_params["effect_name"] == "vhs"
    assert output.shape == (1, 2, 2, 3)


def test_video_generator_uses_standalone_context_and_frame_time(monkeypatch):
    module = _load_module(NODE_PATH)
    fake_moderngl = _FakeModerngl()
    monkeypatch.setitem(sys.modules, "moderngl", fake_moderngl)
    monkeypatch.setattr(module, "load_shader", lambda _name: "shader-source")
    monkeypatch.setattr(module, "load_vertex_shader", lambda _name: "vertex-source")

    node = module.CoolVideoGenerator()
    image = torch.ones((1, 2, 3, 3), dtype=torch.float32)

    output, = node.execute(image=image, effect_params=_build_effect_params("glitch"), fps=4, duration=1.0)

    assert fake_moderngl.create_calls == 1
    assert fake_moderngl.latest_context.vertex_shader == "vertex-source"
    assert fake_moderngl.latest_context.fragment_shader == "shader-source"
    assert fake_moderngl.latest_context.vertex_array_object.rendered_times == [0.0, 0.25, 0.5, 0.75]
    assert output.shape == (4, 2, 3, 3)


def test_video_generator_has_no_inline_glsl_constant():
    module = _load_module(NODE_PATH)
    assert not hasattr(module, "_VERTEX_SHADER_SOURCE")


def test_video_generator_input_types_expose_fps_and_duration_widgets():
    module = _load_module(NODE_PATH)

    input_types = module.CoolVideoGenerator.INPUT_TYPES()
    required_inputs = input_types["required"]

    assert required_inputs["image"] == ("IMAGE",)
    assert required_inputs["effect_params"] == ("EFFECT_PARAMS",)
    assert "effect_name" not in required_inputs
    assert required_inputs["fps"] == ("INT", {"default": 30, "min": 1, "max": 60})
    assert required_inputs["duration"] == (
        "FLOAT",
        {"default": 3.0, "min": 0.5, "max": 60.0, "step": 0.5},
    )


def test_video_generator_execute_signature_accepts_effect_params():
    module = _load_module(NODE_PATH)
    execute_parameters = list(inspect.signature(module.CoolVideoGenerator.execute).parameters)
    assert execute_parameters == ["self", "image", "effect_params", "fps", "duration"]


def test_video_generator_rounds_total_frames_from_duration_times_fps(monkeypatch):
    module = _load_module(NODE_PATH)
    fake_moderngl = _FakeModerngl()
    monkeypatch.setitem(sys.modules, "moderngl", fake_moderngl)
    monkeypatch.setattr(module, "load_shader", lambda _name: "shader-source")

    node = module.CoolVideoGenerator()
    image = torch.ones((1, 2, 3, 3), dtype=torch.float32)
    output, = node.execute(image=image, effect_params=_build_effect_params("glitch"), fps=3, duration=0.5)

    assert output.shape[0] == round(0.5 * 3)
    assert fake_moderngl.latest_context.vertex_array_object.rendered_times == [0.0, 1.0 / 3.0]


def test_video_generator_backward_compatible_output_tensor_shape_dtype_and_range(monkeypatch):
    module = _load_module(NODE_PATH)
    fake_moderngl = _FakeModerngl()
    monkeypatch.setitem(sys.modules, "moderngl", fake_moderngl)
    monkeypatch.setattr(module, "load_shader", lambda _name: "shader-source")

    node = module.CoolVideoGenerator()
    image = torch.ones((1, 2, 3, 3), dtype=torch.float32)
    output, = node.execute(image=image, effect_params=_build_effect_params("glitch"), fps=5, duration=0.6)

    assert output.shape == (3, 2, 3, 3)
    assert output.dtype == torch.float32
    assert output.min().item() >= 0.0
    assert output.max().item() <= 1.0


def test_video_generator_backward_compatible_single_image_tensor_shapes(monkeypatch):
    module = _load_module(NODE_PATH)
    fake_moderngl = _FakeModerngl()
    monkeypatch.setitem(sys.modules, "moderngl", fake_moderngl)
    monkeypatch.setattr(module, "load_shader", lambda _name: "shader-source")
    monkeypatch.setattr(module, "load_vertex_shader", lambda _name: "vertex-source")

    node = module.CoolVideoGenerator()
    single_image = torch.rand((2, 3, 3), dtype=torch.float32)
    batched_single_image = single_image.unsqueeze(0)
    effect_params = _build_effect_params("glitch")

    output_from_single, = node.execute(
        image=single_image, effect_params=effect_params, fps=3, duration=1.0
    )
    output_from_batch, = node.execute(
        image=batched_single_image, effect_params=effect_params, fps=3, duration=1.0
    )

    assert output_from_single.shape == (3, 2, 3, 3)
    assert output_from_batch.shape == (3, 2, 3, 3)
    assert torch.equal(output_from_single, output_from_batch)


def test_video_generator_backward_compatible_frame_count_uses_round(monkeypatch):
    module = _load_module(NODE_PATH)
    fake_moderngl = _FakeModerngl()
    monkeypatch.setitem(sys.modules, "moderngl", fake_moderngl)
    monkeypatch.setattr(module, "load_shader", lambda _name: "shader-source")

    node = module.CoolVideoGenerator()
    image = torch.ones((1, 2, 3, 3), dtype=torch.float32)
    output, = node.execute(image=image, effect_params=_build_effect_params("glitch"), fps=3, duration=0.55)

    assert output.shape[0] == round(0.55 * 3)
    assert output.shape[0] == 2
    assert fake_moderngl.latest_context.vertex_array_object.rendered_times == [0.0, 1.0 / 3.0]


def test_video_generator_backward_compatible_fps_and_duration_input_definitions():
    module = _load_module(NODE_PATH)
    required_inputs = module.CoolVideoGenerator.INPUT_TYPES()["required"]

    assert required_inputs["fps"] == ("INT", {"default": 30, "min": 1, "max": 60})
    assert required_inputs["duration"] == (
        "FLOAT",
        {"default": 3.0, "min": 0.5, "max": 60.0, "step": 0.5},
    )


def test_video_generator_reads_rgb_bytes_per_frame(monkeypatch):
    module = _load_module(NODE_PATH)
    fake_moderngl = _FakeModerngl()
    monkeypatch.setitem(sys.modules, "moderngl", fake_moderngl)
    monkeypatch.setattr(module, "load_shader", lambda _name: "shader-source")

    node = module.CoolVideoGenerator()
    image = torch.ones((1, 2, 3, 3), dtype=torch.float32)
    node.execute(image=image, effect_params=_build_effect_params("glitch"), fps=3, duration=1.0)

    framebuffer = fake_moderngl.latest_context.framebuffer_object
    assert framebuffer.read_components == [3, 3, 3]


def test_video_generator_returns_float32_image_batch_tensor(monkeypatch):
    module = _load_module(NODE_PATH)
    fake_moderngl = _FakeModerngl()
    monkeypatch.setitem(sys.modules, "moderngl", fake_moderngl)
    monkeypatch.setattr(module, "load_shader", lambda _name: "shader-source")

    node = module.CoolVideoGenerator()
    image = torch.ones((1, 2, 3, 3), dtype=torch.float32)
    output, = node.execute(image=image, effect_params=_build_effect_params("glitch"), fps=2, duration=1.0)

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
    result = node.execute(image=image, effect_params=_build_effect_params("glitch"), fps=1, duration=1.0)

    assert module.CoolVideoGenerator.RETURN_TYPES == ("IMAGE",)
    assert isinstance(result, tuple)
    assert len(result) == 1
    assert isinstance(result[0], torch.Tensor)


def test_video_generator_category_is_cool_effects():
    module = _load_module(NODE_PATH)

    assert module.CoolVideoGenerator.CATEGORY == "CoolEffects"


def test_video_generator_outputs_90_frames_for_3s_at_30fps(monkeypatch):
    module = _load_module(NODE_PATH)
    fake_moderngl = _FakeModerngl()
    monkeypatch.setitem(sys.modules, "moderngl", fake_moderngl)
    monkeypatch.setattr(module, "load_shader", lambda _name: "shader-source")

    node = module.CoolVideoGenerator()
    image = torch.ones((1, 4, 5, 3), dtype=torch.float32)
    output, = node.execute(image=image, effect_params=_build_effect_params("glitch"), fps=30, duration=3.0)

    assert output.shape == (90, 4, 5, 3)


def test_video_generator_renders_512_square_90_frames_under_30_seconds(monkeypatch):
    module = _load_module(NODE_PATH)
    fake_moderngl = _FakeModerngl()
    monkeypatch.setitem(sys.modules, "moderngl", fake_moderngl)
    monkeypatch.setattr(module, "load_shader", lambda _name: "shader-source")

    node = module.CoolVideoGenerator()
    image = torch.ones((1, 512, 512, 3), dtype=torch.float32)

    start = time.perf_counter()
    output, = node.execute(image=image, effect_params=_build_effect_params("glitch"), fps=30, duration=3.0)
    elapsed = time.perf_counter() - start

    assert output.shape == (90, 512, 512, 3)
    assert elapsed < 30.0


def test_video_generator_output_is_preview_image_compatible(monkeypatch):
    module = _load_module(NODE_PATH)
    fake_moderngl = _FakeModerngl()
    monkeypatch.setitem(sys.modules, "moderngl", fake_moderngl)
    monkeypatch.setattr(module, "load_shader", lambda _name: "shader-source")

    node = module.CoolVideoGenerator()
    image = torch.ones((1, 2, 2, 3), dtype=torch.float32)
    output, = node.execute(image=image, effect_params=_build_effect_params("glitch"), fps=3, duration=1.0)

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
    node.execute(image=image, effect_params=_build_effect_params("glitch"), fps=1, duration=1.0)

    context = fake_moderngl.latest_context
    input_texture = context.texture_objects[0]
    program = context.program_object

    assert input_texture.used_locations == [0]
    assert program["u_image"].value == 0
    assert program["u_resolution"].value == (3, 2)


def test_video_generator_sets_effect_uniforms_each_frame_as_floats(monkeypatch):
    module = _load_module(NODE_PATH)
    fake_moderngl = _FakeModerngl(
        available_uniforms={"u_wave_freq", "u_wave_amp", "u_speed"},
        strict_missing=True,
    )
    monkeypatch.setitem(sys.modules, "moderngl", fake_moderngl)
    monkeypatch.setattr(module, "load_shader", lambda _name: "shader-source")

    node = module.CoolVideoGenerator()
    image = torch.ones((1, 2, 3, 3), dtype=torch.float32)
    effect_params = _build_effect_params(
        "glitch",
        {"u_wave_freq": 9, "u_wave_amp": 1, "u_speed": 3},
    )
    node.execute(image=image, effect_params=effect_params, fps=3, duration=1.0)

    program = fake_moderngl.latest_context.program_object
    assert program["u_wave_freq"].values == [9.0, 9.0, 9.0]
    assert program["u_wave_amp"].values == [1.0, 1.0, 1.0]
    assert program["u_speed"].values == [3.0, 3.0, 3.0]


def test_video_generator_skips_missing_effect_uniforms_without_error(monkeypatch):
    module = _load_module(NODE_PATH)
    fake_moderngl = _FakeModerngl(
        available_uniforms={"u_wave_freq"},
        strict_missing=True,
    )
    monkeypatch.setitem(sys.modules, "moderngl", fake_moderngl)
    monkeypatch.setattr(module, "load_shader", lambda _name: "shader-source")

    node = module.CoolVideoGenerator()
    image = torch.ones((1, 2, 3, 3), dtype=torch.float32)
    effect_params = _build_effect_params(
        "glitch",
        {"u_not_real": 5},
    )
    node.execute(image=image, effect_params=effect_params, fps=2, duration=1.0)

    program = fake_moderngl.latest_context.program_object
    assert program["u_wave_freq"].values == [120.0, 120.0]
    assert "u_not_real" not in program.uniforms


def test_video_generator_sets_base_uniforms_independently_from_effect_params(monkeypatch):
    module = _load_module(NODE_PATH)
    fake_moderngl = _FakeModerngl()
    monkeypatch.setitem(sys.modules, "moderngl", fake_moderngl)
    monkeypatch.setattr(module, "load_shader", lambda _name: "shader-source")

    node = module.CoolVideoGenerator()
    image = torch.ones((1, 2, 3, 3), dtype=torch.float32)
    effect_params = _build_effect_params(
        "glitch",
        {"u_wave_freq": 15},
    )
    node.execute(image=image, effect_params=effect_params, fps=3, duration=1.0)

    program = fake_moderngl.latest_context.program_object
    assert program["u_image"].values == [0]
    assert program["u_resolution"].values == [(3, 2)]
    assert program["u_time"].values == [0.0, 1.0 / 3.0, 2.0 / 3.0]


def test_video_generator_uses_default_uniforms_when_effect_params_are_empty(monkeypatch):
    module = _load_module(NODE_PATH)
    fake_moderngl = _FakeModerngl()
    monkeypatch.setitem(sys.modules, "moderngl", fake_moderngl)
    monkeypatch.setattr(module, "load_shader", lambda _name: "shader-source")

    node = module.CoolVideoGenerator()
    image = torch.ones((1, 2, 3, 3), dtype=torch.float32)
    effect_params = _build_effect_params("glitch", {})
    node.execute(image=image, effect_params=effect_params, fps=1, duration=1.0)

    program = fake_moderngl.latest_context.program_object
    assert program["u_wave_freq"].value == 120.0
    assert program["u_wave_amp"].value == 0.0025
    assert program["u_speed"].value == 10.0


def test_video_generator_raises_value_error_for_unknown_effect_params_effect(monkeypatch):
    module = _load_module(NODE_PATH)
    fake_moderngl = _FakeModerngl()
    monkeypatch.setitem(sys.modules, "moderngl", fake_moderngl)
    monkeypatch.setattr(module, "load_shader", lambda _name: "shader-source")

    node = module.CoolVideoGenerator()
    image = torch.ones((1, 2, 2, 3), dtype=torch.float32)

    with pytest.raises(ValueError, match="Unknown effect.*unknown_effect"):
        node.execute(
            image=image,
            effect_params=_build_effect_params("unknown_effect"),
            fps=1,
            duration=1.0,
        )


def test_video_generator_raises_value_error_when_shader_missing(monkeypatch):
    module = _load_module(NODE_PATH)
    monkeypatch.setattr(module, "load_shader", lambda _name: (_ for _ in ()).throw(FileNotFoundError("glitch")))

    node = module.CoolVideoGenerator()
    image = torch.ones((1, 2, 2, 3), dtype=torch.float32)

    with pytest.raises(ValueError, match="effect_name 'glitch'"):
        node.execute(
            image=image,
            effect_params=_build_effect_params("glitch"),
            fps=1,
            duration=1.0,
        )


def test_video_generator_releases_gl_resources(monkeypatch):
    module = _load_module(NODE_PATH)
    fake_moderngl = _FakeModerngl()
    monkeypatch.setitem(sys.modules, "moderngl", fake_moderngl)
    monkeypatch.setattr(module, "load_shader", lambda _name: "shader-source")

    node = module.CoolVideoGenerator()
    image = torch.ones((1, 2, 2, 3), dtype=torch.float32)
    node.execute(image=image, effect_params=_build_effect_params("glitch"), fps=1, duration=1.0)

    context = fake_moderngl.latest_context
    assert context.program_object.released is True
    assert context.framebuffer_object.released is True
    assert context.buffer_object.released is True
    assert context.vertex_array_object.released is True
    assert all(texture.released for texture in context.texture_objects)
    assert context.released is True


def test_package_registers_cool_video_generator_node():
    package_module = _load_module(PACKAGE_INIT)

    assert "CoolVideoGenerator" in package_module.NODE_CLASS_MAPPINGS
    assert package_module.NODE_DISPLAY_NAME_MAPPINGS["CoolVideoGenerator"] == "Cool Video Generator"
