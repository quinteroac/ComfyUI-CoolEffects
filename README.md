# ComfyUI-CoolEffects

ComfyUI-CoolEffects is a custom node package for applying GLSL-driven effects to images in ComfyUI.

## Included nodes

- `CoolEffectSelector`: outputs the selected effect name (no image input required).
- `CoolGlitchEffect`: outputs glitch `EFFECT_PARAMS` from wave controls and includes a live preview widget.
- `CoolVHSEffect`: outputs VHS `EFFECT_PARAMS` from scanline/chroma controls and includes a live preview widget.
- `CoolZoomPulseEffect`: outputs zoom pulse `EFFECT_PARAMS` from pulse controls and includes a live preview widget.
- `CoolWaterDropsEffect`: outputs water-drops `EFFECT_PARAMS` from drop density/size/fall/refraction/gravity/wind controls.
- `CoolFrostedGlassEffect`: outputs frosted-glass `EFFECT_PARAMS` from frost intensity/blur/uniformity/tint/condensation controls.
- `CoolVideoGenerator`: renders shader-driven frame batches from an input image.
- `CoolVideoPlayer`: accepts a `VIDEO` input and previews decoded frames in an embedded canvas widget.
- `CoolTextOverlay`: burns text into every frame of a `VIDEO` with controllable style, position, alignment, and opacity, plus an inline canvas preview for first-frame text composition.

## Shader architecture

- Shared shader files live in `shaders/glsl/*.frag`.
- Python backend loads shaders through `shaders/loader.py`.
- Frontend shader list is fetched from `GET /cool_effects/shaders`.

## Development notes

- Place this repository under ComfyUI's `custom_nodes/`.
- Install dependencies from `requirements.txt`.

## GPU performance validation (US-004-AC05)

To validate the 512x512, 3s, 30fps under-30s requirement on real GPU hardware, run:

`python tests/manual_gpu_benchmark.py --effect-name glitch --width 512 --height 512 --fps 30 --duration 3 --threshold-seconds 30`

The script prints a JSON report and exits non-zero when the run exceeds the threshold.
