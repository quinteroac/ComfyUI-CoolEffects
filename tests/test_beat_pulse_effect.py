import unittest

from nodes.beat_pulse_effect import CoolBeatPulseEffect


class TestBeatPulseEffectNode(unittest.TestCase):
    def test_input_types_match_story_contract(self):
        required = CoolBeatPulseEffect.INPUT_TYPES()["required"]
        self.assertEqual(required["pulse_intensity"][0], "FLOAT")
        self.assertEqual(
            required["pulse_intensity"][1],
            {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01},
        )
        self.assertEqual(required["zoom_amount"][0], "FLOAT")
        self.assertEqual(
            required["zoom_amount"][1],
            {"default": 0.05, "min": 0.0, "max": 0.3, "step": 0.005},
        )
        self.assertEqual(required["decay"][0], "FLOAT")
        self.assertEqual(
            required["decay"][1],
            {"default": 0.3, "min": 0.0, "max": 1.0, "step": 0.01},
        )

    def test_execute_returns_beat_pulse_effect_params(self):
        node = CoolBeatPulseEffect()
        (effect_params,) = node.execute(0.8, 0.1, 0.2)
        self.assertEqual(effect_params["effect_name"], "beat_pulse")
        self.assertEqual(
            effect_params["params"],
            {
                "u_pulse_intensity": 0.8,
                "u_zoom_amount": 0.1,
                "u_decay": 0.2,
            },
        )


if __name__ == "__main__":
    unittest.main()
