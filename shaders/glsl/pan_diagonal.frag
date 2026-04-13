#version 330

uniform sampler2D u_image;
uniform float u_time;
uniform vec2 u_resolution;
uniform float u_speed;
uniform float u_origin_x;
uniform float u_origin_y;
uniform float u_dir_x;
uniform float u_dir_y;

out vec4 fragColor;

void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution;
    vec2 origin_uv = uv + vec2(u_origin_x, u_origin_y);
    vec2 scroll_offset = u_speed * u_time * vec2(u_dir_x, u_dir_y);
    vec2 wrapped_uv = fract(origin_uv + scroll_offset);
    vec3 color = texture(u_image, wrapped_uv).rgb;

    fragColor = vec4(color, 1.0);
}
