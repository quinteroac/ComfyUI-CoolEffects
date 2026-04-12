import argparse
import importlib.util
import json
import time
from pathlib import Path

import torch


PACKAGE_ROOT = Path(__file__).resolve().parent.parent
NODE_PATH = PACKAGE_ROOT / "nodes" / "video_generator.py"


def _load_video_generator_module():
    spec = importlib.util.spec_from_file_location("cool_effects_video_generator_benchmark", NODE_PATH)
    if spec is None or spec.loader is None:
        raise ValueError(f"Missing node module at {NODE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_benchmark(effect_name: str, width: int, height: int, fps: int, duration: float, threshold_seconds: float) -> int:
    module = _load_video_generator_module()
    node = module.CoolVideoGenerator()

    image = torch.ones((1, height, width, 3), dtype=torch.float32)
    expected_frames = round(duration * fps)

    start = time.perf_counter()
    output, = node.execute(image=image, effect_name=effect_name, fps=fps, duration=duration)
    elapsed_seconds = time.perf_counter() - start

    passed = elapsed_seconds < threshold_seconds and tuple(output.shape) == (expected_frames, height, width, 3)
    report = {
        "effect_name": effect_name,
        "resolution": [width, height],
        "fps": fps,
        "duration_seconds": duration,
        "expected_frames": expected_frames,
        "actual_shape": list(output.shape),
        "elapsed_seconds": elapsed_seconds,
        "threshold_seconds": threshold_seconds,
        "passed": passed,
    }
    print(json.dumps(report, indent=2))
    return 0 if passed else 1


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run real-GPU benchmark for CoolVideoGenerator US-004-AC05."
    )
    parser.add_argument("--effect-name", default="glitch")
    parser.add_argument("--width", type=int, default=512)
    parser.add_argument("--height", type=int, default=512)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--duration", type=float, default=3.0)
    parser.add_argument("--threshold-seconds", type=float, default=30.0)
    args = parser.parse_args()

    return _run_benchmark(
        effect_name=args.effect_name,
        width=args.width,
        height=args.height,
        fps=args.fps,
        duration=args.duration,
        threshold_seconds=args.threshold_seconds,
    )


if __name__ == "__main__":
    raise SystemExit(main())
