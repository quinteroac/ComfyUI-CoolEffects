import json
import subprocess
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent.parent
WIDGET_PATH = PACKAGE_ROOT / "web" / "video_player.js"
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


def test_video_player_widget_renders_canvas_inside_node_body():
    script = f"""
import {{ register_comfy_extension, EXTENSION_NAME }} from "{WIDGET_URL}";

class FakeElement {{
    constructor(tagName) {{
        this.tagName = tagName;
        this.children = [];
        this.attributes = {{}};
        this.listeners = {{}};
        this.style = {{}};
        this.textContent = "";
        this.width = 320;
        this.height = 180;
    }}
    appendChild(child) {{
        this.children.push(child);
        return child;
    }}
    setAttribute(name, value) {{
        this.attributes[name] = value;
    }}
    addEventListener(name, listener) {{
        this.listeners[name] = listener;
    }}
    click() {{
        if (typeof this.listeners.click === "function") {{
            this.listeners.click({{ currentTarget: this }});
        }}
    }}
}}

class FakeCanvasElement extends FakeElement {{
    constructor() {{
        super("canvas");
    }}
    getContext(kind) {{
        if (kind !== "2d") {{
            return null;
        }}
        return {{ drawImage() {{}} }};
    }}
}}

class FakeVideoElement extends FakeElement {{
    constructor() {{
        super("video");
        this.readyState = 0;
        this.videoWidth = 0;
        this.videoHeight = 0;
        this.src = "";
    }}
    play() {{
        return Promise.resolve();
    }}
    pause() {{}}
    load() {{}}
}}

const document_ref = {{
    createElement(tagName) {{
        if (tagName === "canvas") {{
            return new FakeCanvasElement();
        }}
        if (tagName === "video") {{
            return new FakeVideoElement();
        }}
        return new FakeElement(tagName);
    }},
}};

const api_ref = {{
    addEventListener() {{}},
    removeEventListener() {{}},
}};
let captured_extension = null;
const app_ref = {{
    api: api_ref,
    registerExtension(extension) {{
        captured_extension = extension;
    }},
}};

register_comfy_extension(app_ref, {{
    document_ref,
    api_ref,
    request_animation_frame: () => 1,
    cancel_animation_frame: () => {{}},
}});

function NodeType() {{
    this.id = 7;
    this.dom_widgets = [];
}}
NodeType.prototype.addDOMWidget = function addDOMWidget(_name, _type, element) {{
    this.dom_widgets.push({{ element }});
    return {{ element }};
}};

await captured_extension.beforeRegisterNodeDef(NodeType, {{ name: "CoolVideoPlayer" }});
const node = new NodeType();
await node.onNodeCreated();

const container = node.dom_widgets[0].element;
const controls = container.children[1];
const playButton = controls.children[0];
console.log(JSON.stringify({{
    extensionName: captured_extension.name,
    expectedName: EXTENSION_NAME,
    childTags: container.children.map((child) => child.tagName),
    buttonText: playButton.textContent,
    buttonPressed: playButton.attributes["aria-pressed"],
}}));
"""
    output = _run_node_module(script)
    assert output["extensionName"] == output["expectedName"]
    assert output["childTags"][0] == "canvas"
    assert output["childTags"][1] == "div"
    assert output["buttonText"] == "Play"
    assert output["buttonPressed"] == "false"


