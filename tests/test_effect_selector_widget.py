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
