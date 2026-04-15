import importlib.util
import unittest
from pathlib import Path

import nodes.video_generator as video_generator


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_entrypoint_module():
    module_path = REPO_ROOT / "__init__.py"
    module_spec = importlib.util.spec_from_file_location(
        "cool_effects_entrypoint_for_bass_zoom_tests", module_path
    )
    if module_spec is None or module_spec.loader is None:
        raise ValueError(f"Missing module config at {module_path}")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


class TestBassZoomIntegration(unittest.TestCase):
    def test_entrypoint_registers_bass_zoom_node(self):
        entrypoint = _load_entrypoint_module()
        self.assertIn("CoolBassZoomEffect", entrypoint.NODE_CLASS_MAPPINGS)
        self.assertEqual(
            entrypoint.NODE_DISPLAY_NAME_MAPPINGS.get("CoolBassZoomEffect"),
            "Cool Bass Zoom Effect",
        )

    def test_video_generator_resolves_bass_feature_per_frame(self):
        beat_value, rms_value, bass_value = video_generator._resolve_audio_feature_frame(
            [{"beat": True, "rms": 0.75, "bass": 0.6}],
            0,
        )
        self.assertEqual(beat_value, 1.0)
        self.assertAlmostEqual(rms_value, 0.75)
        self.assertAlmostEqual(bass_value, 0.6)

    def test_video_generator_sets_bass_uniform_in_render_loop(self):
        source = (REPO_ROOT / "nodes" / "video_generator.py").read_text(encoding="utf-8")
        self.assertIn('program["u_bass"].value', source)


if __name__ == "__main__":
    unittest.main()