def test_video_player_widget_play_pause_controls_drive_looping_preview():
    script = f"""
import {{ register_comfy_extension }} from "{WIDGET_URL}";

const raf_callbacks = new Map();
let next_raf_id = 1;
let cancelled_animation_handles = 0;

function run_next_frame() {{
    const first = raf_callbacks.entries().next().value;
    if (!first) {{
        return false;
    }}
    const [handle, callback] = first;
    raf_callbacks.delete(handle);
    callback();
    return true;
}}

class FakeElement {{
    constructor(tagName) {{
        this.tagName = tagName;
        this.children = [];
        this.attributes = {{}};
        this.listeners = {{}};
        this.style = {{}};
        this.textContent = "";
        this.width = 320;
        this.height = 180;
    }}
    appendChild(child) {{
        this.children.push(child);
        return child;
    }}
    setAttribute(name, value) {{
        this.attributes[name] = value;
    }}
    addEventListener(name, listener) {{
        this.listeners[name] = listener;
    }}
    click() {{
        if (typeof this.listeners.click === "function") {{
            this.listeners.click({{ currentTarget: this }});
        }}
    }}
}}

class FakeCanvasElement extends FakeElement {{
    constructor() {{
        super("canvas");
        this.draw_calls = 0;
    }}
    getContext(kind) {{
        if (kind !== "2d") {{
            return null;
        }}
        return {{
            drawImage: () => {{
                this.draw_calls += 1;
            }},
        }};
    }}
}}

class FakeVideoElement extends FakeElement {{
    constructor() {{
        super("video");
        this.readyState = 0;
        this.videoWidth = 0;
        this.videoHeight = 0;
        this.src = "";
        this.play_calls = 0;
        this.pause_calls = 0;
        this.loop = false;
    }}
    play() {{
        this.play_calls += 1;
        return Promise.resolve();
    }}
    pause() {{
        this.pause_calls += 1;
    }}
    load() {{}}
}}

const document_ref = {{
    createElement(tagName) {{
        if (tagName === "canvas") {{
            return new FakeCanvasElement();
        }}
        if (tagName === "video") {{
            return new FakeVideoElement();
        }}
        return new FakeElement(tagName);
    }},
}};

const listeners = {{}};
const api_ref = {{
    addEventListener(name, listener) {{
        listeners[name] = listener;
    }},
    removeEventListener() {{}},
}};
let captured_extension = null;
const app_ref = {{
    api: api_ref,
    registerExtension(extension) {{
        captured_extension = extension;
    }},
}};

register_comfy_extension(app_ref, {{
    document_ref,
    api_ref,
    request_animation_frame: (callback) => {{
        const handle = next_raf_id;
        next_raf_id += 1;
        raf_callbacks.set(handle, callback);
        return handle;
    }},
    cancel_animation_frame: (handle) => {{
        cancelled_animation_handles += 1;
        raf_callbacks.delete(handle);
    }},
}});

function NodeType() {{
    this.id = 41;
    this.dom_widgets = [];
}}
NodeType.prototype.addDOMWidget = function addDOMWidget(_name, _type, element) {{
    this.dom_widgets.push({{ element }});
    return {{ element }};
}};

await captured_extension.beforeRegisterNodeDef(NodeType, {{ name: "CoolVideoPlayer" }});
const node = new NodeType();
await node.onNodeCreated();

listeners.executed({{
    detail: {{
        node: 41,
        output: {{
            video_entries: [{{ source_url: "https://example.com/video.mp4" }}],
        }},
    }},
}});
await Promise.resolve();

const state = node.__cool_video_player_widget_state;
const play_button = state.toggle_button_element;

play_button.click();
await Promise.resolve();
const queuedAfterPlay = raf_callbacks.size;

state.video_element.readyState = 3;
state.video_element.videoWidth = 640;
state.video_element.videoHeight = 360;
run_next_frame();
const queuedAfterFirstFrame = raf_callbacks.size;

play_button.click();
const queuedAfterPause = raf_callbacks.size;

console.log(JSON.stringify({{
    videoSrc: state.video_element.src,
    playCalls: state.video_element.play_calls,
    pauseCalls: state.video_element.pause_calls,
    videoLoop: state.video_element.loop,
    drawCalls: state.canvas_element.draw_calls,
    canvasWidth: state.canvas_element.width,
    canvasHeight: state.canvas_element.height,
    buttonText: state.toggle_button_element.textContent,
    queuedAfterPlay,
    queuedAfterFirstFrame,
    queuedAfterPause,
    cancelledAnimationHandles: cancelled_animation_handles,
    statusText: state.status_element.textContent,
}}));
"""
    output = _run_node_module(script)
    assert output["videoSrc"] == "https://example.com/video.mp4"
    assert output["playCalls"] == 1
    assert output["pauseCalls"] >= 1
    assert output["videoLoop"] is True
    assert output["drawCalls"] >= 1
    assert output["canvasWidth"] == 640
    assert output["canvasHeight"] == 360
    assert output["buttonText"] == "Play"
    assert output["queuedAfterPlay"] == 1
    assert output["queuedAfterFirstFrame"] == 1
    assert output["queuedAfterPause"] == 0
    assert output["cancelledAnimationHandles"] >= 1
    assert output["statusText"] == "Paused on current frame."
