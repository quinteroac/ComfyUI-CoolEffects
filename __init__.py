"""ComfyUI-CoolEffects package entrypoint."""

import importlib.util
import json
from pathlib import Path

PACKAGE_ROOT = Path(__file__).parent
WEB_DIRECTORY = "web"


def _load_module_from_path(module_name: str, module_path: Path):
    module_spec = importlib.util.spec_from_file_location(module_name, module_path)
    if module_spec is None or module_spec.loader is None:
        raise ValueError(f"Missing module config at {module_path}")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


_shader_loader_module = _load_module_from_path(
    "cool_effects_shader_loader_runtime", PACKAGE_ROOT / "shaders" / "loader.py"
)
list_shaders = _shader_loader_module.list_shaders

_effect_selector_module = _load_module_from_path(
    "cool_effects_effect_selector_runtime",
    PACKAGE_ROOT / "nodes" / "effect_selector.py",
)
CoolEffectSelector = _effect_selector_module.CoolEffectSelector

_video_generator_module = _load_module_from_path(
    "cool_effects_video_generator_runtime",
    PACKAGE_ROOT / "nodes" / "video_generator.py",
)
CoolVideoGenerator = _video_generator_module.CoolVideoGenerator

NODE_CLASS_MAPPINGS = {
    "CoolEffectSelector": CoolEffectSelector,
    "CoolVideoGenerator": CoolVideoGenerator,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "CoolEffectSelector": "Cool Effect Selector",
    "CoolVideoGenerator": "Cool Video Generator",
}


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
