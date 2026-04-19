#version 330

uniform sampler2D u_image;
uniform float u_time;
uniform vec2 u_resolution;
uniform float u_dither_scale;
uniform float u_threshold;
uniform float u_palette_size;

out vec4 fragColor;

const float BAYER_8X8[64] = float[](
    0.0, 32.0, 8.0, 40.0, 2.0, 34.0, 10.0, 42.0,
    48.0, 16.0, 56.0, 24.0, 50.0, 18.0, 58.0, 26.0,
    12.0, 44.0, 4.0, 36.0, 14.0, 46.0, 6.0, 38.0,
    60.0, 28.0, 52.0, 20.0, 62.0, 30.0, 54.0, 22.0,
    3.0, 35.0, 11.0, 43.0, 1.0, 33.0, 9.0, 41.0,
    51.0, 19.0, 59.0, 27.0, 49.0, 17.0, 57.0, 25.0,
    15.0, 47.0, 7.0, 39.0, 13.0, 45.0, 5.0, 37.0,
    63.0, 31.0, 55.0, 23.0, 61.0, 29.0, 53.0, 21.0
);

float bayer_8x8(ivec2 matrix_coord) {
    int index = matrix_coord.y * 8 + matrix_coord.x;
    return (BAYER_8X8[index] + 0.5) / 64.0;
}

void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution;
    vec3 color = texture(u_image, uv).rgb;

    float safe_scale = max(u_dither_scale, 0.0001);
    ivec2 matrix_coord = ivec2(mod(floor(gl_FragCoord.xy / safe_scale), 8.0));
    float bayer_value = bayer_8x8(matrix_coord);

    float threshold = clamp(u_threshold, 0.0, 1.0);
    float palette_levels = clamp(u_palette_size, 2.0, 16.0);
    float palette_steps = max(palette_levels - 1.0, 1.0);

    float dither_offset = (bayer_value - 0.5) / palette_steps;
    vec3 adjusted = clamp(color + vec3(dither_offset) - vec3(threshold) + vec3(0.5), 0.0, 1.0);
    vec3 quantized = floor(adjusted * palette_steps + 0.5) / palette_steps;

    fragColor = vec4(clamp(quantized + (u_time * 0.0), 0.0, 1.0), 1.0);
}
