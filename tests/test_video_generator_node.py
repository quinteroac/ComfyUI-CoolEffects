import importlib.util
import inspect
import sys
import time
import types
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


def _mock_comfy_api(monkeypatch):
    """Inject a minimal comfy_api.latest stub so execute() can be called without av/ffmpeg."""

    class _FakeVideoComponents:
        def __init__(self, images, audio, frame_rate):
            self.images = images

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
        self.uploads = []
        self.write_calls = []
        if data is not None:
            self.uploads.append(data)
        self.used_locations = []
        self.released = False

    def use(self, location):
        self.used_locations.append(location)

    def write(self, data):
        self.data = data
        self.uploads.append(data)
        self.write_calls.append(data)

    def release(self):
        self.released = True


class _FakeFramebuffer:
    def __init__(self, color_attachment):
        self.color_attachment = color_attachment
        self.released = False
        self.use_calls = 0
        self.read_components = []
        self.read_count = 0

    def use(self):
        self.use_calls += 1

    def read(self, components):
        self.read_components.append(components)
        width, height = self.color_attachment.size
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


class _FakeRenderbuffer:
    def __init__(self, size, components):
        self.size = size
        self.components = components
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
        self.renderbuffer_objects = []
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

    def renderbuffer(self, size, components):
        renderbuffer = _FakeRenderbuffer(size=size, components=components)
        self.renderbuffer_objects.append(renderbuffer)
        return renderbuffer

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
        self.contexts = []
        self.available_uniforms = available_uniforms
        self.strict_missing = strict_missing

    def create_standalone_context(self, **_kwargs):
        self.create_calls += 1
        self.latest_context = _FakeContext(
            available_uniforms=self.available_uniforms,
            strict_missing=self.strict_missing,
        )
        self.contexts.append(self.latest_context)
        return self.latest_context


# ---------------------------------------------------------------------------
# Interface / contract tests
# ---------------------------------------------------------------------------

def test_video_generator_input_types_expose_required_widgets():
    module = _load_module(NODE_PATH)
    required = module.CoolVideoGenerator.INPUT_TYPES()["required"]

    assert required["image"] == ("IMAGE",)
    assert required["fps"] == ("INT", {"default": 30, "min": 1, "max": 60})
    assert required["duration"] == ("FLOAT", {"default": 3.0, "min": 0.5, "max": 60.0, "step": 0.5})
    assert required["effect_count"][0] == "INT"
    assert "effect_name" not in required


def test_video_generator_input_types_expose_effect_params_1_as_optional():
    module = _load_module(NODE_PATH)
    optional = module.CoolVideoGenerator.INPUT_TYPES().get("optional", {})
    assert "effect_params_1" in optional
    assert optional["effect_params_1"] == ("EFFECT_PARAMS",)


def test_video_generator_execute_signature_accepts_effect_count_and_kwargs():
    module = _load_module(NODE_PATH)
    sig = inspect.signature(module.CoolVideoGenerator.execute)
    params = list(sig.parameters)
    assert "self" in params
    assert "image" in params
    assert "fps" in params
    assert "duration" in params
    assert "effect_count" in params
    # **kwargs carries effect_params_2, effect_params_3, etc.
    assert any(
        p.kind == inspect.Parameter.VAR_KEYWORD
        for p in sig.parameters.values()
    ), "execute must accept **kwargs"


def test_video_generator_category_is_cool_effects():
    module = _load_module(NODE_PATH)
    assert module.CoolVideoGenerator.CATEGORY == "CoolEffects"


# ---------------------------------------------------------------------------
# Single-effect execution (effect_params_1 via kwargs)
# ---------------------------------------------------------------------------

