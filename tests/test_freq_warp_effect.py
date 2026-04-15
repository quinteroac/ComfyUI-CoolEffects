import unittest

from nodes.freq_warp_effect import CoolFreqWarpEffect


class TestFreqWarpEffectNode(unittest.TestCase):
    def test_input_types_match_story_contract(self):
        required = CoolFreqWarpEffect.INPUT_TYPES()["required"]
        self.assertEqual(required["warp_intensity"][0], "FLOAT")
        self.assertEqual(
            required["warp_intensity"][1],
            {"default": 0.4, "min": 0.0, "max": 1.0, "step": 0.01},
        )
        self.assertEqual(required["warp_frequency"][0], "FLOAT")
        self.assertEqual(
            required["warp_frequency"][1],
            {"default": 8.0, "min": 1.0, "max": 32.0, "step": 0.5},
        )
        self.assertEqual(required["mid_weight"][0], "FLOAT")
        self.assertEqual(
            required["mid_weight"][1],
            {"default": 0.6, "min": 0.0, "max": 1.0, "step": 0.01},
        )
        self.assertEqual(required["treble_weight"][0], "FLOAT")
        self.assertEqual(
            required["treble_weight"][1],
            {"default": 0.4, "min": 0.0, "max": 1.0, "step": 0.01},
        )

    def test_execute_returns_freq_warp_effect_params(self):
        node = CoolFreqWarpEffect()
        (effect_params,) = node.execute(0.55, 12.5, 0.7, 0.3)
        self.assertEqual(effect_params["effect_name"], "freq_warp")
        self.assertEqual(
            effect_params["params"],
            {
                "u_warp_intensity": 0.55,
                "u_warp_frequency": 12.5,
                "u_mid_weight": 0.7,
                "u_treble_weight": 0.3,
            },
        )


if __name__ == "__main__":
    unittest.main()
