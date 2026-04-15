#version 330

uniform sampler2D u_image;
uniform float u_time;
uniform vec2 u_resolution;
uniform float u_pulse_intensity;
uniform float u_zoom_amount;
uniform float u_decay;
uniform float u_beat;
uniform float u_rms;

out vec4 fragColor;

void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution;
    vec2 center = vec2(0.5, 0.5);

    float beat_gate = clamp(u_beat, 0.0, 1.0);
    float rms_gate = clamp(u_rms, 0.0, 1.0);
    float beat_energy = max(beat_gate, rms_gate);
    float envelope = exp(-max(u_decay, 0.0) * (1.0 - beat_energy) * 6.0);
    float pulse = clamp(beat_energy * envelope, 0.0, 1.0);

    float zoom_scale = 1.0 + u_zoom_amount * pulse;
    vec2 zoom_uv = (uv - center) / zoom_scale + center;
    vec3 color = texture(u_image, zoom_uv).rgb;

    float flash = u_pulse_intensity * pulse;
    color = color * (1.0 + flash);

    fragColor = vec4(clamp(color, 0.0, 1.0), 1.0);
}