def test_effect_params_1_connects_and_renders_frames(monkeypatch):
    module = _load_module(NODE_PATH)
    _mock_comfy_api(monkeypatch)
    fake_moderngl = _FakeModerngl()
    monkeypatch.setitem(sys.modules, "moderngl", fake_moderngl)
    monkeypatch.setattr(module, "load_shader", lambda _name: "shader-source")
    monkeypatch.setattr(module, "load_vertex_shader", lambda _name: "vertex-source")

    node = module.CoolVideoGenerator()
    image = torch.ones((1, 2, 2, 3), dtype=torch.float32)
    ep = _build_effect_params("vhs")
    result = node.execute(image=image, fps=1, duration=1.0, effect_count=1, effect_params_1=ep)

    assert "result" in result
    assert result["result"][0].images.shape[0] == 1  # 1 fps × 1 s


def test_video_generator_uses_standalone_context_and_frame_time(monkeypatch):
    module = _load_module(NODE_PATH)
    _mock_comfy_api(monkeypatch)
    fake_moderngl = _FakeModerngl()
    monkeypatch.setitem(sys.modules, "moderngl", fake_moderngl)
    monkeypatch.setattr(module, "load_shader", lambda _name: "shader-source")
    monkeypatch.setattr(module, "load_vertex_shader", lambda _name: "vertex-source")

    node = module.CoolVideoGenerator()
    image = torch.ones((1, 2, 3, 3), dtype=torch.float32)
    ep = _build_effect_params("glitch")
    node.execute(image=image, fps=4, duration=1.0, effect_count=1, effect_params_1=ep)

    assert fake_moderngl.create_calls == 1
    assert fake_moderngl.latest_context.vertex_shader == "vertex-source"
    assert fake_moderngl.latest_context.fragment_shader == "shader-source"
    assert fake_moderngl.latest_context.vertex_array_object.rendered_times == [0.0, 0.25, 0.5, 0.75]


def test_video_generator_rounds_total_frames_from_duration_times_fps(monkeypatch):
    module = _load_module(NODE_PATH)
    _mock_comfy_api(monkeypatch)
    fake_moderngl = _FakeModerngl()
    monkeypatch.setitem(sys.modules, "moderngl", fake_moderngl)
    monkeypatch.setattr(module, "load_shader", lambda _name: "shader-source")

    node = module.CoolVideoGenerator()
    image = torch.ones((1, 2, 3, 3), dtype=torch.float32)
    ep = _build_effect_params("glitch")
    result = node.execute(image=image, fps=3, duration=0.5, effect_count=1, effect_params_1=ep)

    assert result["result"][0].images.shape[0] == round(0.5 * 3)
    assert fake_moderngl.latest_context.vertex_array_object.rendered_times == [0.0, 1.0 / 3.0]


def test_video_generator_reads_rgb_bytes_per_frame(monkeypatch):
    module = _load_module(NODE_PATH)
    _mock_comfy_api(monkeypatch)
    fake_moderngl = _FakeModerngl()
    monkeypatch.setitem(sys.modules, "moderngl", fake_moderngl)
    monkeypatch.setattr(module, "load_shader", lambda _name: "shader-source")

    node = module.CoolVideoGenerator()
    image = torch.ones((1, 2, 3, 3), dtype=torch.float32)
    ep = _build_effect_params("glitch")
    node.execute(image=image, fps=3, duration=1.0, effect_count=1, effect_params_1=ep)

    framebuffer = fake_moderngl.latest_context.framebuffer_object
    assert framebuffer.read_components == [3, 3, 3]


def test_video_generator_releases_gl_resources(monkeypatch):
    module = _load_module(NODE_PATH)
    _mock_comfy_api(monkeypatch)
    fake_moderngl = _FakeModerngl()
    monkeypatch.setitem(sys.modules, "moderngl", fake_moderngl)
    monkeypatch.setattr(module, "load_shader", lambda _name: "shader-source")

    node = module.CoolVideoGenerator()
    image = torch.ones((1, 2, 2, 3), dtype=torch.float32)
    ep = _build_effect_params("glitch")
    node.execute(image=image, fps=1, duration=1.0, effect_count=1, effect_params_1=ep)

    ctx = fake_moderngl.latest_context
    assert ctx.program_object.released is True
    assert ctx.framebuffer_object.released is True
    assert ctx.buffer_object.released is True
    assert ctx.vertex_array_object.released is True
    assert all(t.released for t in ctx.texture_objects)
    assert all(r.released for r in ctx.renderbuffer_objects)
    assert ctx.released is True


