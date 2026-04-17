"""Shared EFFECT_PARAMS contract and per-effect default uniforms."""

EFFECT_PARAMS = "EFFECT_PARAMS"

DEFAULT_PARAMS: dict[str, dict] = {
    "glitch": {
        "u_wave_freq": 120.0,
        "u_wave_amp": 0.0025,
        "u_speed": 10.0,
    },
    "vhs": {
        "u_scanline_intensity": 0.04,
        "u_jitter_amount": 0.0018,
        "u_chroma_shift": 0.002,
    },
    "zoom_pulse": {
        "u_pulse_amp": 0.06,
        "u_pulse_speed": 3.0,
    },
    "zoom_in": {
        "u_zoom_strength": 0.25,
        "u_zoom_speed": 0.6,
    },
    "zoom_out": {
        "u_zoom_strength": 0.2,
        "u_zoom_speed": 0.6,
    },
    "dolly_in": {
        "u_dolly_strength": 0.35,
        "u_dolly_speed": 0.7,
        "u_focus_x": 0.5,
        "u_focus_y": 0.5,
    },
    "dolly_out": {
        "u_dolly_strength": 0.35,
        "u_dolly_speed": 0.7,
        "u_focus_x": 0.5,
        "u_focus_y": 0.5,
    },
    "bass_zoom": {
        "u_zoom_strength": 0.3,
        "u_smoothing": 0.5,
        "u_bass": 0.0,
    },
    "beat_pulse": {
        "u_pulse_intensity": 0.5,
        "u_zoom_amount": 0.05,
        "u_decay": 0.3,
        "u_beat": 0.0,
        "u_rms": 0.0,
    },
    "freq_warp": {
        "u_warp_intensity": 0.4,
        "u_warp_frequency": 8.0,
        "u_mid_weight": 0.6,
        "u_treble_weight": 0.4,
        "u_mid": 0.0,
        "u_treble": 0.0,
    },
    "water_drops": {
        "u_drop_density": 60,
        "u_drop_size": 0.08,
        "u_fall_speed": 1.0,
        "u_refraction_strength": 0.3,
        "u_gravity": 1.0,
        "u_wind": 0.0,
    },
    "frosted_glass": {
        "u_frost_intensity": 0.5,
        "u_blur_radius": 0.015,
        "u_uniformity": 0.6,
        "u_tint_temperature": 0.0,
        "u_condensation_rate": 0.0,
    },
    "fisheye": {
        "u_strength": 0.5,
        "u_zoom": 1.0,
    },
    "vignette": {
        "u_strength": 0.5,
        "u_radius": 0.75,
        "u_softness": 0.5,
    },
    "tilt_shift": {
        "u_focus_center": 0.5,
        "u_focus_width": 0.2,
        "u_blur_strength": 0.5,
        "u_angle": 0.0,
    },
    "pincushion": {
        "u_strength": 0.5,
        "u_zoom": 1.0,
    },
    "chromatic_aberration": {
        "u_strength": 0.01,
        "u_radial": 1.0,
    },
    "brightness_contrast": {
        "u_brightness": 0.0,
        "u_contrast": 0.0,
    },
    "hsl": {
        "u_hue_shift": 0.0,
        "u_saturation": 0.0,
        "u_lightness": 0.0,
    },
    "color_temperature": {
        "u_temperature": 0.0,
        "u_tint": 0.0,
    },
    "pan_left": {
        "u_speed": 0.1,
        "u_origin_x": 0.0,
        "u_origin_y": 0.0,
    },
    "pan_right": {
        "u_speed": 0.1,
        "u_origin_x": 0.0,
        "u_origin_y": 0.0,
    },
    "pan_up": {
        "u_speed": 0.1,
        "u_origin_x": 0.0,
        "u_origin_y": 0.0,
    },
    "pan_down": {
        "u_speed": 0.1,
        "u_origin_x": 0.0,
        "u_origin_y": 0.0,
    },
    "pan_diagonal": {
        "u_speed": 0.1,
        "u_origin_x": 0.0,
        "u_origin_y": 0.0,
        "u_dir_x": 0.7071,
        "u_dir_y": 0.7071,
    },
    "waveform": {
        "u_line_color": (1.0, 0.8, 0.2),
        "u_line_thickness": 0.005,
        "u_waveform_height": 0.2,
        "u_waveform_y": 0.8,
        "u_opacity": 0.85,
    },
    "text_overlay": {
        "u_color_r": 1.0,
        "u_color_g": 1.0,
        "u_color_b": 1.0,
        "u_opacity": 1.0,
        "u_anchor_x": 0.5,
        "u_anchor_y": 0.12,
        "u_offset_x": 0.0,
        "u_offset_y": 0.0,
        "u_font_size": 48.0,
        "u_animation_mode": 1.0,
        "u_animation_duration": 0.5,
    },
}


def build_effect_params(effect_name: str, params: dict) -> dict:
    if not effect_name:
        raise ValueError("effect_name must be a non-empty string")
    if not isinstance(params, dict):
        raise ValueError("params must be a dict")
    return {"effect_name": effect_name, "params": params}


def merge_params(effect_name: str, params: dict) -> dict:
    return {**DEFAULT_PARAMS[effect_name], **params}
