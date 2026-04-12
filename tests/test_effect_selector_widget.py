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
    hasError: Boolean(preview_state.preview_error),
    uImage: controller.preview_descriptor.uniforms.u_image,
}}));
"""
    output = _run_node_module(script)
    assert output["background"] == "rgb(128, 128, 128)"
    assert output["hasError"] is False
    assert output["uImage"] is None


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
