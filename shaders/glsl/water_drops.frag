#version 330

// Based on "Heartfelt" by Martijn Steinrucken aka BigWings - 2017
// Email: countfrolic@gmail.com  Twitter: @The_ArtOfCode
// Original: https://www.shadertoy.com/view/ltffzl
// License: Creative Commons Attribution-NonCommercial-ShareAlike 3.0
//
// ComfyUI adaptation:
//   - Removed HAS_HEART (zoom, story timeline, heart shape)
//   - Removed animated cos() zoom from the non-heart path
//   - Removed lightning flash from USE_POST_PROCESSING
//   - Kept fog, subtle colour tint, vignette and fade-in
//   - iChannel0/iTime/iResolution/iMouse → ComfyUI uniforms
//   - textureLod (mipmap) → manual 13-tap blur kernel (sampleFog)
//   - Added u_wind for horizontal drift, u_drop_size for drop scale

uniform sampler2D u_image;
uniform float u_time;
uniform vec2 u_resolution;
uniform float u_drop_density;        // 1-200  → rain intensity
uniform float u_drop_size;           // 0.01-0.5 → drop scale (bigger = fewer, larger drops)
uniform float u_fall_speed;          // 0.1-5.0
uniform float u_refraction_strength; // 0.0-1.0 → lens displacement strength
uniform float u_gravity;             // 0.1-5.0 → fall speed multiplier
uniform float u_wind;                // -2.0 to 2.0 → horizontal drift
uniform float u_blur;                // 0.0-2.0 → fog/blur intensity multiplier

out vec4 fragColor;

#define S(a, b, t) smoothstep(a, b, t)

// ── Hash helpers (from original) ────────────────────────────────────────────
vec3 N13(float p) {
    vec3 p3 = fract(vec3(p) * vec3(.1031, .11369, .13787));
    p3 += dot(p3, p3.yzx + 19.19);
    return fract(vec3((p3.x+p3.y)*p3.z, (p3.x+p3.z)*p3.y, (p3.y+p3.z)*p3.x));
}
float N(float t) {
    return fract(sin(t*12345.564)*7658.76);
}
float Saw(float b, float t) {
    return S(0., b, t) * S(1., b, t);
}

// ── Falling drop layer (from original, + u_wind drift) ──────────────────────
vec2 DropLayer2(vec2 uv, float t) {
    vec2 UV = uv;
    uv.y += t*0.75;
    vec2 a = vec2(6., 1.);
    vec2 grid = a*2.;
    vec2 id = floor(uv*grid);
    float colShift = N(id.x);
    uv.y += colShift;
    id = floor(uv*grid);
    vec3 n = N13(id.x*35.2+id.y*2376.1);
    vec2 st = fract(uv*grid)-vec2(.5, 0);
    float x = n.x-.5;
    float y = UV.y*20.;
    float wiggle = sin(y+sin(y));
    x += wiggle*(.5-abs(x))*(n.z-.5);
    x += u_wind*0.12;
    x *= .7;
    float ti = fract(t+n.z);
    y = (Saw(.85, ti)-.5)*.9+.5;
    vec2 p = vec2(x, y);
    float d = length((st-p)*a.yx);
    float mainDrop = S(.4, .0, d);
    float r = sqrt(S(1., y, st.y));
    float cd = abs(st.x-x);
    float trail = S(.23*r, .15*r*r, cd);
    float trailFront = S(-.02, .02, st.y-y);
    trail *= trailFront*r*r;
    y = UV.y;
    float trail2 = S(.2*r, .0, cd);
    float droplets = max(0., (sin(y*(1.-y)*120.)-st.y))*trail2*trailFront*n.z;
    y = fract(y*10.)+(st.y-.5);
    float dd = length(st-vec2(x, y));
    droplets = S(.3, 0., dd);
    float m = mainDrop+droplets*r*trailFront;
    return vec2(m, trail);
}

// ── Static (condensation) drops (from original) ─────────────────────────────
float StaticDrops(vec2 uv, float t) {
    uv *= 40.;
    vec2 id = floor(uv);
    uv = fract(uv)-.5;
    vec3 n = N13(id.x*107.45+id.y*3543.654);
    vec2 p = (n.xy-.5)*.7;
    float d = length(uv-p);
    float fade = Saw(.025, fract(t+n.z));
    float c = S(.3, 0., d)*fract(n.z*10.)*fade;
    return c;
}

