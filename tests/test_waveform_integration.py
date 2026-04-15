import importlib.util
import unittest
from pathlib import Path

import nodes.video_generator as video_generator


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_entrypoint_module():
    module_path = REPO_ROOT / "__init__.py"
    module_spec = importlib.util.spec_from_file_location(
        "cool_effects_entrypoint_for_waveform_tests", module_path
    )
    if module_spec is None or module_spec.loader is None:
        raise ValueError(f"Missing module config at {module_path}")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


class TestWaveformIntegration(unittest.TestCase):
    def test_entrypoint_registers_waveform_node(self):
        entrypoint = _load_entrypoint_module()
        self.assertIn("CoolWaveformEffect", entrypoint.NODE_CLASS_MAPPINGS)
        self.assertEqual(
            entrypoint.NODE_DISPLAY_NAME_MAPPINGS.get("CoolWaveformEffect"),
            "Cool Waveform Effect",
        )

    def test_video_generator_resolves_waveform_feature_per_frame(self):
        values = video_generator._resolve_waveform_feature_frame(
            [{"waveform": [0.5, -2.0, 2.0]}],
            0,
        )
        self.assertEqual(len(values), 256)
        self.assertEqual(values[0], 0.5)
        self.assertEqual(values[1], -1.0)
        self.assertEqual(values[2], 1.0)

    def test_video_generator_sets_waveform_uniform_in_render_loop(self):
        source = (REPO_ROOT / "nodes" / "video_generator.py").read_text(encoding="utf-8")
        self.assertIn("program['u_waveform'].value = features[i]['waveform']", source)


if __name__ == "__main__":
    unittest.main()
