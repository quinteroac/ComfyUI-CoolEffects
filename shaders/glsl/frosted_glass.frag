#version 330

// Based on Shadertoy dist() technique
// iChannel0 → u_image, iTime → u_time, iResolution → u_resolution
// iChannel1 (noise texture) → replaced with sin-wave noise from the
//   commented alternative in the original snippet.
//
// Controls:
//   u_dew_amount       → max distortion strength (0 = no effect)
//   u_condensation_rate + u_frost_speed → how fast the effect builds up
//   u_uniformity       → spatial frequency of the distortion pattern

uniform sampler2D u_image;
uniform float u_time;
uniform vec2 u_resolution;
uniform float u_frost_intensity;    // reserved / unused
uniform float u_blur_radius;        // reserved / unused
uniform float u_uniformity;         // distortion frequency
uniform float u_tint_temperature;   // reserved / unused
uniform float u_condensation_rate;  // speed of build-up
uniform float u_frost_speed;        // speed multiplier
uniform float u_dew_amount;         // max displacement strength

out vec4 fragColor;

// Sin-wave noise replacing iChannel1 .xy
// Returns values in [0,1] — same range as a noise texture sample.
vec2 noise_sample(vec2 uv) {
    float freq = mix(1.0, 10.0, clamp(u_uniformity, 0.0, 1.0));
    return vec2(
        sin(uv.x * freq * 10.0) * 0.5 + sin(uv.x * freq * 3.14 / 2.0) * 0.5,
        sin(uv.y * freq * 10.0 + 200.0) * 0.5 + sin(uv.y * freq * 3.14 / 2.0 + 20.0) * 0.5
    ) * 0.5 + 0.5;   // map to [0, 1]
}

float stepfun(float x) {
    return (sign(x) + 1.0) / 2.0;
}

// Returns 1 inside [-1,1]x[-1,1], 0 outside — same as original square()
float square(vec2 pos) {
    return (stepfun(pos.x + 1.0) * stepfun(1.0 - pos.x)) *
           (stepfun(pos.y + 1.0) * stepfun(1.0 - pos.y));
}

// Exact port of the original dist() — covers the whole image (no circular
// movement), strength grows from 0 via condensation_rate * frost_speed * time.
vec2 dist_fn(vec2 pos, float strength) {
    // Scale so square() returns 1 for the entire image (range stays in [-1,1])
    vec2 scaled = (pos - 0.5) * 1.8;
    return pos + square(scaled) * noise_sample(scaled) * strength;
}

void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution;

    // Distortion grows from 0 → u_dew_amount * 0.1 over time
    float grow     = clamp(u_condensation_rate * u_time * u_frost_speed * 0.04, 0.0, 1.0);
    float strength = clamp(u_dew_amount, 0.0, 1.0) * grow * 0.10;

    vec2 duv = clamp(dist_fn(uv, strength), vec2(0.0), vec2(1.0));

    fragColor = vec4(texture(u_image, duv).rgb, 1.0);
}
