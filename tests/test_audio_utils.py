import ast
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

from nodes.audio_utils import extract_audio_features


class TestAudioUtils(unittest.TestCase):
    def test_extract_audio_features_returns_expected_frame_count(self):
        fps = 30
        duration = 2.5
        audio = np.zeros((1, int(fps * duration * 100)), dtype=np.float32)
        features = extract_audio_features(audio, fps=fps, duration=duration)
        self.assertEqual(len(features), round(duration * fps))

    def test_extract_audio_features_contract_and_beat_detection(self):
        fps = 10
        duration = 1.0
        samples_per_frame = 100
        frame_count = round(fps * duration)
        audio = np.zeros((frame_count * samples_per_frame,), dtype=np.float32)
        spike_frame = 6
        start = spike_frame * samples_per_frame
        end = (spike_frame + 1) * samples_per_frame
        audio[start:end] = 1.0

        features = extract_audio_features(audio, fps=fps, duration=duration)
        expected_keys = {"rms", "beat", "bass", "mid", "treble"}

        self.assertEqual(len(features), frame_count)
        self.assertEqual(set(features[0].keys()), expected_keys)

        beat_frames = []
        for index, feature in enumerate(features):
            self.assertIsInstance(feature["rms"], float)
            self.assertGreaterEqual(feature["rms"], 0.0)
            self.assertLessEqual(feature["rms"], 1.0)
            self.assertIsInstance(feature["beat"], bool)
            self.assertIsInstance(feature["bass"], float)
            self.assertIsInstance(feature["mid"], float)
            self.assertIsInstance(feature["treble"], float)
            self.assertGreaterEqual(feature["bass"], 0.0)
            self.assertLessEqual(feature["bass"], 1.0)
            self.assertGreaterEqual(feature["mid"], 0.0)
            self.assertLessEqual(feature["mid"], 1.0)
            self.assertGreaterEqual(feature["treble"], 0.0)
            self.assertLessEqual(feature["treble"], 1.0)
            if feature["beat"]:
                beat_frames.append(index)

        self.assertIn(spike_frame, beat_frames)

    def test_extract_audio_features_frequency_bands_use_rfft_and_normalize_per_band(self):
        fps = 4
        duration = 1.0
        sample_rate = 48000
        samples_per_frame = int(sample_rate / fps)

        t = np.arange(samples_per_frame, dtype=np.float32) / float(sample_rate)
        frame_bass_loud = np.sin(2.0 * np.pi * 120.0 * t)
        frame_bass_quiet = 0.5 * np.sin(2.0 * np.pi * 120.0 * t)
        frame_mid = np.sin(2.0 * np.pi * 900.0 * t)
        frame_treble = np.sin(2.0 * np.pi * 8100.0 * t)
        audio = np.concatenate(
            [frame_bass_loud, frame_bass_quiet, frame_mid, frame_treble]
        ).astype(np.float32)

        with mock.patch("nodes.audio_utils.np.fft.rfft", wraps=np.fft.rfft) as rfft_mock:
            features = extract_audio_features(
                {"samples": audio, "sample_rate": sample_rate},
                fps=fps,
                duration=duration,
            )

        self.assertGreaterEqual(rfft_mock.call_count, round(duration * fps))
        self.assertEqual(len(features), round(duration * fps))

        self.assertGreater(features[0]["bass"], 0.95)
        self.assertGreater(features[1]["bass"], 0.45)
        self.assertLess(features[1]["bass"], 0.55)
        self.assertLess(features[2]["bass"], 0.05)
        self.assertLess(features[3]["bass"], 0.05)

        self.assertLess(features[0]["mid"], 0.05)
        self.assertLess(features[1]["mid"], 0.05)
        self.assertGreater(features[2]["mid"], 0.95)
        self.assertLess(features[3]["mid"], 0.05)

        self.assertLess(features[0]["treble"], 0.05)
        self.assertLess(features[1]["treble"], 0.05)
        self.assertLess(features[2]["treble"], 0.05)
        self.assertGreater(features[3]["treble"], 0.95)

    def test_extract_audio_features_handles_none_audio(self):
        fps = 24
        duration = 2.0
        features = extract_audio_features(None, fps=fps, duration=duration)
        self.assertEqual(len(features), round(duration * fps))
        for feature in features:
            self.assertEqual(
                feature,
                {
                    "rms": 0.0,
                    "beat": False,
                    "bass": 0.0,
                    "mid": 0.0,
                    "treble": 0.0,
                },
            )

    def test_audio_utils_module_imports_are_dependency_safe(self):
        source_path = Path(__file__).resolve().parents[1] / "nodes" / "audio_utils.py"
        module_ast = ast.parse(source_path.read_text(encoding="utf-8"))
        imported_modules = set()

        for node in module_ast.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_modules.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported_modules.add(node.module.split(".")[0])

        self.assertNotIn("moderngl", imported_modules)
        self.assertNotIn("torch", imported_modules)
        self.assertNotIn("server", imported_modules)
        self.assertNotIn("comfy_api", imported_modules)
        self.assertNotIn("librosa", imported_modules)


if __name__ == "__main__":
    unittest.main()
