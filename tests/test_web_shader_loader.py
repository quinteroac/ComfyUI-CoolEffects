import json
import subprocess
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent.parent
WEB_LOADER_PATH = PACKAGE_ROOT / "web" / "shaders" / "loader.js"
WEB_LOADER_URL = WEB_LOADER_PATH.resolve().as_uri()


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


def test_list_shaders_fetches_endpoint_and_returns_json():
    script = f"""
import {{ listShaders }} from "{WEB_LOADER_URL}";
let requestedUrl = null;
globalThis.fetch = async (url) => {{
    requestedUrl = String(url);
    return {{
        ok: true,
        status: 200,
        async json() {{
            return ["glitch", "vhs"];
        }},
    }};
}};
const result = await listShaders();
console.log(JSON.stringify({{ requestedUrl, result }}));
"""

    output = _run_node_module(script)
    assert output["requestedUrl"] == "/cool_effects/shaders"
    assert output["result"] == ["glitch", "vhs"]


def test_list_shaders_non_200_throws_expected_error():
    script = f"""
import {{ listShaders }} from "{WEB_LOADER_URL}";
globalThis.fetch = async () => ({{
    ok: false,
    status: 503,
}});
let message = "";
try {{
    await listShaders();
}} catch (error) {{
    message = error.message;
}}
console.log(JSON.stringify({{ message }}));
"""

    output = _run_node_module(script)
    assert output["message"] == "Failed to list shaders: 503"


def test_load_shader_fetches_frag_file_and_returns_source():
    script = f"""
import {{ loadShader }} from "{WEB_LOADER_URL}";
let requestedUrl = null;
globalThis.fetch = async (url) => {{
    requestedUrl = String(url);
    return {{
        ok: true,
        status: 200,
        async text() {{
            return "void main() {{}}";
        }},
    }};
}};
const source = await loadShader("glitch");
console.log(JSON.stringify({{ requestedUrl, source }}));
"""

    output = _run_node_module(script)
    assert output["requestedUrl"].endswith("/shaders/glsl/glitch.frag")
    assert output["source"] == "void main() {}"


def test_load_shader_non_200_throws_expected_error():
    script = f"""
import {{ loadShader }} from "{WEB_LOADER_URL}";
globalThis.fetch = async () => ({{
    ok: false,
    status: 404,
}});
let message = "";
try {{
    await loadShader("missing_effect");
}} catch (error) {{
    message = error.message;
}}
console.log(JSON.stringify({{ message }}));
"""

    output = _run_node_module(script)
    assert output["message"] == "Shader not found: missing_effect"