def test_video_generator_uses_default_uniforms_when_effect_params_are_empty(monkeypatch):
    module = _load_module(NODE_PATH)
    _mock_comfy_api(monkeypatch)
    fake_moderngl = _FakeModerngl()
    monkeypatch.setitem(sys.modules, "moderngl", fake_moderngl)
    monkeypatch.setattr(module, "load_shader", lambda _name: "shader-source")

    node = module.CoolVideoGenerator()
    image = torch.ones((1, 2, 3, 3), dtype=torch.float32)
    ep = _build_effect_params("glitch", {})
    node.execute(image=image, fps=1, duration=1.0, effect_count=1, effect_params_1=ep)

    program = fake_moderngl.latest_context.program_object
    assert program["u_wave_freq"].value == 120.0
    assert program["u_wave_amp"].value == 0.0025
    assert program["u_speed"].value == 10.0


def test_video_generator_sets_effect_uniforms_each_frame_as_floats(monkeypatch):
    module = _load_module(NODE_PATH)
    _mock_comfy_api(monkeypatch)
    fake_moderngl = _FakeModerngl(
        available_uniforms={"u_wave_freq", "u_wave_amp", "u_speed"},
        strict_missing=True,
    )
    monkeypatch.setitem(sys.modules, "moderngl", fake_moderngl)
    monkeypatch.setattr(module, "load_shader", lambda _name: "shader-source")

    node = module.CoolVideoGenerator()
    image = torch.ones((1, 2, 3, 3), dtype=torch.float32)
    ep = _build_effect_params("glitch", {"u_wave_freq": 9, "u_wave_amp": 1, "u_speed": 3})
    node.execute(image=image, fps=3, duration=1.0, effect_count=1, effect_params_1=ep)

    program = fake_moderngl.latest_context.program_object
    assert program["u_wave_freq"].values == [9.0, 9.0, 9.0]
    assert program["u_wave_amp"].values == [1.0, 1.0, 1.0]
    assert program["u_speed"].values == [3.0, 3.0, 3.0]


def test_video_generator_skips_missing_effect_uniforms_without_error(monkeypatch):
    module = _load_module(NODE_PATH)
    _mock_comfy_api(monkeypatch)
    fake_moderngl = _FakeModerngl(available_uniforms={"u_wave_freq"}, strict_missing=True)
    monkeypatch.setitem(sys.modules, "moderngl", fake_moderngl)
    monkeypatch.setattr(module, "load_shader", lambda _name: "shader-source")

    node = module.CoolVideoGenerator()
    image = torch.ones((1, 2, 3, 3), dtype=torch.float32)
    ep = _build_effect_params("glitch", {"u_not_real": 5})
    node.execute(image=image, fps=2, duration=1.0, effect_count=1, effect_params_1=ep)

    program = fake_moderngl.latest_context.program_object
    assert program["u_wave_freq"].values == [120.0, 120.0]
    assert "u_not_real" not in program.uniforms


def test_video_generator_raises_value_error_for_unknown_effect(monkeypatch):
    module = _load_module(NODE_PATH)
    _mock_comfy_api(monkeypatch)
    fake_moderngl = _FakeModerngl()
    monkeypatch.setitem(sys.modules, "moderngl", fake_moderngl)
    monkeypatch.setattr(module, "load_shader", lambda _name: "shader-source")

    node = module.CoolVideoGenerator()
    image = torch.ones((1, 2, 2, 3), dtype=torch.float32)
    ep = _build_effect_params("unknown_effect")

    with pytest.raises(ValueError, match="Unknown effect.*unknown_effect"):
        node.execute(image=image, fps=1, duration=1.0, effect_count=1, effect_params_1=ep)


