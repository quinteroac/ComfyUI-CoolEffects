"""ComfyUI-CoolEffects package entrypoint."""

import importlib.util
import json
from pathlib import Path

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

_SHADER_LOADER_PATH = Path(__file__).parent / "shaders" / "loader.py"
_SHADER_LOADER_SPEC = importlib.util.spec_from_file_location(
    "cool_effects_shader_loader_runtime", _SHADER_LOADER_PATH
)
if _SHADER_LOADER_SPEC is None or _SHADER_LOADER_SPEC.loader is None:
    raise ValueError(f"Missing shader loader config at {_SHADER_LOADER_PATH}")
_shader_loader_module = importlib.util.module_from_spec(_SHADER_LOADER_SPEC)
_SHADER_LOADER_SPEC.loader.exec_module(_shader_loader_module)
list_shaders = _shader_loader_module.list_shaders


class _JsonResponseFallback:
    def __init__(self, payload):
        self.status = 200
        self.content_type = "application/json"
        self.text = json.dumps(payload)


async def get_shaders(_request):
    payload = list_shaders()

    try:
        from aiohttp import web
    except ImportError:
        return _JsonResponseFallback(payload)

    return web.json_response(payload)


def _register_routes() -> None:
    try:
        from server import PromptServer
    except ImportError:
        return

    prompt_server = getattr(PromptServer, "instance", None)
    if prompt_server is None:
        return

    routes = getattr(prompt_server, "routes", None)
    if routes is None:
        return

    is_registered = getattr(routes, "_cool_effects_shader_list_registered", False)
    if is_registered:
        return

    routes.get("/cool_effects/shaders")(get_shaders)
    setattr(routes, "_cool_effects_shader_list_registered", True)


_register_routes()
