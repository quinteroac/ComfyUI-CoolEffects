#version 330

uniform sampler2D u_image;
uniform float u_time;
uniform vec2 u_resolution;
uniform float u_strength;
uniform float u_radial;

out vec4 fragColor;

void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution;
    vec2 center = vec2(0.5, 0.5);
    vec2 to_center = uv - center;
    float distance_from_center = length(to_center);
    vec2 radial_direction = distance_from_center > 0.0
        ? normalize(to_center)
        : vec2(1.0, 0.0);

    float pulse = 1.0 + 0.5 * sin(u_time * 2.3);
    float clamped_strength = clamp(u_strength, 0.0, 0.1) * pulse;
    float radial_falloff = clamp(distance_from_center * 1.41421356, 0.0, 1.0);
    float radial_mode = step(0.5, u_radial);

    vec2 radial_offset = radial_direction * clamped_strength * radial_falloff;
    vec2 lateral_offset = vec2(clamped_strength, 0.0);
    vec2 channel_offset = mix(lateral_offset, radial_offset, radial_mode);

    float red = texture(u_image, clamp(uv + channel_offset, vec2(0.0), vec2(1.0))).r;
    float green = texture(u_image, clamp(uv, vec2(0.0), vec2(1.0))).g;
    float blue = texture(u_image, clamp(uv - channel_offset, vec2(0.0), vec2(1.0))).b;

    fragColor = vec4(red, green, blue, 1.0);
}