def test_video_generator_raises_value_error_when_shader_missing(monkeypatch):
    module = _load_module(NODE_PATH)
    _mock_comfy_api(monkeypatch)
    monkeypatch.setattr(module, "load_shader", lambda _name: (_ for _ in ()).throw(FileNotFoundError("glitch")))

    node = module.CoolVideoGenerator()
    image = torch.ones((1, 2, 2, 3), dtype=torch.float32)
    ep = _build_effect_params("glitch")

    with pytest.raises(ValueError, match="effect_name 'glitch'"):
        node.execute(image=image, fps=1, duration=1.0, effect_count=1, effect_params_1=ep)


def test_video_generator_outputs_90_frames_for_3s_at_30fps(monkeypatch):
    module = _load_module(NODE_PATH)
    _mock_comfy_api(monkeypatch)
    fake_moderngl = _FakeModerngl()
    monkeypatch.setitem(sys.modules, "moderngl", fake_moderngl)
    monkeypatch.setattr(module, "load_shader", lambda _name: "shader-source")

    node = module.CoolVideoGenerator()
    image = torch.ones((1, 4, 5, 3), dtype=torch.float32)
    ep = _build_effect_params("glitch")
    result = node.execute(image=image, fps=30, duration=3.0, effect_count=1, effect_params_1=ep)

    assert result["result"][0].images.shape == (90, 4, 5, 3)


def test_video_generator_no_effect_repeats_frames_to_fill_duration(monkeypatch):
    module = _load_module(NODE_PATH)
    _mock_comfy_api(monkeypatch)

    node = module.CoolVideoGenerator()
    image = torch.rand((2, 4, 4, 3), dtype=torch.float32)
    result = node.execute(image=image, fps=5, duration=1.0, effect_count=1)

    assert result["result"][0].images.shape[0] == 5


# ---------------------------------------------------------------------------
# Multi-effect chaining
# ---------------------------------------------------------------------------

def test_video_generator_chains_two_effects_sequentially(monkeypatch):
    """Two effects are applied in sequence: the output of pass 1 is input to pass 2."""
    module = _load_module(NODE_PATH)
    _mock_comfy_api(monkeypatch)
    fake_moderngl = _FakeModerngl()
    monkeypatch.setitem(sys.modules, "moderngl", fake_moderngl)
    monkeypatch.setattr(module, "load_shader", lambda _name: "shader-source")
    monkeypatch.setattr(module, "load_vertex_shader", lambda _name: "vertex-source")

    node = module.CoolVideoGenerator()
    image = torch.ones((1, 2, 2, 3), dtype=torch.float32)
    ep1 = _build_effect_params("glitch")
    ep2 = _build_effect_params("vhs")

    result = node.execute(
        image=image,
        fps=2,
        duration=1.0,
        effect_count=2,
        effect_params_1=ep1,
        effect_params_2=ep2,
    )

    # Two effects × 2 fps × 1 s = 2 GL contexts created
    assert fake_moderngl.create_calls == 2
    assert result["result"][0].images.shape == (2, 2, 2, 3)


def test_video_generator_accepts_water_drops_effect_name_without_exception(monkeypatch):
    module = _load_module(NODE_PATH)
    _mock_comfy_api(monkeypatch)
    fake_moderngl = _FakeModerngl()
    monkeypatch.setitem(sys.modules, "moderngl", fake_moderngl)

    node = module.CoolVideoGenerator()
    image = torch.ones((1, 2, 2, 3), dtype=torch.float32)
    ep = _build_effect_params("water_drops")

    result = node.execute(image=image, fps=2, duration=1.0, effect_count=1, effect_params_1=ep)

    assert result["result"][0].images.shape == (2, 2, 2, 3)
    water_program = fake_moderngl.contexts[0].program_object
    assert water_program["u_drop_density"].values == [60.0, 60.0]


