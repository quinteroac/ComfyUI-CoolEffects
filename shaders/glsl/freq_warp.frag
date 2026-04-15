#version 330

uniform sampler2D u_image;
uniform float u_time;
uniform vec2 u_resolution;
uniform float u_mid;
uniform float u_treble;
uniform float u_warp_intensity;
uniform float u_warp_frequency;
uniform float u_mid_weight;
uniform float u_treble_weight;

out vec4 fragColor;

void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution;

    float clamped_mid = clamp(u_mid, 0.0, 1.0);
    float clamped_treble = clamp(u_treble, 0.0, 1.0);
    float clamped_mid_weight = max(u_mid_weight, 0.0);
    float clamped_treble_weight = max(u_treble_weight, 0.0);
    float total_weight = clamped_mid_weight + clamped_treble_weight;
    float combined_energy = total_weight > 0.0
        ? clamp(
            (
                clamped_mid * clamped_mid_weight +
                clamped_treble * clamped_treble_weight
            ) / total_weight,
            0.0,
            1.0
        )
        : 0.0;
    float warp_intensity = max(u_warp_intensity, 0.0);
    float warp_frequency = max(u_warp_frequency, 1.0);

    float x_warp = sin(uv.y * warp_frequency + u_time) * combined_energy * warp_intensity;
    float y_warp =
        cos(uv.x * warp_frequency + (u_time * 1.1)) * combined_energy * (warp_intensity * 0.5);
    vec2 warped_uv = clamp(uv + vec2(x_warp, y_warp), 0.0, 1.0);
    vec3 color = texture(u_image, warped_uv).rgb;

    fragColor = vec4(clamp(color, 0.0, 1.0), 1.0);
}
