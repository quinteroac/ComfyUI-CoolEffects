import asyncio
import importlib.util
import json
import sys
import types
import uuid
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_INIT = PACKAGE_ROOT / "__init__.py"


class _FakeRoutes:
    def __init__(self):
        self.registrations = []

    def get(self, path):
        def _decorator(handler):
            self.registrations.append((path, handler))
            return handler

        return _decorator


def _load_package_module(server_module=None):
    module_name = f"comfyui_cool_effects_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, PACKAGE_INIT)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None

    original_server = sys.modules.get("server")
    try:
        if server_module is not None:
            sys.modules["server"] = server_module
        elif "server" in sys.modules:
            del sys.modules["server"]
        spec.loader.exec_module(module)
    finally:
        if original_server is None:
            sys.modules.pop("server", None)
        else:
            sys.modules["server"] = original_server

    return module


def test_endpoint_is_registered_at_import_time():
    routes = _FakeRoutes()
    server_module = types.ModuleType("server")
    server_module.PromptServer = types.SimpleNamespace(
        instance=types.SimpleNamespace(routes=routes)
    )

    module = _load_package_module(server_module=server_module)

    assert routes.registrations
    route_path, route_handler = routes.registrations[0]
    assert route_path == "/cool_effects/shaders"
    assert route_handler is module.get_shaders


def test_endpoint_returns_json_with_http_200(monkeypatch):
    module = _load_package_module()
    monkeypatch.setattr(module, "list_shaders", lambda: ["glitch", "vhs"])

    response = asyncio.run(module.get_shaders(None))

    assert response.status == 200
    assert response.content_type == "application/json"
    assert json.loads(response.text) == {"shaders": ["glitch", "vhs"]}


def test_endpoint_reads_shader_names_at_request_time(monkeypatch):
    module = _load_package_module()
    responses = [["glitch"], ["glitch", "runtime_added"]]

    def _list_shaders():
        return responses.pop(0)

    monkeypatch.setattr(module, "list_shaders", _list_shaders)

    first_response = asyncio.run(module.get_shaders(None))
    second_response = asyncio.run(module.get_shaders(None))

    assert json.loads(first_response.text) == {"shaders": ["glitch"]}
    assert json.loads(second_response.text) == {"shaders": ["glitch", "runtime_added"]}