def test_video_generator_accepts_frosted_glass_effect_name_without_exception(monkeypatch):
    module = _load_module(NODE_PATH)
    _mock_comfy_api(monkeypatch)
    fake_moderngl = _FakeModerngl()
    monkeypatch.setitem(sys.modules, "moderngl", fake_moderngl)

    node = module.CoolVideoGenerator()
    image = torch.ones((1, 2, 2, 3), dtype=torch.float32)
    ep = _build_effect_params("frosted_glass")

    result = node.execute(image=image, fps=2, duration=1.0, effect_count=1, effect_params_1=ep)

    assert result["result"][0].images.shape == (2, 2, 2, 3)
    frosted_program = fake_moderngl.contexts[0].program_object
    assert frosted_program["u_frost_intensity"].values == [0.5, 0.5]


@pytest.mark.parametrize("water_slot", [1, 3, 8])
def test_video_generator_accepts_water_drops_in_any_effect_params_slot(monkeypatch, water_slot):
    module = _load_module(NODE_PATH)
    _mock_comfy_api(monkeypatch)
    fake_moderngl = _FakeModerngl()
    monkeypatch.setitem(sys.modules, "moderngl", fake_moderngl)

    node = module.CoolVideoGenerator()
    image = torch.ones((1, 2, 2, 3), dtype=torch.float32)
    kwargs = {}
    for index in range(1, water_slot + 1):
        if index == water_slot:
            kwargs[f"effect_params_{index}"] = _build_effect_params("water_drops")
        else:
            kwargs[f"effect_params_{index}"] = _build_effect_params("vhs")

    result = node.execute(
        image=image,
        fps=2,
        duration=1.0,
        effect_count=water_slot,
        **kwargs,
    )

    assert result["result"][0].images.shape == (2, 2, 2, 3)
    assert fake_moderngl.create_calls == water_slot
    water_program = fake_moderngl.contexts[water_slot - 1].program_object
    assert water_program["u_drop_density"].values == [60.0, 60.0]


@pytest.mark.parametrize("frosted_slot", [1, 3, 8])
def test_video_generator_accepts_frosted_glass_in_any_effect_params_slot(monkeypatch, frosted_slot):
    module = _load_module(NODE_PATH)
    _mock_comfy_api(monkeypatch)
    fake_moderngl = _FakeModerngl()
    monkeypatch.setitem(sys.modules, "moderngl", fake_moderngl)

    node = module.CoolVideoGenerator()
    image = torch.ones((1, 2, 2, 3), dtype=torch.float32)
    kwargs = {}
    for index in range(1, frosted_slot + 1):
        if index == frosted_slot:
            kwargs[f"effect_params_{index}"] = _build_effect_params("frosted_glass")
        else:
            kwargs[f"effect_params_{index}"] = _build_effect_params("vhs")

    result = node.execute(
        image=image,
        fps=2,
        duration=1.0,
        effect_count=frosted_slot,
        **kwargs,
    )

    assert result["result"][0].images.shape == (2, 2, 2, 3)
    assert fake_moderngl.create_calls == frosted_slot
    frosted_program = fake_moderngl.contexts[frosted_slot - 1].program_object
    assert frosted_program["u_frost_intensity"].values == [0.5, 0.5]


