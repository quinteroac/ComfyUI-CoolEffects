import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestBassZoomAssets(unittest.TestCase):
    def test_shader_uniform_contract_and_zoom_formula(self):
        shader_source = (
            REPO_ROOT / "shaders" / "glsl" / "bass_zoom.frag"
        ).read_text(encoding="utf-8")

        self.assertIn("uniform sampler2D u_image;", shader_source)
        self.assertIn("uniform float u_time;", shader_source)
        self.assertIn("uniform vec2 u_resolution;", shader_source)
        self.assertIn("uniform float u_bass;", shader_source)
        self.assertIn("uniform float u_zoom_strength;", shader_source)
        self.assertIn("uniform float u_smoothing;", shader_source)
        self.assertIn("float zoom_scale = 1.0 + bass * max(u_zoom_strength, 0.0);", shader_source)
        self.assertIn("vec2 center = vec2(0.5, 0.5);", shader_source)

    def test_frontend_widget_mounts_and_uses_synthetic_60bpm_bass_pulse(self):
        web_source = (REPO_ROOT / "web" / "bass_zoom_effect.js").read_text(
            encoding="utf-8"
        )

        self.assertIn('mount_effect_node_widget(node, "bass_zoom"', web_source)
        self.assertIn("const SYNTHETIC_BPM = 60;", web_source)
        self.assertIn("60000 / SYNTHETIC_BPM", web_source)
        self.assertIn('preview_controller.set_uniform("u_bass", get_synthetic_bass_pulse(now()));', web_source)


if __name__ == "__main__":
    unittest.main()
