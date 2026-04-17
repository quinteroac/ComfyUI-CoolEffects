#version 330

uniform sampler2D u_image;
uniform float u_time;
uniform vec2 u_resolution;
uniform float u_mode;
uniform float u_intensity;
uniform float u_shadow_r;
uniform float u_shadow_g;
uniform float u_shadow_b;
uniform float u_highlight_r;
uniform float u_highlight_g;
uniform float u_highlight_b;

out vec4 fragColor;

void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution;
    vec4 source_color = texture(u_image, uv);
    vec3 source_rgb = source_color.rgb;

    float luma = dot(source_rgb, vec3(0.2126, 0.7152, 0.0722));
    vec3 bw_color = vec3(luma);
    vec3 sepia_color = vec3(
        dot(source_rgb, vec3(0.393, 0.769, 0.189)),
        dot(source_rgb, vec3(0.349, 0.686, 0.168)),
        dot(source_rgb, vec3(0.272, 0.534, 0.131))
    );

    vec3 shadow_color = vec3(
        clamp(u_shadow_r, 0.0, 1.0),
        clamp(u_shadow_g, 0.0, 1.0),
        clamp(u_shadow_b, 0.0, 1.0)
    );
    vec3 highlight_color = vec3(
        clamp(u_highlight_r, 0.0, 1.0),
        clamp(u_highlight_g, 0.0, 1.0),
        clamp(u_highlight_b, 0.0, 1.0)
    );
    vec3 duotone_color = mix(shadow_color, highlight_color, luma);

    float mode = clamp(u_mode, 0.0, 3.0);
    vec3 target_color = source_rgb;
    if (mode >= 0.5 && mode < 1.5) {
        target_color = bw_color;
    } else if (mode >= 1.5 && mode < 2.5) {
        target_color = sepia_color;
    } else if (mode >= 2.5) {
        target_color = duotone_color;
    }

    float intensity = clamp(u_intensity, 0.0, 1.0);
    vec3 mapped_color = mix(source_rgb, target_color, intensity);
    fragColor = vec4(clamp(mapped_color, 0.0, 1.0), source_color.a);
}
