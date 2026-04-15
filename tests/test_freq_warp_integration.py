import importlib.util
import unittest
from pathlib import Path

import nodes.video_generator as video_generator


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_entrypoint_module():
    module_path = REPO_ROOT / "__init__.py"
    module_spec = importlib.util.spec_from_file_location(
        "cool_effects_entrypoint_for_freq_warp_tests", module_path
    )
    if module_spec is None or module_spec.loader is None:
        raise ValueError(f"Missing module config at {module_path}")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


class TestFreqWarpIntegration(unittest.TestCase):
    def test_entrypoint_registers_freq_warp_node(self):
        entrypoint = _load_entrypoint_module()
        self.assertIn("CoolFreqWarpEffect", entrypoint.NODE_CLASS_MAPPINGS)
        self.assertEqual(
            entrypoint.NODE_DISPLAY_NAME_MAPPINGS.get("CoolFreqWarpEffect"),
            "Cool Freq Warp Effect",
        )

    def test_video_generator_resolves_mid_and_treble_feature_per_frame(self):
        beat_value, rms_value, bass_value, mid_value, treble_value = (
            video_generator._resolve_audio_feature_frame(
                [{"beat": True, "rms": 0.75, "bass": 0.6, "mid": 0.45, "treble": 0.35}],
                0,
            )
        )
        self.assertEqual(beat_value, 1.0)
        self.assertAlmostEqual(rms_value, 0.75)
        self.assertAlmostEqual(bass_value, 0.6)
        self.assertAlmostEqual(mid_value, 0.45)
        self.assertAlmostEqual(treble_value, 0.35)

    def test_video_generator_sets_mid_and_treble_uniforms_in_render_loop(self):
        source = (REPO_ROOT / "nodes" / "video_generator.py").read_text(encoding="utf-8")
        self.assertIn('program["u_mid"].value', source)
        self.assertIn('program["u_treble"].value', source)


if __name__ == "__main__":
    unittest.main()
