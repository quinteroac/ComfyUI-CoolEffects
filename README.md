# ComfyUI-CoolEffects

ComfyUI-CoolEffects is a custom node package for applying GLSL-driven effects to images in ComfyUI.

## Included nodes

- `CoolEffectSelector`: outputs the selected effect name (no image input required).
- `CoolGlitchEffect`: outputs glitch `EFFECT_PARAMS` from wave controls and includes a live preview widget.
- `CoolVHSEffect`: outputs VHS `EFFECT_PARAMS` from scanline/chroma controls and includes a live preview widget.
- `CoolZoomPulseEffect`: outputs zoom pulse `EFFECT_PARAMS` from pulse controls and includes a live preview widget.
- `CoolZoomInEffect`: outputs zoom-in `EFFECT_PARAMS` from zoom strength/speed controls and includes a live preview widget.
- `CoolZoomOutEffect`: outputs zoom-out `EFFECT_PARAMS` from zoom strength/speed controls and includes a live preview widget.
- `CoolDollyInEffect`: outputs dolly-in `EFFECT_PARAMS` from dolly strength/speed + focus controls and includes a live preview widget.
- `CoolDollyOutEffect`: outputs dolly-out `EFFECT_PARAMS` from dolly strength/speed + focus controls and includes a live preview widget.
- `CoolBassZoomEffect`: outputs bass zoom `EFFECT_PARAMS` from zoom/smoothing controls and includes a synthetic-60-BPM live preview pulse.
- `CoolBeatPulseEffect`: outputs beat pulse `EFFECT_PARAMS` from pulse intensity/zoom/decay controls and includes a synthetic-120-BPM live preview signal.
- `CoolFreqWarpEffect`: outputs frequency-warp `EFFECT_PARAMS` from warp and band-weight controls and includes a synthetic mid/treble live preview signal.
- `CoolWaveformEffect`: outputs waveform `EFFECT_PARAMS` from line color/thickness/height/position/opacity controls and includes an always-animated oscilloscope preview signal.
- `CoolWaterDropsEffect`: outputs water-drops `EFFECT_PARAMS` from drop density/size/fall/refraction/gravity/wind controls.
- `CoolFrostedGlassEffect`: outputs frosted-glass `EFFECT_PARAMS` from frost intensity/blur/uniformity/tint/condensation controls.
- `CoolFisheyeEffect`: outputs fisheye `EFFECT_PARAMS` from strength/zoom controls and includes a live preview widget.
- `CoolVignetteEffect`: outputs vignette `EFFECT_PARAMS` from strength/radius/softness controls and includes a live preview widget.
- `CoolTiltShiftEffect`: outputs tilt-shift `EFFECT_PARAMS` from focus-center/focus-width/blur-strength/angle controls and includes a live preview widget.
- `CoolPincushionEffect`: outputs pincushion `EFFECT_PARAMS` from strength/zoom controls and includes a live preview widget.
- `CoolChromaticAberrationEffect`: outputs chromatic-aberration `EFFECT_PARAMS` from strength/radial controls and includes a live preview widget.
- `CoolBrightnessContrastEffect`: outputs brightness/contrast `EFFECT_PARAMS` from brightness/contrast controls and includes a live preview widget.
- `CoolHSLEffect`: outputs HSL `EFFECT_PARAMS` from hue-shift/saturation/lightness controls and includes a live preview widget.
- `CoolColorTemperatureEffect`: outputs color-temperature `EFFECT_PARAMS` from temperature/tint controls and includes a live preview widget.
- `CoolTextOverlayEffect`: outputs text-overlay `EFFECT_PARAMS` from text/font/color/position/animation controls and includes a live preview widget.
- `CoolVideoGenerator`: renders shader-driven frame batches from an input image and accepts chained `effect_params_1`…`effect_params_8` inputs.
- `CoolVideoPlayer`: accepts a `VIDEO` input and previews decoded frames in an embedded canvas widget.

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
