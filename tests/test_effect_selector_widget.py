import json
import subprocess
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent.parent
WIDGET_PATH = PACKAGE_ROOT / "web" / "effect_selector.js"
WIDGET_URL = WIDGET_PATH.resolve().as_uri()


def _run_node_module(script: str) -> dict:
    command = ["node", "--input-type=module", "-e", script]
    completed = subprocess.run(
        command,
        cwd=PACKAGE_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def test_widget_renders_select_with_all_shaders():
    script = f"""
import {{ initialize_effect_dropdown }} from "{WIDGET_URL}";

class FakeElement {{
    constructor(tagName) {{
        this.tagName = tagName;
        this.children = [];
        this.listeners = {{}};
        this.attributes = {{}};
        this.value = "";
        this.textContent = "";
    }}
    appendChild(child) {{
        this.children.push(child);
        return child;
    }}
    addEventListener(name, listener) {{
        this.listeners[name] = listener;
    }}
    setAttribute(name, value) {{
        this.attributes[name] = value;
    }}
    dispatchEvent(name) {{
        if (this.listeners[name]) {{
            this.listeners[name]();
        }}
    }}
}}

const document_ref = {{
    createElement(tagName) {{
        return new FakeElement(tagName);
    }},
}};

const container_element = new FakeElement("div");
const preview_state = {{}};
const {{ select_element, shader_names }} = await initialize_effect_dropdown({{
    document_ref,
    container_element,
    preview_state,
    shader_names_loader: async () => ["glitch", "vhs", "zoom_pulse"],
    now: () => 0,
}});

console.log(JSON.stringify({{
    tagName: select_element.tagName,
    shaderNames: shader_names,
    options: select_element.children.map((child) => child.value),
}}));
"""
    output = _run_node_module(script)
    assert output["tagName"] == "select"
    assert output["shaderNames"] == ["glitch", "vhs", "zoom_pulse"]
    assert output["options"] == ["glitch", "vhs", "zoom_pulse"]


def test_dropdown_change_updates_preview_quickly_without_reload():
    script = f"""
import {{ initialize_effect_dropdown }} from "{WIDGET_URL}";

class FakeElement {{
    constructor(tagName) {{
        this.tagName = tagName;
        this.children = [];
        this.listeners = {{}};
        this.attributes = {{}};
        this.value = "";
        this.textContent = "";
    }}
    appendChild(child) {{
        this.children.push(child);
        return child;
    }}
    addEventListener(name, listener) {{
        this.listeners[name] = listener;
    }}
    setAttribute(name, value) {{
        this.attributes[name] = value;
    }}
    dispatchEvent(name) {{
        if (this.listeners[name]) {{
            this.listeners[name]();
        }}
    }}
}}

const now_values = [100, 160, 200, 240];
const now = () => now_values.shift();
const document_ref = {{
    createElement(tagName) {{
        return new FakeElement(tagName);
    }},
}};
const container_element = new FakeElement("div");
const preview_state = {{}};
let emitted_effect_name = "";
let reload_calls = 0;
globalThis.location = {{
    reload() {{
        reload_calls += 1;
    }},
}};

const {{ select_element }} = await initialize_effect_dropdown({{
    document_ref,
    container_element,
    preview_state,
    on_effect_selected: (name) => {{
        emitted_effect_name = name;
    }},
    shader_names_loader: async () => ["glitch", "vhs"],
    now,
}});

select_element.value = "vhs";
select_element.dispatchEvent("change");

console.log(JSON.stringify({{
    selectedEffect: preview_state.effect_name,
    updateMs: preview_state.last_preview_update_ms,
    emittedEffectName: emitted_effect_name,
    reloadCalls: reload_calls,
}}));
"""
    output = _run_node_module(script)
    assert output["selectedEffect"] == "vhs"
    assert output["updateMs"] <= 100
    assert output["emittedEffectName"] == "vhs"
    assert output["reloadCalls"] == 0


def test_live_preview_contains_r3f_canvas_plane_and_input_texture():
    script = f"""
import {{ create_live_glsl_preview }} from "{WIDGET_URL}";

class FakeElement {{
    constructor(tagName) {{
        this.tagName = tagName;
        this.children = [];
        this.listeners = {{}};
        this.attributes = {{}};
        this.value = "";
        this.textContent = "";
        this.width = 512;
        this.height = 512;
        this.clientWidth = 512;
        this.clientHeight = 512;
        this.style = {{}};
    }}
    appendChild(child) {{
        this.children.push(child);
        return child;
    }}
    addEventListener(name, listener) {{
        this.listeners[name] = listener;
    }}
    setAttribute(name, value) {{
        this.attributes[name] = value;
    }}
}}

const document_ref = {{
    createElement(tagName) {{
        return new FakeElement(tagName);
    }},
}};
const container_element = new FakeElement("div");
const preview_state = {{}};
const input_image = "image-texture";

class FakeVector2 {{
    constructor(x, y) {{
        this.x = x;
        this.y = y;
    }}
    set(x, y) {{
        this.x = x;
        this.y = y;
    }}
}}

class FakeShaderMaterial {{
    constructor(config) {{
        this.uniforms = config.uniforms;
        this.vertexShader = config.vertexShader;
        this.fragmentShader = config.fragmentShader;
        this.needsUpdate = false;
    }}
    dispose() {{
        this.disposed = true;
    }}
}}

const controller = await create_live_glsl_preview({{
    document_ref,
    container_element,
    effect_name: "glitch",
    input_image,
    preview_state,
    shader_loader: async () => "void main() {{}}",
    three_stack_loader: async () => ({{
        THREE: {{
            ShaderMaterial: FakeShaderMaterial,
            Vector2: FakeVector2,
        }},
        react_three_fiber: {{
            createRoot: () => ({{ render: () => {{}}, unmount: () => {{}} }}),
        }},
        react_three_drei: {{
            Plane: () => null,
        }},
    }}),
    request_animation_frame: () => 1,
}});

console.log(JSON.stringify({{
    containerChildren: container_element.children.length,
    canvasTag: controller.canvas_element.tagName,
    renderer: controller.preview_descriptor.renderer,
    mesh: controller.preview_descriptor.mesh,
    uImage: controller.preview_descriptor.uniforms.u_image,
    hasThreeCanvas: controller.preview_descriptor.three_canvas,
    hasShaderMaterial: Boolean(controller.preview_descriptor.shader_material),
}}));
"""
    output = _run_node_module(script)
    assert output["containerChildren"] == 1
    assert output["canvasTag"] == "canvas"
    assert output["renderer"] == "r3f"
    assert output["mesh"] == "plane"
    assert output["uImage"] == "image-texture"
    assert output["hasThreeCanvas"] is True
    assert output["hasShaderMaterial"] is True


def test_live_preview_animates_u_time_with_raf_loop():
    script = f"""
import {{ create_live_glsl_preview }} from "{WIDGET_URL}";

class FakeElement {{
    constructor(tagName) {{
        this.tagName = tagName;
        this.children = [];
        this.attributes = {{}};
        this.textContent = "";
        this.width = 512;
        this.height = 512;
        this.clientWidth = 512;
        this.clientHeight = 512;
        this.style = {{}};
    }}
    appendChild(child) {{
        this.children.push(child);
        return child;
    }}
    setAttribute(name, value) {{
        this.attributes[name] = value;
    }}
}}

const document_ref = {{
    createElement(tagName) {{
        return new FakeElement(tagName);
    }},
}};
const container_element = new FakeElement("div");
const now_values = [0, 500, 1250];
const now = () => now_values.shift();
const raf_callbacks = [];

const controller = await create_live_glsl_preview({{
    document_ref,
    container_element,
    effect_name: "glitch",
    now,
    shader_loader: async () => "void main() {{}}",
    request_animation_frame: (callback) => {{
        raf_callbacks.push(callback);
        return raf_callbacks.length;
    }},
    cancel_animation_frame: () => {{}},
}});

raf_callbacks.shift()();
raf_callbacks.shift()();

console.log(JSON.stringify({{
    callbackCount: raf_callbacks.length,
    uTime: controller.preview_descriptor.uniforms.u_time,
}}));
"""
    output = _run_node_module(script)
    assert output["callbackCount"] == 1
    assert abs(output["uTime"] - 1.25) < 1e-9


def test_live_preview_updates_u_resolution_on_resize():
    script = f"""
import {{ create_live_glsl_preview }} from "{WIDGET_URL}";

class FakeElement {{
    constructor(tagName) {{
        this.tagName = tagName;
        this.children = [];
        this.attributes = {{}};
        this.textContent = "";
        this.width = 512;
        this.height = 512;
        this.clientWidth = 512;
        this.clientHeight = 512;
        this.style = {{}};
    }}
    appendChild(child) {{
        this.children.push(child);
        return child;
    }}
    setAttribute(name, value) {{
        this.attributes[name] = value;
    }}
}}

const document_ref = {{
    createElement(tagName) {{
        return new FakeElement(tagName);
    }},
}};
const container_element = new FakeElement("div");

const controller = await create_live_glsl_preview({{
    document_ref,
    container_element,
    effect_name: "glitch",
    shader_loader: async () => "void main() {{}}",
    request_animation_frame: () => 1,
}});

controller.resize(640, 360);

console.log(JSON.stringify({{
    resolution: controller.preview_descriptor.uniforms.u_resolution,
}}));
"""
    output = _run_node_module(script)
    assert output["resolution"] == [640, 360]


def test_live_preview_without_input_shows_grey_placeholder_without_errors():
    script = f"""
import {{ create_live_glsl_preview }} from "{WIDGET_URL}";

class FakeElement {{
    constructor(tagName) {{
        this.tagName = tagName;
        this.children = [];
        this.attributes = {{}};
        this.textContent = "";
        this.width = 512;
        this.height = 512;
        this.clientWidth = 512;
        this.clientHeight = 512;
        this.style = {{}};
    }}
    appendChild(child) {{
        this.children.push(child);
        return child;
    }}
    setAttribute(name, value) {{
        this.attributes[name] = value;
    }}
}}

const document_ref = {{
    createElement(tagName) {{
        return new FakeElement(tagName);
    }},
}};
const container_element = new FakeElement("div");
const preview_state = {{}};

const controller = await create_live_glsl_preview({{
    document_ref,
    container_element,
    effect_name: "glitch",
    input_image: null,
    preview_state,
    shader_loader: async () => "void main() {{}}",
    request_animation_frame: () => 1,
}});

console.log(JSON.stringify({{
    background: controller.canvas_element.style.background,
    overlayText: controller.overlay_element.textContent,
    hasError: Boolean(preview_state.preview_error),
    uImage: controller.preview_descriptor.uniforms.u_image,
}}));
"""
    output = _run_node_module(script)
    assert output["background"] == "rgb(128, 128, 128)"
    assert output["overlayText"] == ""
    assert output["hasError"] is False
    assert output["uImage"] is None


def test_mount_widget_initializes_preview_with_js_placeholder_texture():
    script = f"""
import {{ mount_effect_selector_widget_for_node }} from "{WIDGET_URL}";

class FakeElement {{
    constructor(tagName) {{
        this.tagName = tagName;
        this.children = [];
        this.listeners = {{}};
        this.attributes = {{}};
        this.value = "";
        this.textContent = "";
        this.width = 512;
        this.height = 512;
        this.clientWidth = 512;
        this.clientHeight = 512;
        this.style = {{}};
    }}
    appendChild(child) {{
        this.children.push(child);
        return child;
    }}
    addEventListener(name, listener) {{
        this.listeners[name] = listener;
    }}
    setAttribute(name, value) {{
        this.attributes[name] = value;
    }}
    getContext(kind) {{
        if (this.tagName !== "canvas" || kind !== "2d") {{
            return null;
        }}
        return {{
            fillStyle: "",
            strokeStyle: "",
            lineWidth: 1,
            createLinearGradient() {{
                return {{ addColorStop() {{}} }};
            }},
            fillRect() {{}},
            beginPath() {{}},
            moveTo() {{}},
            lineTo() {{}},
            stroke() {{}},
        }};
    }}
}}

const document_ref = {{
    createElement(tagName) {{
        return new FakeElement(tagName);
    }},
}};

let fetch_called = false;
globalThis.fetch = async () => {{
    fetch_called = true;
    throw new Error("unexpected fetch");
}};

const node = {{
    widgets: [{{ name: "effect_name", value: "" }}],
    properties: {{}},
    addDOMWidget(_name, _type, element) {{
        this.container = element;
        return {{ element }};
    }},
    setDirtyCanvas() {{}},
}};

const widget_state = await mount_effect_selector_widget_for_node({{
    node,
    document_ref,
    shader_names_loader: async () => ["glitch", "vhs"],
    shader_loader: async (name) => `shader-${{name}}`,
    request_animation_frame: () => 1,
}});

const controller = widget_state.preview_state.preview_controller;
console.log(JSON.stringify({{
    placeholderTag: controller.preview_descriptor.uniforms.u_image?.tagName ?? null,
    overlayText: controller.overlay_element.textContent,
    canvasBackground: controller.canvas_element.style.background,
    fetchCalled: fetch_called,
}}));
"""
    output = _run_node_module(script)
    assert output["placeholderTag"] == "canvas"
    assert output["overlayText"] == ""
    assert output["canvasBackground"] == "transparent"
    assert output["fetchCalled"] is False


def test_switching_effect_keeps_placeholder_texture_instance():
    script = f"""
import {{ create_live_glsl_preview }} from "{WIDGET_URL}";

class FakeElement {{
    constructor(tagName) {{
        this.tagName = tagName;
        this.children = [];
        this.attributes = {{}};
        this.textContent = "";
        this.width = 512;
        this.height = 512;
        this.clientWidth = 512;
        this.clientHeight = 512;
        this.style = {{}};
    }}
    appendChild(child) {{
        this.children.push(child);
        return child;
    }}
    setAttribute(name, value) {{
        this.attributes[name] = value;
    }}
}}

const document_ref = {{
    createElement(tagName) {{
        return new FakeElement(tagName);
    }},
}};
const container_element = new FakeElement("div");
const placeholder_texture = {{ type: "placeholder" }};
const shader_calls = [];
const controller = await create_live_glsl_preview({{
    document_ref,
    container_element,
    effect_name: "glitch",
    input_image: placeholder_texture,
    shader_loader: async (name) => {{
        shader_calls.push(name);
        return `shader-${{name}}`;
    }},
    request_animation_frame: () => 1,
}});

const image_before = controller.preview_descriptor.uniforms.u_image;
await controller.set_effect("vhs");
const image_after = controller.preview_descriptor.uniforms.u_image;

console.log(JSON.stringify({{
    shaderCalls: shader_calls,
    effectName: controller.preview_descriptor.effect_name,
    fragmentShaderSource: controller.preview_descriptor.fragment_shader_source,
    sameTexture: image_before === image_after,
}}));
"""
    output = _run_node_module(script)
    assert output["shaderCalls"] == ["glitch", "vhs"]
    assert output["effectName"] == "vhs"
    assert output["fragmentShaderSource"] == "shader-vhs"
    assert output["sameTexture"] is True


def test_live_preview_uses_default_js_load_shader_for_effect_source():
    script = f"""
import {{ create_live_glsl_preview }} from "{WIDGET_URL}";

class FakeElement {{
    constructor(tagName) {{
        this.tagName = tagName;
        this.children = [];
        this.attributes = {{}};
        this.textContent = "";
        this.width = 512;
        this.height = 512;
        this.clientWidth = 512;
        this.clientHeight = 512;
        this.style = {{}};
    }}
    appendChild(child) {{
        this.children.push(child);
        return child;
    }}
    setAttribute(name, value) {{
        this.attributes[name] = value;
    }}
}}

let requested_url = "";
globalThis.fetch = async (url) => {{
    requested_url = String(url);
    return {{
        ok: true,
        status: 200,
        async text() {{
            return "shader-source";
        }},
    }};
}};

const document_ref = {{
    createElement(tagName) {{
        return new FakeElement(tagName);
    }},
}};
const container_element = new FakeElement("div");

const controller = await create_live_glsl_preview({{
    document_ref,
    container_element,
    effect_name: "vhs",
    input_image: "image-texture",
    request_animation_frame: () => 1,
}});

console.log(JSON.stringify({{
    requestedUrl: requested_url,
    fragmentShaderSource: controller.preview_descriptor.fragment_shader_source,
}}));
"""
    output = _run_node_module(script)
    assert output["requestedUrl"].endswith("/shaders/glsl/vhs.frag")
    assert output["fragmentShaderSource"] == "shader-source"


def test_live_preview_shows_inline_error_when_shader_load_fails():
    script = f"""
import {{ create_live_glsl_preview }} from "{WIDGET_URL}";

class FakeElement {{
    constructor(tagName) {{
        this.tagName = tagName;
        this.children = [];
        this.attributes = {{}};
        this.textContent = "";
        this.width = 512;
        this.height = 512;
        this.clientWidth = 512;
        this.clientHeight = 512;
        this.style = {{}};
    }}
    appendChild(child) {{
        this.children.push(child);
        return child;
    }}
    setAttribute(name, value) {{
        this.attributes[name] = value;
    }}
}}

globalThis.fetch = async () => ({{
    ok: false,
    status: 404,
}});

const document_ref = {{
    createElement(tagName) {{
        return new FakeElement(tagName);
    }},
}};
const container_element = new FakeElement("div");
const preview_state = {{}};

const controller = await create_live_glsl_preview({{
    document_ref,
    container_element,
    effect_name: "missing_effect",
    input_image: null,
    preview_state,
    request_animation_frame: () => 1,
}});

console.log(JSON.stringify({{
    inlineError: controller.overlay_element.textContent,
    previewError: preview_state.preview_error,
}}));
"""
    output = _run_node_module(script)
    assert output["inlineError"] == "Shader load error: Shader not found: missing_effect"
    assert output["previewError"] == "Shader load error: Shader not found: missing_effect"


def test_live_preview_overlay_uses_aria_live_status_semantics():
    script = f"""
import {{ create_live_glsl_preview }} from "{WIDGET_URL}";

class FakeElement {{
    constructor(tagName) {{
        this.tagName = tagName;
        this.children = [];
        this.attributes = {{}};
        this.textContent = "";
        this.width = 512;
        this.height = 512;
        this.clientWidth = 512;
        this.clientHeight = 512;
        this.style = {{}};
    }}
    appendChild(child) {{
        this.children.push(child);
        return child;
    }}
    setAttribute(name, value) {{
        this.attributes[name] = value;
    }}
}}

const document_ref = {{
    createElement(tagName) {{
        return new FakeElement(tagName);
    }},
}};
const container_element = new FakeElement("div");
const controller = await create_live_glsl_preview({{
    document_ref,
    container_element,
    effect_name: "glitch",
    shader_loader: async () => "void main() {{}}",
    request_animation_frame: () => 1,
}});

console.log(JSON.stringify({{
    ariaLive: controller.overlay_element.attributes["aria-live"],
    role: controller.overlay_element.attributes.role,
}}));
"""
    output = _run_node_module(script)
    assert output["ariaLive"] == "polite"
    assert output["role"] == "status"


def test_live_preview_uses_single_global_resize_listener():
    script = f"""
import {{ create_live_glsl_preview }} from "{WIDGET_URL}";

class FakeElement {{
    constructor(tagName) {{
        this.tagName = tagName;
        this.children = [];
        this.attributes = {{}};
        this.textContent = "";
        this.width = 512;
        this.height = 512;
        this.clientWidth = 512;
        this.clientHeight = 512;
        this.style = {{}};
    }}
    appendChild(child) {{
        this.children.push(child);
        return child;
    }}
    setAttribute(name, value) {{
        this.attributes[name] = value;
    }}
}}

let add_count = 0;
let remove_count = 0;
globalThis.addEventListener = () => {{
    add_count += 1;
}};
globalThis.removeEventListener = () => {{
    remove_count += 1;
}};

const document_ref = {{
    createElement(tagName) {{
        return new FakeElement(tagName);
    }},
}};
const container_element = new FakeElement("div");
const first = await create_live_glsl_preview({{
    document_ref,
    container_element,
    effect_name: "glitch",
    shader_loader: async () => "void main() {{}}",
    request_animation_frame: () => 1,
}});
const second = await create_live_glsl_preview({{
    document_ref,
    container_element,
    effect_name: "vhs",
    shader_loader: async () => "void main() {{}}",
    request_animation_frame: () => 1,
}});

first.stop();
second.stop();

console.log(JSON.stringify({{
    addCount: add_count,
    removeCount: remove_count,
}}));
"""
    output = _run_node_module(script)
    assert output["addCount"] == 1
    assert output["removeCount"] == 1


def test_registers_comfy_extension_and_propagates_widget_selection_to_effect_output():
    script = f"""
import {{ register_comfy_extension, EXTENSION_NAME }} from "{WIDGET_URL}";

class FakeElement {{
    constructor(tagName) {{
        this.tagName = tagName;
        this.children = [];
        this.listeners = {{}};
        this.attributes = {{}};
        this.value = "";
        this.textContent = "";
        this.width = 512;
        this.height = 512;
        this.clientWidth = 512;
        this.clientHeight = 512;
        this.style = {{}};
    }}
    appendChild(child) {{
        this.children.push(child);
        return child;
    }}
    addEventListener(name, listener) {{
        this.listeners[name] = listener;
    }}
    setAttribute(name, value) {{
        this.attributes[name] = value;
    }}
    dispatchEvent(name) {{
        if (this.listeners[name]) {{
            this.listeners[name]();
        }}
    }}
}}

const document_ref = {{
    createElement(tagName) {{
        return new FakeElement(tagName);
    }},
}};

let captured_extension = null;
const app_ref = {{
    registerExtension(extension) {{
        captured_extension = extension;
    }},
}};

register_comfy_extension(app_ref, {{
    document_ref,
    shader_names_loader: async () => ["glitch", "vhs"],
    shader_loader: async () => "void main() {{}}",
    request_animation_frame: () => 1,
}});

function NodeType() {{
    this.widgets = [{{ name: "effect_name", value: "glitch" }}];
    this.properties = {{}};
    this.dirty_calls = 0;
    this.dom_widgets = [];
}}

NodeType.prototype.addDOMWidget = function addDOMWidget(_name, _type, element) {{
    this.dom_widgets.push({{ element }});
    return {{ element }};
}};

NodeType.prototype.setDirtyCanvas = function setDirtyCanvas() {{
    this.dirty_calls += 1;
}};

await captured_extension.beforeRegisterNodeDef(NodeType, {{ name: "CoolEffectSelector" }});
const node = new NodeType();
await node.onNodeCreated();

const container = node.dom_widgets[0].element;
const select_element = container.children[0];
select_element.value = "vhs";
select_element.dispatchEvent("change");
await Promise.resolve();

console.log(JSON.stringify({{
    extensionName: captured_extension.name,
    expectedName: EXTENSION_NAME,
    selectedEffect: node.widgets[0].value,
    propertyEffect: node.properties.effect_name,
    dirtyCalls: node.dirty_calls,
}}));
"""
    output = _run_node_module(script)
    assert output["extensionName"] == output["expectedName"]
    assert output["selectedEffect"] == "vhs"
    assert output["propertyEffect"] == "vhs"
    assert output["dirtyCalls"] >= 1


def test_webgl2_renderer_exposes_set_uniform_and_existing_methods():
    script = f"""
import {{ create_webgl2_renderer }} from "{WIDGET_URL}";

class FakeGL {{
    constructor() {{
        this.ARRAY_BUFFER = 34962;
        this.STATIC_DRAW = 35044;
        this.VERTEX_SHADER = 35633;
        this.FRAGMENT_SHADER = 35632;
        this.COMPILE_STATUS = 35713;
        this.LINK_STATUS = 35714;
        this.TEXTURE_2D = 3553;
        this.RGBA = 6408;
        this.UNSIGNED_BYTE = 5121;
        this.TEXTURE_MIN_FILTER = 10241;
        this.LINEAR_MIPMAP_LINEAR = 9987;
        this.TEXTURE_WRAP_S = 10242;
        this.TEXTURE_WRAP_T = 10243;
        this.CLAMP_TO_EDGE = 33071;
        this.TEXTURE0 = 33984;
        this.FLOAT = 5126;
        this.TRIANGLE_STRIP = 5;
        this.drawCount = 0;
    }}
    createBuffer() {{ return {{ kind: "buffer" }}; }}
    bindBuffer() {{}}
    bufferData() {{}}
    createShader(type) {{ return {{ type }}; }}
    shaderSource() {{}}
    compileShader() {{}}
    getShaderParameter() {{ return true; }}
    getShaderInfoLog() {{ return ""; }}
    deleteShader() {{}}
    createProgram() {{ return {{ kind: "program" }}; }}
    attachShader() {{}}
    linkProgram() {{}}
    getProgramParameter() {{ return true; }}
    getProgramInfoLog() {{ return ""; }}
    deleteProgram() {{}}
    useProgram() {{}}
    getAttribLocation() {{ return 0; }}
    getUniformLocation(_program, name) {{
        return {{ name }};
    }}
    createTexture() {{ return {{ kind: "texture" }}; }}
    deleteTexture() {{}}
    bindTexture() {{}}
    texImage2D() {{}}
    generateMipmap() {{}}
    texParameteri() {{}}
    viewport() {{}}
    enableVertexAttribArray() {{}}
    vertexAttribPointer() {{}}
    uniform1f() {{}}
    uniform2f() {{}}
    activeTexture() {{}}
    uniform1i() {{}}
    drawArrays() {{
        this.drawCount += 1;
    }}
    deleteBuffer() {{}}
}}

const canvas_element = {{
    width: 256,
    height: 256,
    getContext(kind) {{
        if (kind === "webgl2") return new FakeGL();
        return null;
    }},
}};
const renderer = create_webgl2_renderer(canvas_element);
renderer.set_fragment_shader("out vec4 fragColor; void main() {{ fragColor = vec4(1.0); }}");
renderer.set_image_texture({{ tagName: "img" }});
renderer.render(1.5);
renderer.dispose();
console.log(JSON.stringify({{
    hasSetUniform: typeof renderer.set_uniform === "function",
    hasSetFragmentShader: typeof renderer.set_fragment_shader === "function",
    hasSetImageTexture: typeof renderer.set_image_texture === "function",
    hasRender: typeof renderer.render === "function",
    hasDispose: typeof renderer.dispose === "function",
    drawCount: renderer.gl.drawCount,
}}));
"""
    output = _run_node_module(script)
    assert output["hasSetUniform"] is True
    assert output["hasSetFragmentShader"] is True
    assert output["hasSetImageTexture"] is True
    assert output["hasRender"] is True
    assert output["hasDispose"] is True
    assert output["drawCount"] == 1


def test_webgl2_renderer_set_uniform_updates_existing_uniform_only():
    script = f"""
import {{ create_webgl2_renderer }} from "{WIDGET_URL}";

class FakeGL {{
    constructor() {{
        this.ARRAY_BUFFER = 34962;
        this.STATIC_DRAW = 35044;
        this.VERTEX_SHADER = 35633;
        this.FRAGMENT_SHADER = 35632;
        this.COMPILE_STATUS = 35713;
        this.LINK_STATUS = 35714;
        this.TEXTURE_2D = 3553;
        this.RGBA = 6408;
        this.UNSIGNED_BYTE = 5121;
        this.TEXTURE_MIN_FILTER = 10241;
        this.LINEAR_MIPMAP_LINEAR = 9987;
        this.TEXTURE_WRAP_S = 10242;
        this.TEXTURE_WRAP_T = 10243;
        this.CLAMP_TO_EDGE = 33071;
        this.TEXTURE0 = 33984;
        this.FLOAT = 5126;
        this.TRIANGLE_STRIP = 5;
        this.uniformCalls = [];
        this.uniformLookups = [];
    }}
    createBuffer() {{ return {{ kind: "buffer" }}; }}
    bindBuffer() {{}}
    bufferData() {{}}
    createShader(type) {{ return {{ type }}; }}
    shaderSource() {{}}
    compileShader() {{}}
    getShaderParameter() {{ return true; }}
    getShaderInfoLog() {{ return ""; }}
    deleteShader() {{}}
    createProgram() {{ return {{ kind: "program" }}; }}
    attachShader() {{}}
    linkProgram() {{}}
    getProgramParameter() {{ return true; }}
    getProgramInfoLog() {{ return ""; }}
    deleteProgram() {{}}
    useProgram() {{}}
    getAttribLocation() {{ return 0; }}
    getUniformLocation(_program, name) {{
        this.uniformLookups.push(name);
        if (name === "u_speed") return {{ name }};
        return null;
    }}
    createTexture() {{ return {{ kind: "texture" }}; }}
    deleteTexture() {{}}
    bindTexture() {{}}
    texImage2D() {{}}
    generateMipmap() {{}}
    texParameteri() {{}}
    viewport() {{}}
    enableVertexAttribArray() {{}}
    vertexAttribPointer() {{}}
    uniform1f(location, value) {{
        this.uniformCalls.push({{ location: location.name, value }});
    }}
    uniform2f() {{}}
    activeTexture() {{}}
    uniform1i() {{}}
    drawArrays() {{}}
    deleteBuffer() {{}}
}}

const canvas_element = {{
    width: 256,
    height: 256,
    getContext(kind) {{
        if (kind === "webgl2") return new FakeGL();
        return null;
    }},
}};
const renderer = create_webgl2_renderer(canvas_element);
renderer.set_uniform("u_speed", 2.25);
renderer.set_uniform("u_missing", 3.5);
console.log(JSON.stringify({{
    uniformLookups: renderer.gl.uniformLookups,
    uniformCalls: renderer.gl.uniformCalls,
}}));
"""
    output = _run_node_module(script)
    assert output["uniformLookups"][-2:] == ["u_speed", "u_missing"]
    assert output["uniformCalls"] == [{"location": "u_speed", "value": 2.25}]


def test_webgl2_renderer_set_uniform_does_not_throw_when_program_is_null():
    script = f"""
import {{ create_webgl2_renderer }} from "{WIDGET_URL}";

class FakeGL {{
    constructor() {{
        this.ARRAY_BUFFER = 34962;
        this.STATIC_DRAW = 35044;
        this.VERTEX_SHADER = 35633;
        this.FRAGMENT_SHADER = 35632;
        this.COMPILE_STATUS = 35713;
        this.LINK_STATUS = 35714;
        this.TEXTURE_2D = 3553;
        this.RGBA = 6408;
        this.UNSIGNED_BYTE = 5121;
        this.TEXTURE_MIN_FILTER = 10241;
        this.LINEAR_MIPMAP_LINEAR = 9987;
        this.TEXTURE_WRAP_S = 10242;
        this.TEXTURE_WRAP_T = 10243;
        this.CLAMP_TO_EDGE = 33071;
        this.TEXTURE0 = 33984;
        this.FLOAT = 5126;
        this.TRIANGLE_STRIP = 5;
    }}
    createBuffer() {{ return {{ kind: "buffer" }}; }}
    bindBuffer() {{}}
    bufferData() {{}}
    createShader(type) {{ return {{ type }}; }}
    shaderSource() {{}}
    compileShader() {{}}
    getShaderParameter() {{ return true; }}
    getShaderInfoLog() {{ return ""; }}
    deleteShader() {{}}
    createProgram() {{ return null; }}
    attachShader() {{}}
    linkProgram() {{}}
    getProgramParameter() {{ return true; }}
    getProgramInfoLog() {{ return ""; }}
    deleteProgram() {{}}
    useProgram() {{}}
    getAttribLocation() {{ return -1; }}
    getUniformLocation() {{ return null; }}
    createTexture() {{ return {{ kind: "texture" }}; }}
    deleteTexture() {{}}
    bindTexture() {{}}
    texImage2D() {{}}
    generateMipmap() {{}}
    texParameteri() {{}}
    viewport() {{}}
    enableVertexAttribArray() {{}}
    vertexAttribPointer() {{}}
    uniform1f() {{}}
    uniform2f() {{}}
    activeTexture() {{}}
    uniform1i() {{}}
    drawArrays() {{}}
    deleteBuffer() {{}}
}}

const canvas_element = {{
    width: 256,
    height: 256,
    getContext(kind) {{
        if (kind === "webgl2") return new FakeGL();
        return null;
    }},
}};
const renderer = create_webgl2_renderer(canvas_element);
let threw = false;
try {{
    renderer.set_uniform("u_speed", 1.0);
}} catch (_error) {{
    threw = true;
}}
console.log(JSON.stringify({{ threw }}));
"""
    output = _run_node_module(script)
    assert output["threw"] is False
