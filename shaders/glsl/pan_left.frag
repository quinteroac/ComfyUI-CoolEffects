#version 330

uniform sampler2D u_image;
uniform float u_time;
uniform vec2 u_resolution;
uniform float u_speed;
uniform float u_origin_x;
uniform float u_origin_y;
uniform float u_zoom;

out vec4 fragColor;

void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution;
    float zoom_scale = max(1.0 + u_zoom, 0.001);
    vec2 zoomed_uv = (uv - 0.5) / zoom_scale + 0.5;
    vec2 origin_uv = zoomed_uv + vec2(u_origin_x, u_origin_y);
    vec2 scroll_offset = vec2(-u_speed * u_time, 0.0);
    vec2 wrapped_uv = fract(origin_uv + scroll_offset);
    vec3 color = texture(u_image, wrapped_uv).rgb;

    fragColor = vec4(color, 1.0);
}
