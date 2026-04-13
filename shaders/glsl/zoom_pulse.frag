#version 330

uniform sampler2D u_image;
uniform float u_time;
uniform vec2 u_resolution;
uniform float u_pulse_amp;
uniform float u_pulse_speed;

out vec4 fragColor;

void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution;
    vec2 center = vec2(0.5, 0.5);
    float pulse = 1.0 + u_pulse_amp * sin(u_time * u_pulse_speed);
    vec2 zoom_uv = (uv - center) / pulse + center;
    vec3 color = texture(u_image, zoom_uv).rgb;

    fragColor = vec4(color, 1.0);
}
