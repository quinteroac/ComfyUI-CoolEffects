import json
import subprocess
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent.parent
WIDGET_PATH = PACKAGE_ROOT / "web" / "water_drops_effect.js"
WIDGET_URL = WIDGET_PATH.resolve().as_uri()


def _run_node_module(script: str) -> dict:
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=PACKAGE_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def test_mount_water_drops_widget_creates_canvas_and_uses_water_drops_shader_source():
    script = f"""
import {{ mount_water_drops_effect_widget_for_node }} from "{WIDGET_URL}";

class FakeElement {{
    constructor(tagName) {{
        this.tagName = tagName;
        this.children = [];
        this.attributes = {{}};
        this.width = 512;
        this.height = 512;
        this.clientWidth = 512;
        this.clientHeight = 512;
        this.textContent = "";
        this.style = {{}};
    }}
    appendChild(child) {{
        this.children.push(child);
        return child;
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

const shader_calls = [];
const raf_callbacks = [];
let now_ms = 0;
const node = {{
    addDOMWidget(_name, _type, element) {{
        this.container = element;
        return {{ element }};
    }},
}};

const widget_state = await mount_water_drops_effect_widget_for_node({{
    node,
    document_ref,
    shader_loader: async (name) => {{
        shader_calls.push(name);
        return "void main() {{}}";
    }},
    request_animation_frame: (callback) => {{
        raf_callbacks.push(callback);
        return raf_callbacks.length;
    }},
    now: () => now_ms,
}});

const controller = widget_state.preview_state.preview_controller;
const initial_u_time = controller.preview_descriptor.uniforms.u_time;
now_ms = 1000;
raf_callbacks.shift()?.(1000);
const updated_u_time = controller.preview_descriptor.uniforms.u_time;

console.log(JSON.stringify({{
    shaderCalls: shader_calls,
    hasCanvas: controller.canvas_element.tagName,
    placeholderTag: controller.preview_descriptor.uniforms.u_image?.tagName ?? null,
    initialUTime: initial_u_time,
    updatedUTime: updated_u_time,
    pendingAnimationCallbacks: raf_callbacks.length,
}}));
"""
    output = _run_node_module(script)
    assert output["shaderCalls"] == ["water_drops"]
    assert output["hasCanvas"] == "canvas"
    assert output["placeholderTag"] == "canvas"
    assert output["initialUTime"] == 0
    assert output["updatedUTime"] == 1
    assert output["pendingAnimationCallbacks"] >= 1


def test_registers_water_drops_extension_and_mounts_widget_on_node_create():
    script = f"""
import {{ register_comfy_extension, EXTENSION_NAME }} from "{WIDGET_URL}";

class FakeElement {{
    constructor(tagName) {{
        this.tagName = tagName;
        this.children = [];
        this.attributes = {{}};
        this.width = 512;
        this.height = 512;
        this.clientWidth = 512;
        this.clientHeight = 512;
        this.textContent = "";
        this.style = {{}};
    }}
    appendChild(child) {{
        this.children.push(child);
        return child;
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

let captured_extension = null;
const app_ref = {{
    registerExtension(extension) {{
        captured_extension = extension;
    }},
}};

register_comfy_extension(app_ref, {{
    document_ref,
    shader_loader: async () => "void main() {{}}",
    request_animation_frame: () => 1,
}});

function NodeType() {{
    this.dom_widgets = [];
}}
NodeType.prototype.addDOMWidget = function addDOMWidget(_name, _type, element) {{
    this.dom_widgets.push({{ element }});
    return {{ element }};
}};

await captured_extension.beforeRegisterNodeDef(NodeType, {{ name: "CoolWaterDropsEffect" }});
const node = new NodeType();
await node.onNodeCreated();

console.log(JSON.stringify({{
    extensionName: captured_extension.name,
    expectedName: EXTENSION_NAME,
    widgetCount: node.dom_widgets.length,
    previewEffect: node.__cool_water_drops_widget_state.preview_state.preview_descriptor.effect_name,
}}));
"""
    output = _run_node_module(script)
    assert output["extensionName"] == output["expectedName"]
    assert output["widgetCount"] == 1
    assert output["previewEffect"] == "water_drops"


def test_water_drops_widget_changes_update_primary_preview_uniforms_without_shader_reload():
    script = f"""
import {{ register_comfy_extension }} from "{WIDGET_URL}";

class FakeElement {{
    constructor(tagName) {{
        this.tagName = tagName;
        this.children = [];
        this.attributes = {{}};
        this.width = 512;
        this.height = 512;
        this.clientWidth = 512;
        this.clientHeight = 512;
        this.textContent = "";
        this.style = {{}};
    }}
    appendChild(child) {{
        this.children.push(child);
        return child;
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

let captured_extension = null;
const app_ref = {{
    registerExtension(extension) {{
        captured_extension = extension;
    }},
}};
const shader_calls = [];
register_comfy_extension(app_ref, {{
    document_ref,
    shader_loader: async (name) => {{
        shader_calls.push(name);
        return "void main() {{}}";
    }},
    request_animation_frame: () => 1,
}});

function NodeType() {{}}
NodeType.prototype.addDOMWidget = function addDOMWidget(_name, _type, element) {{
    return {{ element }};
}};

await captured_extension.beforeRegisterNodeDef(NodeType, {{ name: "CoolWaterDropsEffect" }});
const node = new NodeType();
await node.onNodeCreated();

const controller = node.__cool_water_drops_widget_state.preview_state.preview_controller;
const uniform_calls = [];
const original_set_uniform = controller.set_uniform.bind(controller);
controller.set_uniform = (uniform_name, value) => {{
    uniform_calls.push([uniform_name, value]);
    original_set_uniform(uniform_name, value);
}};

let did_throw = false;
try {{
    node.onWidgetChanged("drop_density", 120);
    node.onWidgetChanged("drop_size", 0.12);
    node.onWidgetChanged("fall_speed", 2.5);
    node.onWidgetChanged("refraction_strength", 0.48);
}} catch (_error) {{
    did_throw = true;
}}

console.log(JSON.stringify({{
    hasOnWidgetChanged: typeof node.onWidgetChanged === "function",
    didThrow: did_throw,
    shaderCalls: shader_calls,
    uniformCalls: uniform_calls,
    uniforms: controller.preview_descriptor.uniforms,
}}));
"""
    output = _run_node_module(script)
    assert output["hasOnWidgetChanged"] is True
    assert output["didThrow"] is False
    assert output["shaderCalls"] == ["water_drops"]
    assert output["uniformCalls"] == [
        ["u_drop_density", 120],
        ["u_drop_size", 0.12],
        ["u_fall_speed", 2.5],
        ["u_refraction_strength", 0.48],
    ]
    assert output["uniforms"]["u_drop_density"] == 120
    assert output["uniforms"]["u_drop_size"] == 0.12
    assert output["uniforms"]["u_fall_speed"] == 2.5
    assert output["uniforms"]["u_refraction_strength"] == 0.48
