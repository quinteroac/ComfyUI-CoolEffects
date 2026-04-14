#version 330

uniform sampler2D u_image;
uniform float u_time;
uniform vec2 u_resolution;
uniform float u_drop_density;
uniform float u_drop_size;
uniform float u_fall_speed;
uniform float u_refraction_strength;
uniform float u_gravity;
uniform float u_wind;

out vec4 fragColor;

float hash11(float p) {
    p = fract(p * 0.1031);
    p *= p + 33.33;
    p *= p + p;
    return fract(p);
}

vec2 hash22(vec2 p) {
    float n = dot(p, vec2(127.1, 311.7));
    return fract(sin(vec2(n, n + 19.19)) * 43758.5453123);
}

void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution;
    float density = max(1.0, u_drop_density);
    vec2 grid_uv = uv * vec2(density, density * 1.35);
    vec2 cell = floor(grid_uv);
    vec2 local = fract(grid_uv) - 0.5;

    float gravity_term = max(0.05, u_gravity);
    float travel = u_time * u_fall_speed * gravity_term;
    vec2 displacement = vec2(0.0);
    float drop_mask = 0.0;

    for (int y = -1; y <= 1; y++) {
        for (int x = -1; x <= 1; x++) {
            vec2 offset = vec2(float(x), float(y));
            vec2 current_cell = cell + offset;
            vec2 jitter = hash22(current_cell);
            float size_mod = mix(0.6, 1.25, hash11(dot(current_cell, vec2(5.8, 13.3))));
            float radius = max(0.003, u_drop_size * size_mod);

            float cell_phase = hash11(dot(current_cell, vec2(17.0, 29.0))) * 12.0;
            float fall = fract(travel + cell_phase) - 0.5;
            vec2 drop_center = vec2(jitter.x - 0.5, fall + (jitter.y - 0.5) * 0.1);

            vec2 diff = local - offset - drop_center;
            diff.x -= u_wind * 0.12;
            float dist = length(diff);

            float drop = smoothstep(radius, radius * 0.45, dist);
            drop_mask = max(drop_mask, drop);

            vec2 normal = normalize(diff + vec2(1e-4));
            displacement += normal * drop;
        }
    }

    vec2 refract_uv = clamp(
        uv + displacement * (u_refraction_strength / 220.0),
        vec2(0.0),
        vec2(1.0)
    );
    vec3 color = texture(u_image, refract_uv).rgb;

    vec3 specular = vec3(0.08, 0.1, 0.12) * pow(drop_mask, 1.5);
    fragColor = vec4(color + specular, 1.0);
}
