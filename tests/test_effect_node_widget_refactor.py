from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = PACKAGE_ROOT / "web"


def test_shared_effect_node_widget_helper_exists_with_mount_api():
    helper_source = (WEB_DIR / "effect_node_widget.js").read_text(encoding="utf-8")
    assert "export async function mount_effect_node_widget(" in helper_source
    assert "export function apply_effect_widget_uniform_from_widget(" in helper_source


def test_effect_extensions_use_shared_effect_node_widget_helper():
    for widget_file_name in (
        "glitch_effect.js",
        "vhs_effect.js",
        "zoom_pulse_effect.js",
        "water_drops_effect.js",
        "frosted_glass_effect.js",
    ):
        widget_source = (WEB_DIR / widget_file_name).read_text(encoding="utf-8")
        assert 'from "./effect_node_widget.js"' in widget_source
        assert "mount_effect_node_widget(" in widget_source
        assert "apply_effect_widget_uniform_from_widget(" in widget_source
        assert "create_live_glsl_preview" not in widget_source
        assert "create_placeholder_texture" not in widget_source
