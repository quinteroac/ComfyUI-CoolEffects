import importlib.util
import inspect
import uuid
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent.parent
NODE_PATH = PACKAGE_ROOT / "nodes" / "video_player.py"
PACKAGE_INIT = PACKAGE_ROOT / "__init__.py"


def _load_module(module_path: Path):
    module_name = f"cool_effects_test_video_player_module_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_video_player_declares_single_video_input():
    module = _load_module(NODE_PATH)
    input_types = module.CoolVideoPlayer.INPUT_TYPES()

    assert input_types == {"required": {"video": ("VIDEO",)}}
    assert module.CoolVideoPlayer.RETURN_TYPES == ()
    assert module.CoolVideoPlayer.OUTPUT_NODE is True


def test_video_player_execute_signature_and_ui_payload():
    module = _load_module(NODE_PATH)
    node = module.CoolVideoPlayer()

    result = node.execute(
        {
            "filename": "preview.mp4",
            "subfolder": "cool",
            "type": "temp",
            "format": "video/mp4",
        }
    )

    assert list(inspect.signature(module.CoolVideoPlayer.execute).parameters) == [
        "self",
        "video",
    ]
    assert result["result"] == ()
    assert result["ui"]["video_entries"] == [
        {
            "source_url": "/view?filename=preview.mp4&type=temp&subfolder=cool",
            "filename": "preview.mp4",
            "type": "temp",
            "subfolder": "cool",
            "format": "video/mp4",
        }
    ]


def test_package_registers_cool_video_player_node():
    package_module = _load_module(PACKAGE_INIT)

    assert "CoolVideoPlayer" in package_module.NODE_CLASS_MAPPINGS
    assert package_module.NODE_DISPLAY_NAME_MAPPINGS["CoolVideoPlayer"] == "Cool Video Player"
