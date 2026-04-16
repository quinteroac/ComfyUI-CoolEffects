#version 330

uniform sampler2D u_image;
uniform float u_time;
uniform vec2 u_resolution;
uniform float u_strength;
uniform float u_radius;
uniform float u_softness;

out vec4 fragColor;

void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution;
    float radial_distance = distance(uv, vec2(0.5, 0.5));

    float strength = clamp(u_strength, 0.0, 1.0);
    float radius = max(u_radius, 0.0001);
    float softness = clamp(u_softness, 0.0, 1.0);
    float soft_edge = max(radius + softness * 0.75, radius + 0.0001);

    float vignette_factor = smoothstep(radius, soft_edge, radial_distance);
    vec3 source_color = texture(u_image, clamp(uv, vec2(0.0), vec2(1.0))).rgb;
    vec3 vignette_color = source_color * (1.0 - strength * vignette_factor);

    fragColor = vec4(clamp(vignette_color, 0.0, 1.0), 1.0);
}
