#version 330

uniform sampler2D u_image;
uniform float u_time;
uniform vec2 u_resolution;
uniform float u_pixel_size;
uniform float u_grid_strength;
uniform float u_scanline_strength;

out vec4 fragColor;

void main() {
    float cell_size = max(u_pixel_size, 1.0);
    vec2 cell_origin = floor(gl_FragCoord.xy / cell_size) * cell_size;
    vec2 sample_coord = cell_origin + vec2(cell_size * 0.5);
    vec2 sample_uv = clamp(sample_coord / u_resolution, vec2(0.0), vec2(1.0));
    vec3 base_color = texture(u_image, sample_uv).rgb;

    float local_x = mod(gl_FragCoord.x, cell_size) / cell_size;
    vec3 rgb_mask = vec3(0.0);
    if (local_x < (1.0 / 3.0)) {
        rgb_mask = vec3(1.0, 0.0, 0.0);
    } else if (local_x < (2.0 / 3.0)) {
        rgb_mask = vec3(0.0, 1.0, 0.0);
    } else {
        rgb_mask = vec3(0.0, 0.0, 1.0);
    }

    float grid_strength = clamp(u_grid_strength, 0.0, 1.0);
    vec3 grid_color = mix(base_color, base_color * rgb_mask, grid_strength);

    float scanline_pattern = 0.5 + 0.5 * cos(gl_FragCoord.y * 3.14159265);
    float scanline_strength = clamp(u_scanline_strength, 0.0, 1.0);
    float scanline_factor = 1.0 - scanline_strength * (1.0 - scanline_pattern);

    vec3 color = clamp(grid_color * scanline_factor + (u_time * 0.0), 0.0, 1.0);
    fragColor = vec4(color, 1.0);
}
