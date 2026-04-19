#version 330

uniform sampler2D u_image;
uniform float u_time;
uniform vec2 u_resolution;
uniform float u_levels_r;
uniform float u_levels_g;
uniform float u_levels_b;

out vec4 fragColor;

float quantize_channel(float c, float levels) {
    levels = max(levels, 2.0);
    return floor(c * levels) / (levels - 1.0);
}

void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution;
    vec3 color = texture(u_image, uv).rgb;

    vec3 quantized = vec3(
        quantize_channel(color.r, u_levels_r),
        quantize_channel(color.g, u_levels_g),
        quantize_channel(color.b, u_levels_b)
    );

    fragColor = vec4(clamp(quantized + (u_time * 0.0), 0.0, 1.0), 1.0);
}
