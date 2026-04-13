#version 330

uniform sampler2D u_image;
uniform float u_time;
uniform vec2 u_resolution;
uniform float u_scanline_intensity;
uniform float u_jitter_amount;
uniform float u_chroma_shift;

out vec4 fragColor;

void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution;
    float scanline = sin(uv.y * u_resolution.y * 0.75) * u_scanline_intensity;
    float jitter = sin((uv.y + u_time * 2.0) * 90.0) * u_jitter_amount;

    vec3 color;
    color.r = texture(u_image, uv + vec2(u_chroma_shift + jitter, 0.0)).r;
    color.g = texture(u_image, uv + vec2(jitter, 0.0)).g;
    color.b = texture(u_image, uv + vec2(-u_chroma_shift + jitter, 0.0)).b;
    color -= scanline;

    fragColor = vec4(color, 1.0);
}
