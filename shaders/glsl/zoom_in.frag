#version 330

uniform sampler2D u_image;
uniform float u_time;
uniform vec2 u_resolution;
uniform float u_zoom_strength;
uniform float u_zoom_speed;

out vec4 fragColor;

void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution;
    vec2 center = vec2(0.5, 0.5);

    float zoom_progress = max(u_zoom_speed, 0.0) * max(u_time, 0.0);
    float zoom_scale = 1.0 + max(u_zoom_strength, 0.0) * zoom_progress;
    vec2 zoom_uv = (uv - center) / max(zoom_scale, 0.001) + center;
    vec3 color = texture(u_image, clamp(zoom_uv, vec2(0.0), vec2(1.0))).rgb;

    fragColor = vec4(clamp(color, 0.0, 1.0), 1.0);
}
