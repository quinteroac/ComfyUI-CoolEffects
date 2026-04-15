import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestBeatPulseAssets(unittest.TestCase):
    def test_shader_uniform_contract_and_decay_behavior(self):
        shader_source = (
            REPO_ROOT / "shaders" / "glsl" / "beat_pulse.frag"
        ).read_text(encoding="utf-8")

        self.assertIn("uniform sampler2D u_image;", shader_source)
        self.assertIn("uniform float u_time;", shader_source)
        self.assertIn("uniform vec2 u_resolution;", shader_source)
        self.assertIn("uniform float u_pulse_intensity;", shader_source)
        self.assertIn("uniform float u_zoom_amount;", shader_source)
        self.assertIn("uniform float u_decay;", shader_source)
        self.assertIn("uniform float u_beat;", shader_source)
        self.assertIn("uniform float u_rms;", shader_source)
        self.assertIn("exp(", shader_source)

    def test_frontend_widget_mounts_and_uses_synthetic_120bpm_signal(self):
        web_source = (REPO_ROOT / "web" / "beat_pulse_effect.js").read_text(
            encoding="utf-8"
        )

        self.assertIn('mount_effect_node_widget(\n        node,\n        "beat_pulse"', web_source)
        self.assertIn("const SYNTHETIC_BPM = 120;", web_source)
        self.assertIn("60000 / SYNTHETIC_BPM", web_source)
        self.assertIn('preview_controller.set_uniform("u_beat", beat);', web_source)
        self.assertIn('preview_controller.set_uniform("u_rms", rms);', web_source)


if __name__ == "__main__":
    unittest.main()
