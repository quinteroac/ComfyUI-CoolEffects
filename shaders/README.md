# Shader Contract

All fragment shaders in `shaders/glsl/` must compile in ModernGL and expose the same required uniforms so they can be used interchangeably by backend and frontend render paths.

## Required uniforms

- `uniform sampler2D u_image` — input image texture
- `uniform float u_time` — animation time in seconds
- `uniform vec2 u_resolution` — output resolution in pixels

## Output variable

- Use `out vec4 fragColor` for fragment output.

## File naming

- Use lowercase snake_case names
- Use `.frag` extension
- Example: `zoom_pulse.frag`

## Per-effect uniforms and defaults

Defaults below mirror `nodes/effect_params.py` (`DEFAULT_PARAMS`) and preserve behavior when effect-specific uniforms are not explicitly overridden.

### `glitch.frag`

- `uniform float u_wave_freq` — default: `120.0`
- `uniform float u_wave_amp` — default: `0.0025`
- `uniform float u_speed` — default: `10.0`

### `vhs.frag`

- `uniform float u_scanline_intensity` — default: `0.04`
- `uniform float u_jitter_amount` — default: `0.0018`
- `uniform float u_chroma_shift` — default: `0.002`

### `zoom_pulse.frag`

- `uniform float u_pulse_amp` — default: `0.06`
- `uniform float u_pulse_speed` — default: `3.0`

### `pan_left.frag`

- `uniform float u_speed` — default: `0.1`
- `uniform float u_origin_x` — default: `0.0`
- `uniform float u_origin_y` — default: `0.0`

### `pan_right.frag`

- `uniform float u_speed` — default: `0.1`
- `uniform float u_origin_x` — default: `0.0`
- `uniform float u_origin_y` — default: `0.0`

### `pan_up.frag`

- `uniform float u_speed` — default: `0.1`
- `uniform float u_origin_x` — default: `0.0`
- `uniform float u_origin_y` — default: `0.0`

### `pan_down.frag`

- `uniform float u_speed` — default: `0.1`
- `uniform float u_origin_x` — default: `0.0`
- `uniform float u_origin_y` — default: `0.0`