// ── Combined drop field (from original) ─────────────────────────────────────
vec2 Drops(vec2 uv, float t, float l0, float l1, float l2) {
    float s = StaticDrops(uv, t)*l0;
    vec2 m1 = DropLayer2(uv,      t)*l1;
    vec2 m2 = DropLayer2(uv*1.85, t)*l2;
    float c = s+m1.x+m2.x;
    c = S(.3, 1., c);
    return vec2(c, max(m1.y*l0, m2.y*l1));
}

// ── Manual blur — replaces textureLod mipmap fog ─────────────────────────────
// Weighted 13-tap kernel; blur radius scales with the `amount` arg (0-6 range).
vec3 sampleFog(sampler2D tex, vec2 uv, float amount) {
    float r = amount * 0.0042;
    vec3 col  = texture(tex, uv).rgb * 4.0;
    col += texture(tex, uv + vec2( r,    0.0)).rgb * 2.0;
    col += texture(tex, uv + vec2(-r,    0.0)).rgb * 2.0;
    col += texture(tex, uv + vec2( 0.0,  r  )).rgb * 2.0;
    col += texture(tex, uv + vec2( 0.0, -r  )).rgb * 2.0;
    col += texture(tex, uv + vec2( r,    r  )).rgb;
    col += texture(tex, uv + vec2(-r,    r  )).rgb;
    col += texture(tex, uv + vec2( r,   -r  )).rgb;
    col += texture(tex, uv + vec2(-r,   -r  )).rgb;
    col += texture(tex, uv + vec2( r*2.2,  0.0)).rgb * 0.5;
    col += texture(tex, uv + vec2(-r*2.2,  0.0)).rgb * 0.5;
    col += texture(tex, uv + vec2( 0.0,  r*2.2)).rgb * 0.5;
    col += texture(tex, uv + vec2( 0.0, -r*2.2)).rgb * 0.5;
    return col / 17.0;
}

void main() {
    // Aspect-corrected UV — keeps drop shapes round at any resolution
    // Y negated to match ComfyUI framebuffer orientation (Y=0 at top)
    vec2 uv = (gl_FragCoord.xy - 0.5*u_resolution) / u_resolution.y;
    uv.y = -uv.y;
    // Standard 0-1 UV for texture sampling
    vec2 UV = gl_FragCoord.xy / u_resolution;

    float T = u_time * u_fall_speed * max(0.1, u_gravity);
    float t = T * 0.2;

    // u_drop_density (1-200) → rainAmount in the original's 0.4–1.0 range
    float rainAmount = 0.3 + clamp(u_drop_density / 200.0, 0.0, 1.0) * 0.7;

    // Original blur range (from Heartfelt, non-HAS_HEART path), scaled by u_blur
    float maxBlur = mix(3., 6., rainAmount) * u_blur;
    float minBlur = 2. * u_blur;

    float staticDrops = S(-.5, 1., rainAmount) * 2.;
    float layer1      = S(.25, .75, rainAmount);
    float layer2      = S(.0,  .5,  rainAmount);

    // u_drop_size controls view scale; smaller → more zoom → larger drops
    float dropScale = clamp(1.0 / (u_drop_size * 12.0), 0.3, 5.0);
    vec2 scaledUV   = uv * dropScale;

    vec2 c = Drops(scaledUV, t, staticDrops, layer1, layer2);

    // Expensive normals (same as original: 3 Drops evaluations)
    vec2 e  = vec2(.001, 0.);
    float cx = Drops(scaledUV + e,    t, staticDrops, layer1, layer2).x;
    float cy = Drops(scaledUV + e.yx, t, staticDrops, layer1, layer2).x;
    vec2 n  = vec2(cx-c.x, cy-c.x);
    // u_refraction_strength = 1 ≈ original unscaled refraction
    n *= u_refraction_strength * 3.5;

    // Focus: foggy where no drops, sharp+refracted on drops (c.y = trail mask)
    float focus = mix(maxBlur-c.y, minBlur, S(.1, .2, c.x));
    vec3 col = sampleFog(u_image, UV+n, focus);

    // USE_POST_PROCESSING (from original) — colour tint + vignette,
    // lightning flash and fade-in intentionally removed.
    float t2 = (T+3.)*.5;
    float colFade = sin(t2*.2)*.5+.5;
    col *= mix(vec3(1.), vec3(.8, .9, 1.3), colFade);  // subtle cool tint
    col *= 1.-dot(UV-=.5, UV);                          // vignette

    fragColor = vec4(clamp(col, 0.0, 1.0), 1.);
}
