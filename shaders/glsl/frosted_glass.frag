#version 330

uniform sampler2D u_image;
uniform float u_time;
uniform vec2 u_resolution;
uniform float u_frost_intensity;
uniform float u_blur_radius;
uniform float u_uniformity;
uniform float u_tint_temperature;
uniform float u_condensation_rate;

out vec4 fragColor;

float hash12(vec2 p) {
    vec3 p3 = fract(vec3(p.xyx) * 0.1031);
    p3 += dot(p3, p3.yzx + 33.33);
    return fract((p3.x + p3.y) * p3.z);
}

float value_noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    float a = hash12(i);
    float b = hash12(i + vec2(1.0, 0.0));
    float c = hash12(i + vec2(0.0, 1.0));
    float d = hash12(i + vec2(1.0, 1.0));
    return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

float fbm(vec2 p) {
    float value = 0.0;
    float amplitude = 0.6;
    vec2 q = p;
    for (int i = 0; i < 4; i++) {
        value += value_noise(q) * amplitude;
        q *= 2.0;
        amplitude *= 0.5;
    }
    return value;
}

void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution;
    float uniformity = clamp(u_uniformity, 0.0, 1.0);
    float frost_intensity = clamp(u_frost_intensity, 0.0, 1.0);
    float condensation = clamp(
        frost_intensity + u_condensation_rate * u_time * 0.08,
        0.0,
        1.0
    );
    float noise_frequency = mix(2.5, 28.0, uniformity);
    float time_phase = u_time * 0.22;
    float frost_noise = fbm(uv * noise_frequency + vec2(time_phase * 0.28, -time_phase * 0.21));

    vec3 center_sample = texture(u_image, uv).rgb;
    vec3 blur_sum = center_sample;
    float weight_sum = 1.0;
    float angle_step = 0.78539816339; // 2*PI / 8
    float jitter = (frost_noise - 0.5) * 0.7;
    float blur_radius = max(0.0, u_blur_radius);

    for (int i = 0; i < 8; i++) {
        float angle = float(i) * angle_step;
        vec2 direction = vec2(cos(angle), sin(angle));
        float radial_offset = blur_radius * (1.0 + jitter * 0.55);
        vec2 sample_uv = clamp(uv + direction * radial_offset, vec2(0.0), vec2(1.0));
        vec3 sample_color = texture(u_image, sample_uv).rgb;
        blur_sum += sample_color;
        weight_sum += 1.0;
    }

    vec3 blurred = blur_sum / weight_sum;
    float blur_mix = clamp(frost_intensity * 0.7 + condensation * 0.25, 0.0, 1.0);
    vec3 softened = mix(center_sample, blurred, blur_mix);

    float patch_mask = smoothstep(0.35, 0.9, frost_noise) * condensation;
    vec3 cold_tint = vec3(0.9, 0.95, 1.05);
    vec3 warm_tint = vec3(1.06, 1.0, 0.9);
    float tint_mix = clamp((u_tint_temperature + 1.0) * 0.5, 0.0, 1.0);
    vec3 tint = mix(cold_tint, warm_tint, tint_mix);
    vec3 frosted_color = softened * tint + vec3(0.09) * patch_mask;

    fragColor = vec4(clamp(mix(softened, frosted_color, patch_mask), 0.0, 1.0), 1.0);
}
