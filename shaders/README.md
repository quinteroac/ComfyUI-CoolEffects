# Shader Contract

All fragment shaders in `shaders/glsl/` must compile in ModernGL and expose the same required uniforms so they can be used interchangeably by backend and frontend render paths.

## Required uniforms

- `uniform sampler2D u_image` — input image texture
- `uniform float u_time` — animation time in seconds
- `uniform vec2 u_resolution` — output resolution in pixels

## File naming

- Use lowercase snake_case names
- Use `.frag` extension
- Example: `zoom_pulse.frag`
