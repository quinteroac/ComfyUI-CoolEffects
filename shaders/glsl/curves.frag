#version 330

uniform sampler2D u_image;
uniform float u_time;
uniform vec2 u_resolution;
uniform float u_lift;
uniform float u_gamma;
uniform float u_gain;

out vec4 fragColor;

void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution;
    vec4 source_color = texture(u_image, uv);

    float lift = clamp(u_lift, 0.0, 1.0);
    float gamma = clamp(u_gamma, 0.1, 4.0);
    float gain = clamp(u_gain, 0.0, 4.0);

    vec3 adjusted_color = max(source_color.rgb + vec3(lift), vec3(0.0));
    adjusted_color = pow(adjusted_color, vec3(1.0 / gamma));
    adjusted_color *= vec3(gain);

    fragColor = vec4(clamp(adjusted_color, 0.0, 1.0), source_color.a);
}
