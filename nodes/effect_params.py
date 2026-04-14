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
    "water_drops": {
        "u_drop_density": 60,
        "u_drop_size": 0.08,
        "u_fall_speed": 1.0,
        "u_refraction_strength": 0.3,
        "u_gravity": 1.0,
        "u_wind": 0.0,
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
}


def build_effect_params(effect_name: str, params: dict) -> dict:
    if not effect_name:
        raise ValueError("effect_name must be a non-empty string")
    if not isinstance(params, dict):
        raise ValueError("params must be a dict")
    return {"effect_name": effect_name, "params": params}


def merge_params(effect_name: str, params: dict) -> dict:
    return {**DEFAULT_PARAMS[effect_name], **params}
