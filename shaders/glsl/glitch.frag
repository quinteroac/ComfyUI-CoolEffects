#version 330

uniform sampler2D u_image;
uniform float u_time;
uniform vec2 u_resolution;

out vec4 frag_color;

void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution;
    float wave = sin(uv.y * 120.0 + u_time * 10.0) * 0.0025;
    vec2 r_uv = uv + vec2(wave * 1.8, 0.0);
    vec2 g_uv = uv + vec2(wave * 0.7, 0.0);
    vec2 b_uv = uv - vec2(wave * 1.2, 0.0);

    float r = texture(u_image, r_uv).r;
    float g = texture(u_image, g_uv).g;
    float b = texture(u_image, b_uv).b;

    frag_color = vec4(r, g, b, 1.0);
}