def test_video_generator_applies_water_drops_after_vhs_on_processed_frames(monkeypatch):
    module = _load_module(NODE_PATH)
    _mock_comfy_api(monkeypatch)
    fake_moderngl = _FakeModerngl()
    monkeypatch.setitem(sys.modules, "moderngl", fake_moderngl)

    node = module.CoolVideoGenerator()
    image = torch.ones((1, 2, 2, 3), dtype=torch.float32)

    node.execute(
        image=image,
        fps=2,
        duration=1.0,
        effect_count=2,
        effect_params_1=_build_effect_params("vhs"),
        effect_params_2=_build_effect_params("water_drops"),
    )

    assert fake_moderngl.create_calls == 2
    second_pass_input = fake_moderngl.contexts[1].texture_objects[0].uploads[0]
    assert second_pass_input == bytes([0]) * len(second_pass_input)


def test_video_generator_applies_frosted_glass_after_water_drops_on_processed_frames(monkeypatch):
    module = _load_module(NODE_PATH)
    _mock_comfy_api(monkeypatch)
    fake_moderngl = _FakeModerngl()
    monkeypatch.setitem(sys.modules, "moderngl", fake_moderngl)

    node = module.CoolVideoGenerator()
    image = torch.ones((1, 2, 2, 3), dtype=torch.float32)

    node.execute(
        image=image,
        fps=2,
        duration=1.0,
        effect_count=2,
        effect_params_1=_build_effect_params("water_drops"),
        effect_params_2=_build_effect_params("frosted_glass"),
    )

    assert fake_moderngl.create_calls == 2
    second_pass_input = fake_moderngl.contexts[1].texture_objects[0].uploads[0]
    assert second_pass_input == bytes([0]) * len(second_pass_input)
    frosted_program = fake_moderngl.contexts[1].program_object
    assert frosted_program["u_frost_intensity"].values == [0.5, 0.5]


def test_video_generator_ignores_extra_effect_params_beyond_count(monkeypatch):
    """effect_params_2 is ignored when effect_count=1."""
    module = _load_module(NODE_PATH)
    _mock_comfy_api(monkeypatch)
    fake_moderngl = _FakeModerngl()
    monkeypatch.setitem(sys.modules, "moderngl", fake_moderngl)
    monkeypatch.setattr(module, "load_shader", lambda _name: "shader-source")
    monkeypatch.setattr(module, "load_vertex_shader", lambda _name: "vertex-source")

    node = module.CoolVideoGenerator()
    image = torch.ones((1, 2, 2, 3), dtype=torch.float32)
    ep1 = _build_effect_params("glitch")
    ep2 = _build_effect_params("vhs")

    node.execute(
        image=image,
        fps=1,
        duration=1.0,
        effect_count=1,
        effect_params_1=ep1,
        effect_params_2=ep2,
    )

    # Only one GL context should have been created (effect_params_2 ignored)
    assert fake_moderngl.create_calls == 1


def test_video_generator_three_effects_create_three_gl_contexts(monkeypatch):
    module = _load_module(NODE_PATH)
    _mock_comfy_api(monkeypatch)
    fake_moderngl = _FakeModerngl()
    monkeypatch.setitem(sys.modules, "moderngl", fake_moderngl)
    monkeypatch.setattr(module, "load_shader", lambda _name: "shader-source")
    monkeypatch.setattr(module, "load_vertex_shader", lambda _name: "vertex-source")

    node = module.CoolVideoGenerator()
    image = torch.ones((1, 2, 2, 3), dtype=torch.float32)

    node.execute(
        image=image,
        fps=1,
        duration=1.0,
        effect_count=3,
        effect_params_1=_build_effect_params("glitch"),
        effect_params_2=_build_effect_params("vhs"),
        effect_params_3=_build_effect_params("zoom_pulse"),
    )

    assert fake_moderngl.create_calls == 3


# ---------------------------------------------------------------------------
# Package registration
# ---------------------------------------------------------------------------

def test_package_registers_cool_video_generator_node():
    package_module = _load_module(PACKAGE_INIT)

    assert "CoolVideoGenerator" in package_module.NODE_CLASS_MAPPINGS
    assert package_module.NODE_DISPLAY_NAME_MAPPINGS["CoolVideoGenerator"] == "Cool Video Generator"
