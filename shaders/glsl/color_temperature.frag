#version 330

uniform sampler2D u_image;
uniform float u_time;
uniform vec2 u_resolution;
uniform float u_temperature;
uniform float u_tint;

out vec4 fragColor;

void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution;
    vec4 source_color = texture(u_image, uv);

    float temperature = clamp(u_temperature, -1.0, 1.0);
    float tint = clamp(u_tint, -1.0, 1.0);

    vec3 temperature_bias = vec3(
        temperature * 0.18,
        temperature * 0.03,
        -temperature * 0.18
    );
    vec3 tint_bias = vec3(
        tint * 0.12,
        -tint * 0.18,
        tint * 0.12
    );

    vec3 adjusted_color = source_color.rgb + temperature_bias + tint_bias;
    fragColor = vec4(clamp(adjusted_color, 0.0, 1.0), source_color.a);
}
