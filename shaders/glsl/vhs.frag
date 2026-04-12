#version 330

uniform sampler2D u_image;
uniform float u_time;
uniform vec2 u_resolution;

out vec4 frag_color;

void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution;
    float scanline = sin(uv.y * u_resolution.y * 0.75) * 0.04;
    float jitter = sin((uv.y + u_time * 2.0) * 90.0) * 0.0018;

    vec3 color;
    color.r = texture(u_image, uv + vec2(0.002 + jitter, 0.0)).r;
    color.g = texture(u_image, uv + vec2(jitter, 0.0)).g;
    color.b = texture(u_image, uv + vec2(-0.002 + jitter, 0.0)).b;
    color -= scanline;

    frag_color = vec4(color, 1.0);
}
