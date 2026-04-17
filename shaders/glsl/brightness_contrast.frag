#version 330

uniform sampler2D u_image;
uniform float u_time;
uniform vec2 u_resolution;
uniform float u_brightness;
uniform float u_contrast;

out vec4 fragColor;

void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution;
    vec4 source_color = texture(u_image, uv);

    float brightness = clamp(u_brightness, -1.0, 1.0);
    float contrast = clamp(u_contrast, -1.0, 1.0);
    float contrast_scale = 1.0 + contrast;

    vec3 adjusted_color = (source_color.rgb - vec3(0.5)) * contrast_scale + vec3(0.5);
    adjusted_color += vec3(brightness);

    fragColor = vec4(clamp(adjusted_color, 0.0, 1.0), source_color.a);
}
