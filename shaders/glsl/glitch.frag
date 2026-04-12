// Minimal passthrough effect with required uniform contract.
uniform sampler2D u_image;
uniform float u_time;
uniform vec2 u_resolution;

void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution;
    vec3 color = texture(u_image, uv).rgb;
    gl_FragColor = vec4(color, 1.0);
}
