import json
import subprocess
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent.parent
WIDGET_PATH = PACKAGE_ROOT / "web" / "vhs_effect.js"
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


def test_mount_vhs_widget_creates_live_vhs_preview_with_placeholder():
    script = f"""
import {{ mount_vhs_effect_widget_for_node }} from "{WIDGET_URL}";

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
const node = {{
    addDOMWidget(_name, _type, element) {{
        this.container = element;
        return {{ element }};
    }},
}};

const widget_state = await mount_vhs_effect_widget_for_node({{
    node,
    document_ref,
    shader_loader: async (name) => {{
        shader_calls.push(name);
        return "void main() {{}}";
    }},
    request_animation_frame: () => 1,
}});

const controller = widget_state.preview_state.preview_controller;
console.log(JSON.stringify({{
    shaderCalls: shader_calls,
    effectName: controller.preview_descriptor.effect_name,
    placeholderTag: controller.preview_descriptor.uniforms.u_image?.tagName ?? null,
    hasCanvas: controller.canvas_element.tagName,
}}));
"""
    output = _run_node_module(script)
    assert output["shaderCalls"] == ["vhs"]
    assert output["effectName"] == "vhs"
    assert output["placeholderTag"] == "canvas"
    assert output["hasCanvas"] == "canvas"


def test_registers_vhs_extension_and_mounts_widget_on_node_create():
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

await captured_extension.beforeRegisterNodeDef(NodeType, {{ name: "CoolVHSEffect" }});
const node = new NodeType();
await node.onNodeCreated();

console.log(JSON.stringify({{
    extensionName: captured_extension.name,
    expectedName: EXTENSION_NAME,
    widgetCount: node.dom_widgets.length,
    previewEffect: node.__cool_vhs_widget_state.preview_state.preview_descriptor.effect_name,
}}));
"""
    output = _run_node_module(script)
    assert output["extensionName"] == output["expectedName"]
    assert output["widgetCount"] == 1
    assert output["previewEffect"] == "vhs"


def test_vhs_widget_changes_update_preview_uniforms_without_shader_reload():
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

await captured_extension.beforeRegisterNodeDef(NodeType, {{ name: "CoolVHSEffect" }});
const node = new NodeType();
await node.onNodeCreated();

const controller = node.__cool_vhs_widget_state.preview_state.preview_controller;
const uniform_calls = [];
const original_set_uniform = controller.set_uniform.bind(controller);
controller.set_uniform = (uniform_name, value) => {{
    uniform_calls.push([uniform_name, value]);
    original_set_uniform(uniform_name, value);
}};

let did_throw = false;
try {{
    node.onWidgetChanged("scanline_intensity", 0.08);
    node.onWidgetChanged("jitter_amount", 0.0031);
    node.onWidgetChanged("chroma_shift", 0.0042);
}} catch (_error) {{
    did_throw = true;
}}

console.log(JSON.stringify({{
    hasOnWidgetChanged: typeof node.onWidgetChanged === "function",
    didThrow: did_throw,
    shaderCalls: shader_calls,
    overlayText: controller.overlay_element.textContent,
    uniformCalls: uniform_calls,
    uniforms: controller.preview_descriptor.uniforms,
}}));
"""
    output = _run_node_module(script)
    assert output["hasOnWidgetChanged"] is True
    assert output["didThrow"] is False
    assert output["shaderCalls"] == ["vhs"]
    assert output["overlayText"] == "WebGL2 not available"
    assert output["uniformCalls"] == [
        ["u_scanline_intensity", 0.08],
        ["u_jitter_amount", 0.0031],
        ["u_chroma_shift", 0.0042],
    ]
    assert output["uniforms"]["u_scanline_intensity"] == 0.08
    assert output["uniforms"]["u_jitter_amount"] == 0.0031
    assert output["uniforms"]["u_chroma_shift"] == 0.0042
