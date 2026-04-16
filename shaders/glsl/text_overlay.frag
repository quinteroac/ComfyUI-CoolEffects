#version 330 core

uniform sampler2D u_image;
uniform float u_time;
uniform vec2 u_resolution;

uniform float u_anchor_x;
uniform float u_anchor_y;
uniform float u_offset_x;
uniform float u_offset_y;
uniform float u_color_r;
uniform float u_color_g;
uniform float u_color_b;
uniform float u_opacity;
uniform float u_font_size;

in vec2 v_uv;
out vec4 fragColor;

float rounded_rect_alpha(vec2 p, vec2 half_size, float radius) {
    vec2 d = abs(p) - (half_size - vec2(radius));
    float outside = length(max(d, vec2(0.0)));
    float inside = min(max(d.x, d.y), 0.0);
    float signed_distance = outside + inside - radius;
    return 1.0 - smoothstep(0.0, 1.5, signed_distance);
}

void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution;
    vec4 base_color = texture(u_image, uv);

    float resolved_font_size = max(u_font_size, 8.0);
    vec2 text_size = vec2(
        clamp((resolved_font_size / u_resolution.x) * 6.0, 0.08, 0.75),
        clamp((resolved_font_size / u_resolution.y) * 1.6, 0.04, 0.3)
    );

    vec2 anchor = vec2(u_anchor_x, u_anchor_y) + vec2(u_offset_x, u_offset_y);
    vec2 center = clamp(anchor, text_size * 0.5, vec2(1.0) - text_size * 0.5);

    vec2 local = uv - center;
    float radius = min(text_size.x, text_size.y) * 0.2;
    float alpha_shape = rounded_rect_alpha(local, text_size * 0.5, radius);
    float pulse = 0.96 + 0.04 * sin(u_time * 2.0);
    vec3 tint = vec3(u_color_r, u_color_g, u_color_b) * pulse;
    float alpha = clamp(u_opacity, 0.0, 1.0) * alpha_shape;

    vec3 mixed_rgb = mix(base_color.rgb, tint, alpha);
    fragColor = vec4(mixed_rgb, 1.0);
}
