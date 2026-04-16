#version 330

uniform sampler2D u_image;
uniform float u_time;
uniform vec2 u_resolution;
uniform float u_dolly_strength;
uniform float u_dolly_speed;
uniform float u_focus_x;
uniform float u_focus_y;

out vec4 fragColor;

void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution;
    vec2 center = clamp(vec2(u_focus_x, u_focus_y), vec2(0.0), vec2(1.0));

    float dolly_progress = max(u_dolly_speed, 0.0) * max(u_time, 0.0);
    float dolly_scale = 1.0 + max(u_dolly_strength, 0.0) * dolly_progress;
    vec2 dolly_uv = (uv - center) / max(dolly_scale, 0.001) + center;
    vec3 color = texture(u_image, clamp(dolly_uv, vec2(0.0), vec2(1.0))).rgb;

    fragColor = vec4(clamp(color, 0.0, 1.0), 1.0);
}
