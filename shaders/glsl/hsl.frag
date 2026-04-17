#version 330

uniform sampler2D u_image;
uniform float u_time;
uniform vec2 u_resolution;
uniform float u_hue_shift;
uniform float u_saturation;
uniform float u_lightness;

out vec4 fragColor;

vec3 rgb_to_hsl(vec3 color) {
    float max_channel = max(max(color.r, color.g), color.b);
    float min_channel = min(min(color.r, color.g), color.b);
    float chroma = max_channel - min_channel;
    float lightness = (max_channel + min_channel) * 0.5;

    float hue = 0.0;
    float saturation = 0.0;

    if (chroma > 0.000001) {
        saturation = chroma / (1.0 - abs(2.0 * lightness - 1.0));
        if (max_channel == color.r) {
            hue = mod((color.g - color.b) / chroma, 6.0);
        } else if (max_channel == color.g) {
            hue = ((color.b - color.r) / chroma) + 2.0;
        } else {
            hue = ((color.r - color.g) / chroma) + 4.0;
        }
        hue /= 6.0;
        if (hue < 0.0) {
            hue += 1.0;
        }
    }

    return vec3(hue, clamp(saturation, 0.0, 1.0), lightness);
}

float hue_to_rgb(float p, float q, float t) {
    if (t < 0.0) {
        t += 1.0;
    }
    if (t > 1.0) {
        t -= 1.0;
    }
    if (t < (1.0 / 6.0)) {
        return p + (q - p) * 6.0 * t;
    }
    if (t < 0.5) {
        return q;
    }
    if (t < (2.0 / 3.0)) {
        return p + (q - p) * ((2.0 / 3.0) - t) * 6.0;
    }
    return p;
}

vec3 hsl_to_rgb(vec3 hsl) {
    float hue = hsl.x;
    float saturation = clamp(hsl.y, 0.0, 1.0);
    float lightness = clamp(hsl.z, 0.0, 1.0);

    if (saturation <= 0.000001) {
        return vec3(lightness);
    }

    float q = lightness < 0.5
        ? lightness * (1.0 + saturation)
        : lightness + saturation - (lightness * saturation);
    float p = 2.0 * lightness - q;

    return vec3(
        hue_to_rgb(p, q, hue + (1.0 / 3.0)),
        hue_to_rgb(p, q, hue),
        hue_to_rgb(p, q, hue - (1.0 / 3.0))
    );
}

void main() {
    vec2 uv = gl_FragCoord.xy / u_resolution;
    vec4 source_color = texture(u_image, uv);

    float hue_shift = clamp(u_hue_shift, -180.0, 180.0);
    float saturation_delta = clamp(u_saturation, -1.0, 1.0);
    float lightness_delta = clamp(u_lightness, -1.0, 1.0);

    vec3 hsl = rgb_to_hsl(source_color.rgb);
    float normalized_hue_shift = hue_shift / 360.0;
    hsl.x = mod(hsl.x + normalized_hue_shift + 1.0, 1.0);
    hsl.y = clamp(hsl.y + saturation_delta, 0.0, 1.0);
    hsl.z = clamp(hsl.z + lightness_delta, 0.0, 1.0);

    vec3 adjusted_color = hsl_to_rgb(hsl);
    fragColor = vec4(clamp(adjusted_color, 0.0, 1.0), source_color.a);
}
