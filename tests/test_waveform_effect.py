import unittest

from nodes.waveform_effect import CoolWaveformEffect


class TestWaveformEffectNode(unittest.TestCase):
    def test_input_types_match_story_contract(self):
        required = CoolWaveformEffect.INPUT_TYPES()["required"]
        self.assertEqual(required["line_color"][0], "STRING")
        self.assertEqual(required["line_color"][1], {"default": "1.0,0.8,0.2"})
        self.assertEqual(required["line_thickness"][0], "FLOAT")
        self.assertEqual(
            required["line_thickness"][1],
            {"default": 0.005, "min": 0.001, "max": 0.05, "step": 0.001},
        )
        self.assertEqual(required["waveform_height"][0], "FLOAT")
        self.assertEqual(
            required["waveform_height"][1],
            {"default": 0.2, "min": 0.05, "max": 0.8, "step": 0.01},
        )
        self.assertEqual(required["waveform_y"][0], "FLOAT")
        self.assertEqual(
            required["waveform_y"][1],
            {"default": 0.8, "min": 0.0, "max": 1.0, "step": 0.01},
        )
        self.assertEqual(required["opacity"][0], "FLOAT")
        self.assertEqual(
            required["opacity"][1],
            {"default": 0.85, "min": 0.0, "max": 1.0, "step": 0.01},
        )

    def test_execute_returns_waveform_effect_params(self):
        node = CoolWaveformEffect()
        (effect_params,) = node.execute("0.2,0.4,0.6", 0.01, 0.25, 0.7, 0.9)
        self.assertEqual(effect_params["effect_name"], "waveform")
        self.assertEqual(
            effect_params["params"],
            {
                "u_line_color": (0.2, 0.4, 0.6),
                "u_line_thickness": 0.01,
                "u_waveform_height": 0.25,
                "u_waveform_y": 0.7,
                "u_opacity": 0.9,
            },
        )

    def test_execute_falls_back_to_default_color_and_logs_warning(self):
        node = CoolWaveformEffect()
        with self.assertLogs("nodes.waveform_effect", level="WARNING") as logs:
            (effect_params,) = node.execute("oops", 0.01, 0.25, 0.7, 0.9)

        self.assertEqual(effect_params["params"]["u_line_color"], (1.0, 0.8, 0.2))
        self.assertIn("using default (1.0, 0.8, 0.2)", logs.output[0])

    def test_execute_clamps_line_color_components_to_unit_range(self):
        node = CoolWaveformEffect()
        (effect_params,) = node.execute("1.7,-0.5,0.4", 0.01, 0.25, 0.7, 0.9)
        self.assertEqual(effect_params["params"]["u_line_color"], (1.0, 0.0, 0.4))


if __name__ == "__main__":
    unittest.main()
