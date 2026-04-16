#version 330

uniform sampler2D u_image;
uniform float u_time;
uniform vec2 u_resolution;
uniform float u_focus_center;
uniform float u_focus_width;
uniform float u_blur_strength;
uniform float u_angle;

out vec4 fragColor;

vec2 clamp_uv(vec2 uv) {
    return clamp(uv, vec2(0.0), vec2(1.0));
}

vec3 sample_axis_blur(vec2 uv, vec2 texel, vec2 axis, float radius_px) {
    vec2 offset = axis * texel * radius_px;
    vec3 color = texture(u_image, clamp_uv(uv)).rgb * 0.2270270270;
    color += texture(u_image, clamp_uv(uv + offset * 1.3846153846)).rgb * 0.3162162162;
    color += texture(u_image, clamp_uv(uv - offset * 1.3846153846)).rgb * 0.3162162162;
    color += texture(u_image, clamp_uv(uv + offset * 3.2307692308)).rgb * 0.0702702703;
    color += texture(u_image, clamp_uv(uv - offset * 3.2307692308)).rgb * 0.0702702703;
    return color;
}

void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution;
    vec3 source_color = texture(u_image, clamp_uv(uv)).rgb;

    float focus_center = mix(-0.5, 0.5, clamp(u_focus_center, 0.0, 1.0));
    float focus_half_width = max(clamp(u_focus_width, 0.0, 1.0) * 0.5, 0.0001);
    float blur_strength = clamp(u_blur_strength, 0.0, 1.0);
    float angle_radians = radians(clamp(u_angle, 0.0, 360.0));

    float sin_angle = sin(angle_radians);
    float cos_angle = cos(angle_radians);
    vec2 centered_uv = uv - vec2(0.5);
    vec2 rotated_uv = vec2(
        cos_angle * centered_uv.x - sin_angle * centered_uv.y,
        sin_angle * centered_uv.x + cos_angle * centered_uv.y
    );

    float distance_from_focus_band = abs(rotated_uv.y - focus_center) - focus_half_width;
    float outside_distance = max(distance_from_focus_band, 0.0);
    float max_outside_distance = max(0.5 - focus_half_width, 0.0001);
    float blur_factor = clamp(outside_distance / max_outside_distance, 0.0, 1.0);
    blur_factor = blur_factor * blur_factor;

    float blur_radius_px = blur_strength * blur_factor * 12.0;
    vec2 texel = vec2(1.0) / max(u_resolution, vec2(1.0));

    vec3 blur_x = sample_axis_blur(uv, texel, vec2(1.0, 0.0), blur_radius_px);
    vec3 blur_y = sample_axis_blur(uv, texel, vec2(0.0, 1.0), blur_radius_px);
    vec3 gaussian_blur = 0.5 * (blur_x + blur_y);

    float mix_amount = blur_factor * blur_strength;
    vec3 final_color = mix(source_color, gaussian_blur, mix_amount);

    fragColor = vec4(clamp(final_color, 0.0, 1.0), 1.0);
}
