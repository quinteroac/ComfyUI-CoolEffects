import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestWaveformAssets(unittest.TestCase):
    def test_shader_uniform_contract_and_waveform_line_formula(self):
        shader_source = (REPO_ROOT / "shaders" / "glsl" / "waveform.frag").read_text(
            encoding="utf-8"
        )

        self.assertIn("uniform sampler2D u_image;", shader_source)
        self.assertIn("uniform float u_time;", shader_source)
        self.assertIn("uniform vec2 u_resolution;", shader_source)
        self.assertIn("uniform float u_waveform[256];", shader_source)
        self.assertIn("uniform vec3 u_line_color;", shader_source)
        self.assertIn("uniform float u_line_thickness;", shader_source)
        self.assertIn("uniform float u_waveform_height;", shader_source)
        self.assertIn("uniform float u_waveform_y;", shader_source)
        self.assertIn("uniform float u_opacity;", shader_source)
        self.assertIn("int sample_index = int(floor(uv.x * 256.0));", shader_source)
        self.assertIn(
            "float waveform_y = u_waveform_y + sample * u_waveform_height * 0.5;",
            shader_source,
        )
        self.assertIn("abs(uv.y - waveform_y) < line_thickness", shader_source)

    def test_frontend_widget_mounts_and_synthesizes_waveform_preview(self):
        web_source = (REPO_ROOT / "web" / "waveform_effect.js").read_text(encoding="utf-8")

        self.assertIn('mount_effect_node_widget(node, "waveform"', web_source)
        self.assertIn("const WAVEFORM_SAMPLE_COUNT = 256;", web_source)
        self.assertIn("Math.sin(u_time * 4.0 + index / 40.0)", web_source)
        self.assertIn('preview_controller.set_uniform_array("u_waveform[0]", waveform_values);', web_source)


if __name__ == "__main__":
    unittest.main()
