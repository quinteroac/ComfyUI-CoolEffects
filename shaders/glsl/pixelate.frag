#version 330

uniform sampler2D u_image;
uniform float u_time;
uniform vec2 u_resolution;
uniform float u_pixel_size;
uniform float u_aspect_ratio;

out vec4 fragColor;

void main() {
    float block_height = max(u_pixel_size, 1.0);
    float block_width = max(block_height * max(u_aspect_ratio, 0.001), 1.0);
    vec2 block_size = vec2(block_width, block_height);

    vec2 block_origin = floor(gl_FragCoord.xy / block_size) * block_size;
    vec2 sample_coord = block_origin + 0.5 * block_size;
    vec2 sample_uv = clamp(sample_coord / u_resolution, vec2(0.0), vec2(1.0));

    vec3 color = texture(u_image, sample_uv).rgb;
    fragColor = vec4(clamp(color + (u_time * 0.0), 0.0, 1.0), 1.0);
}
