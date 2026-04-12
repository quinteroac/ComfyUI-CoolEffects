#version 330

uniform sampler2D u_image;
uniform float u_time;
uniform vec2 u_resolution;

out vec4 fragColor;

void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution;
    vec2 center = vec2(0.5, 0.5);
    float pulse = 1.0 + 0.06 * sin(u_time * 3.0);
    vec2 zoom_uv = (uv - center) / pulse + center;
    vec3 color = texture(u_image, zoom_uv).rgb;

    fragColor = vec4(color, 1.0);
}
