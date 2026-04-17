#version 330

uniform sampler2D u_image;
uniform float u_time;
uniform vec2 u_resolution;
uniform float u_shadows_r;
uniform float u_shadows_g;
uniform float u_shadows_b;
uniform float u_midtones_r;
uniform float u_midtones_g;
uniform float u_midtones_b;
uniform float u_highlights_r;
uniform float u_highlights_g;
uniform float u_highlights_b;

out vec4 fragColor;

void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution;
    vec4 source_color = texture(u_image, uv);
    float luma = dot(source_color.rgb, vec3(0.2126, 0.7152, 0.0722));

    float shadows_weight = clamp((0.5 - luma) * 2.0, 0.0, 1.0);
    float highlights_weight = clamp((luma - 0.5) * 2.0, 0.0, 1.0);
    float midtones_weight = clamp(1.0 - shadows_weight - highlights_weight, 0.0, 1.0);

    vec3 shadows_tint = vec3(
        clamp(u_shadows_r, -1.0, 1.0),
        clamp(u_shadows_g, -1.0, 1.0),
        clamp(u_shadows_b, -1.0, 1.0)
    );
    vec3 midtones_tint = vec3(
        clamp(u_midtones_r, -1.0, 1.0),
        clamp(u_midtones_g, -1.0, 1.0),
        clamp(u_midtones_b, -1.0, 1.0)
    );
    vec3 highlights_tint = vec3(
        clamp(u_highlights_r, -1.0, 1.0),
        clamp(u_highlights_g, -1.0, 1.0),
        clamp(u_highlights_b, -1.0, 1.0)
    );

    vec3 adjusted_color = source_color.rgb;
    adjusted_color += shadows_tint * shadows_weight;
    adjusted_color += midtones_tint * midtones_weight;
    adjusted_color += highlights_tint * highlights_weight;

    fragColor = vec4(clamp(adjusted_color, 0.0, 1.0), source_color.a);
}
