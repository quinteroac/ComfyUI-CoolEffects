#version 330

uniform sampler2D u_image;
uniform float u_time;
uniform vec2 u_resolution;
uniform float u_waveform[256];
uniform vec3 u_line_color;
uniform float u_line_thickness;
uniform float u_waveform_height;
uniform float u_waveform_y;
uniform float u_opacity;

out vec4 fragColor;

void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution;
    vec3 base_color = texture(u_image, uv).rgb;

    int sample_index = int(floor(uv.x * 256.0));
    sample_index = clamp(sample_index, 0, 255);
    float waveform_sample = clamp(u_waveform[sample_index], -1.0, 1.0);
    float waveform_y = u_waveform_y + waveform_sample * u_waveform_height * 0.5;
    float line_thickness = max(u_line_thickness, 0.0001);
    float line_mask = abs(uv.y - waveform_y) < line_thickness ? 1.0 : 0.0;

    float mix_strength = clamp(u_opacity, 0.0, 1.0) * line_mask;
    vec3 color = mix(base_color, clamp(u_line_color, 0.0, 1.0), mix_strength);
    fragColor = vec4(color, 1.0);
}
