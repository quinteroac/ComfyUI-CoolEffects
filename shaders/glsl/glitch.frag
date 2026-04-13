#version 330

uniform sampler2D u_image;
uniform float u_time;
uniform vec2 u_resolution;
uniform float u_wave_freq;
uniform float u_wave_amp;
uniform float u_speed;

out vec4 fragColor;

void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution;
    float wave = sin(uv.y * u_wave_freq + u_time * u_speed) * u_wave_amp;
    vec2 r_uv = uv + vec2(wave * 1.8, 0.0);
    vec2 g_uv = uv + vec2(wave * 0.7, 0.0);
    vec2 b_uv = uv - vec2(wave * 1.2, 0.0);

    float r = texture(u_image, r_uv).r;
    float g = texture(u_image, g_uv).g;
    float b = texture(u_image, b_uv).b;

    fragColor = vec4(r, g, b, 1.0);
}
