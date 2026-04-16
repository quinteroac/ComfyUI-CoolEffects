#version 330

uniform sampler2D u_image;
uniform float u_time;
uniform vec2 u_resolution;
uniform float u_strength;
uniform float u_zoom;

out vec4 fragColor;

void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution;
    vec2 centered_uv = (uv - vec2(0.5, 0.5)) * 2.0;

    float radius = length(centered_uv);
    float theta = atan(centered_uv.y, centered_uv.x);

    float strength = clamp(u_strength, 0.0, 1.0);
    float zoom = max(u_zoom, 0.001);
    float inverse_barrel = max(1.0 - strength * radius * radius, 0.0);
    float sample_radius = (radius * inverse_barrel) / zoom;

    vec2 remapped_uv = vec2(cos(theta), sin(theta)) * sample_radius * 0.5 + vec2(0.5, 0.5);
    vec3 color = texture(u_image, clamp(remapped_uv, vec2(0.0), vec2(1.0))).rgb;

    fragColor = vec4(clamp(color, 0.0, 1.0), 1.0);
}
