import importlib.util
import io
from contextlib import redirect_stderr
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_INIT = PACKAGE_ROOT / "__init__.py"


def _load_package_module():
    spec = importlib.util.spec_from_file_location("comfyui_cool_effects", PACKAGE_INIT)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_package_imports_without_errors():
    _load_package_module()


def test_init_exports_expected_node_mappings():
    module = _load_package_module()
    assert hasattr(module, "NODE_CLASS_MAPPINGS")
    assert hasattr(module, "NODE_DISPLAY_NAME_MAPPINGS")
    assert isinstance(module.NODE_CLASS_MAPPINGS, dict)
    assert isinstance(module.NODE_DISPLAY_NAME_MAPPINGS, dict)


def test_import_does_not_write_import_error_traceback():
    stderr = io.StringIO()
    with redirect_stderr(stderr):
        _load_package_module()
    assert "Traceback" not in stderr.getvalue()

