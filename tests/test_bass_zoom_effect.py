import unittest

from nodes.bass_zoom_effect import CoolBassZoomEffect


class TestBassZoomEffectNode(unittest.TestCase):
    def test_input_types_match_story_contract(self):
        required = CoolBassZoomEffect.INPUT_TYPES()["required"]
        self.assertEqual(required["zoom_strength"][0], "FLOAT")
        self.assertEqual(
            required["zoom_strength"][1],
            {"default": 0.3, "min": 0.0, "max": 1.0, "step": 0.01},
        )
        self.assertEqual(required["smoothing"][0], "FLOAT")
        self.assertEqual(
            required["smoothing"][1],
            {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01},
        )

    def test_execute_returns_bass_zoom_effect_params(self):
        node = CoolBassZoomEffect()
        (effect_params,) = node.execute(0.42, 0.25)
        self.assertEqual(effect_params["effect_name"], "bass_zoom")
        self.assertEqual(
            effect_params["params"],
            {
                "u_zoom_strength": 0.42,
                "u_smoothing": 0.25,
            },
        )


if __name__ == "__main__":
    unittest.main()
