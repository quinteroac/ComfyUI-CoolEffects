import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestFreqWarpAssets(unittest.TestCase):
    def test_shader_uniform_contract_and_warp_formula(self):
        shader_source = (
            REPO_ROOT / "shaders" / "glsl" / "freq_warp.frag"
        ).read_text(encoding="utf-8")

        self.assertIn("uniform sampler2D u_image;", shader_source)
        self.assertIn("uniform float u_time;", shader_source)
        self.assertIn("uniform vec2 u_resolution;", shader_source)
        self.assertIn("uniform float u_mid;", shader_source)
        self.assertIn("uniform float u_treble;", shader_source)
        self.assertIn("uniform float u_warp_intensity;", shader_source)
        self.assertIn("uniform float u_warp_frequency;", shader_source)
        self.assertIn("uniform float u_mid_weight;", shader_source)
        self.assertIn("uniform float u_treble_weight;", shader_source)
        self.assertIn("sin(uv.y * warp_frequency + u_time)", shader_source)
        self.assertIn("cos(uv.x * warp_frequency + (u_time * 1.1))", shader_source)

    def test_frontend_widget_mounts_and_uses_synthetic_mid_treble_preview_signal(self):
        web_source = (REPO_ROOT / "web" / "freq_warp_effect.js").read_text(
            encoding="utf-8"
        )

        self.assertIn('mount_effect_node_widget(\n        node,\n        "freq_warp"', web_source)
        self.assertIn('preview_controller.set_uniform("u_mid", Math.sin(u_time * 2.0));', web_source)
        self.assertIn(
            'preview_controller.set_uniform("u_treble", Math.cos(u_time * 3.5));',
            web_source,
        )


if __name__ == "__main__":
    unittest.main()
