#version 330

uniform sampler2D u_image;
uniform sampler2D u_lut_texture;
uniform float u_time;
uniform vec2 u_resolution;
uniform float u_lut_size;
uniform vec3 u_domain_min;
uniform vec3 u_domain_max;
uniform float u_intensity;

out vec4 fragColor;

vec3 sample_lut_strip(vec3 color) {
    float size = max(u_lut_size, 2.0);
    float cells_per_row = size;
    float row_width = size * size;
    float max_index = size - 1.0;

    float blue_index = clamp(color.b, 0.0, 1.0) * max_index;
    float blue_floor = floor(blue_index);
    float blue_ceil = min(blue_floor + 1.0, max_index);
    float blue_mix = fract(blue_index);

    float red_index = clamp(color.r, 0.0, 1.0) * max_index;
    float green_index = clamp(color.g, 0.0, 1.0) * max_index;

    float x_floor = red_index + (green_index * cells_per_row) + 0.5;
    float x_uv = x_floor / row_width;

    float y0_uv = (blue_floor + 0.5) / size;
    float y1_uv = (blue_ceil + 0.5) / size;

    vec3 slice0 = texture(u_lut_texture, vec2(x_uv, y0_uv)).rgb;
    vec3 slice1 = texture(u_lut_texture, vec2(x_uv, y1_uv)).rgb;
    return mix(slice0, slice1, blue_mix);
}

void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution;
    vec4 source_color = texture(u_image, uv);
    vec3 source_rgb = source_color.rgb;

    vec3 domain_span = max(u_domain_max - u_domain_min, vec3(0.000001));
    vec3 normalized_lut_input = clamp((source_rgb - u_domain_min) / domain_span, 0.0, 1.0);
    vec3 lut_color = sample_lut_strip(normalized_lut_input);

    float intensity = clamp(u_intensity, 0.0, 1.0);
    vec3 output_color = mix(source_rgb, lut_color, intensity);
    fragColor = vec4(clamp(output_color, 0.0, 1.0), source_color.a);
}
