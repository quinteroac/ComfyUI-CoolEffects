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
const controller = await create_live_glsl_preview({{
    document_ref,
    container_element,
    effect_name: "glitch",
    input_image,
    preview_state,
    shader_loader: async () => "void main() {{}}",
    request_animation_frame: () => 1,
}});

console.log(JSON.stringify({{
    containerChildren: container_element.children.length,
    canvasTag: controller.canvas_element.tagName,
    renderer: controller.preview_descriptor.renderer,
    mesh: controller.preview_descriptor.mesh,
    uImage: controller.preview_descriptor.uniforms.u_image,
    hasThreeCanvas: controller.preview_descriptor.three_canvas,
}}));
"""
    output = _run_node_module(script)
    assert output["containerChildren"] == 1
    assert output["canvasTag"] == "canvas"
    assert output["renderer"] == "r3f"
    assert output["mesh"] == "plane"
    assert output["uImage"] == "image-texture"
    assert output["hasThreeCanvas"] is True


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
